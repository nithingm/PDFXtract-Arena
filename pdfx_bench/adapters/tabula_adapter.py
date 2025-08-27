"""
Tabula adapter for PDFX-Bench.
Extracts tables using tabula-py (requires Java).
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import pandas as pd
from ..schema import (
    Document, Table, TableCell, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class TabulaAdapter:
    """Adapter for tabula-py table extraction."""
    
    def __init__(self):
        self.method = ExtractionMethod.TABULA
        self._check_java()
    
    def _check_java(self):
        """Check if Java is available."""
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("Java not found or not working")
            logger.debug("Java check passed")
        except (subprocess.TimeoutExpired, FileNotFoundError, RuntimeError) as e:
            logger.error(f"Java check failed: {e}")
            raise RuntimeError(
                "Java is required for tabula-py. Please install Java and ensure "
                "it's available in your PATH."
            )
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract tables using tabula-py.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-based), None for all
            **kwargs: Additional tabula parameters
            
        Returns:
            Document with extracted tables
        """
        logger.info(f"Starting tabula extraction: {pdf_path}")
        
        with time_operation("tabula_extraction"):
            try:
                import tabula
                
                # Prepare page specification
                if pages is None:
                    pages_spec = "all"
                else:
                    pages_spec = pages
                
                # Extract tables using tabula
                # Use pandas_options to handle various data types
                pandas_options = kwargs.pop('pandas_options', {'dtype': str})

                # Filter out unsupported parameters for tabula
                supported_params = {
                    'lattice', 'stream', 'guess', 'area', 'columns', 'format',
                    'output_format', 'java_options', 'silent', 'encoding'
                }
                tabula_kwargs = {k: v for k, v in kwargs.items() if k in supported_params}

                tables_list = tabula.read_pdf(
                    str(pdf_path),
                    pages=pages_spec,
                    multiple_tables=True,
                    pandas_options=pandas_options,
                    **tabula_kwargs
                )
                
                # Convert tabula tables to our schema
                tables = []
                for table_idx, df in enumerate(tables_list):
                    if df is not None and not df.empty:
                        # Estimate page number (tabula doesn't always provide this clearly)
                        page_num = self._estimate_page_number(table_idx, pages)
                        table = self._convert_tabula_table(df, table_idx, page_num)
                        if table:
                            tables.append(table)
                
                # Get page count
                page_count = self._get_page_count(pdf_path)
                
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=page_count,
                    tables=tables,
                    extraction_metadata={
                        'method': self.method.value,
                        'pages_processed': pages_spec,
                        'tabula_version': tabula.__version__,
                        'total_tables_found': len(tables_list)
                    }
                )
                
                logger.info(f"tabula extraction complete: {len(tables)} tables")
                
                return document
            
            except ImportError:
                logger.error("tabula-py not installed")
                raise RuntimeError(
                    "tabula-py is required. Install with: pip install tabula-py"
                )
            except Exception as e:
                logger.error(f"Tabula extraction failed: {e}")
                # Return empty document on failure
                return Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=self._get_page_count(pdf_path),
                    extraction_metadata={
                        'method': self.method.value,
                        'error': str(e)
                    }
                )
    
    def _convert_tabula_table(
        self,
        df: pd.DataFrame,
        table_idx: int,
        page_num: int
    ) -> Optional[Table]:
        """Convert a tabula DataFrame to our Table schema."""
        try:
            table_id = f"page_{page_num}_table_{table_idx}"
            cells = []
            
            # Convert DataFrame to cells
            for row_idx, (_, row) in enumerate(df.iterrows()):
                for col_idx, cell_value in enumerate(row):
                    # Handle NaN values
                    if pd.isna(cell_value):
                        cell_text = ""
                    else:
                        cell_text = str(cell_value).strip()
                    
                    # Estimate cell bbox (tabula doesn't provide exact coordinates)
                    cell_bbox = self._estimate_cell_bbox(
                        row_idx, col_idx, len(df), len(df.columns)
                    )
                    
                    provenance = create_provenance(
                        method=self.method,
                        page=page_num,
                        bbox=cell_bbox,
                        raw_data={
                            'table_index': table_idx,
                            'row_index': row_idx,
                            'col_index': col_idx,
                            'original_value': cell_value
                        }
                    )
                    
                    cell = TableCell(
                        raw_text=cell_text,
                        row_idx=row_idx,
                        col_idx=col_idx,
                        is_header=(row_idx == 0),  # Assume first row is header
                        provenance=provenance
                    )
                    
                    cells.append(cell)
            
            # Create table provenance
            table_provenance = create_provenance(
                method=self.method,
                page=page_num,
                raw_data={
                    'table_index': table_idx,
                    'rows': len(df),
                    'cols': len(df.columns),
                    'column_names': list(df.columns)
                }
            )
            
            table = Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )
            
            return table
        
        except Exception as e:
            logger.warning(f"Failed to convert tabula table {table_idx}: {e}")
            return None
    
    def _estimate_page_number(
        self,
        table_idx: int,
        pages: Optional[List[int]]
    ) -> int:
        """Estimate page number for a table."""
        if pages is None:
            # If processing all pages, assume tables are in order
            return table_idx + 1
        elif isinstance(pages, list) and pages:
            # If specific pages, distribute tables across them
            page_idx = table_idx % len(pages)
            return pages[page_idx]
        else:
            return 1
    
    def _estimate_cell_bbox(
        self,
        row_idx: int,
        col_idx: int,
        total_rows: int,
        total_cols: int
    ) -> Optional[BoundingBox]:
        """Estimate cell bounding box (very rough approximation)."""
        try:
            # Use standard page dimensions (US Letter: 612x792 points)
            page_width = 612
            page_height = 792
            
            # Assume table takes up most of the page
            table_margin = 50
            table_width = page_width - (2 * table_margin)
            table_height = page_height - (2 * table_margin)
            
            if total_rows == 0 or total_cols == 0:
                return None
            
            cell_width = table_width / total_cols
            cell_height = table_height / total_rows
            
            x0 = table_margin + (col_idx * cell_width)
            y0 = table_margin + (row_idx * cell_height)
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            
            return create_bbox_from_coords(x0, y0, x1, y1)
        
        except Exception:
            return None
    
    def _get_page_count(self, pdf_path: Path) -> int:
        """Get page count from PDF."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception:
            logger.warning(f"Could not determine page count for {pdf_path}")
            return 1
