"""
Camelot adapter for PDFX-Bench.
Extracts tables using camelot in both lattice and stream modes.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import camelot
from ..schema import (
    Document, Table, TableCell, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class CamelotAdapter:
    """Adapter for camelot table extraction."""
    
    def __init__(self, mode: str = "lattice"):
        """
        Initialize Camelot adapter.
        
        Args:
            mode: Extraction mode ("lattice" or "stream")
        """
        if mode not in ["lattice", "stream"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'lattice' or 'stream'")
        
        self.mode = mode
        self.method = (
            ExtractionMethod.CAMELOT_LATTICE if mode == "lattice"
            else ExtractionMethod.CAMELOT_STREAM
        )
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract tables using camelot.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-based), None for all
            **kwargs: Additional camelot parameters
            
        Returns:
            Document with extracted tables
        """
        logger.info(f"Starting camelot-{self.mode} extraction: {pdf_path}")
        
        with time_operation(f"camelot_{self.mode}_extraction"):
            # Prepare page specification for camelot
            if pages is None:
                pages_spec = "all"
            else:
                pages_spec = ",".join(str(p) for p in pages)
            
            try:
                # Extract tables using camelot
                # Filter kwargs to only include camelot-specific parameters
                camelot_kwargs = {k: v for k, v in kwargs.items()
                                if k in ['table_areas', 'columns', 'split_text', 'flag_size',
                                        'strip_text', 'row_tol', 'column_tol', 'line_scale',
                                        'copy_text', 'shift_text', 'line_tol', 'joint_tol',
                                        'threshold_blocksize', 'threshold_constant', 'iterations',
                                        'resolution']}

                if self.mode == "lattice":
                    tables_list = camelot.read_pdf(
                        str(pdf_path),
                        pages=pages_spec,
                        flavor="lattice",
                        **camelot_kwargs
                    )
                else:  # stream mode
                    tables_list = camelot.read_pdf(
                        str(pdf_path),
                        pages=pages_spec,
                        flavor="stream",
                        **camelot_kwargs
                    )
                
                # Convert camelot tables to our schema
                tables = []
                for table_idx, camelot_table in enumerate(tables_list):
                    table = self._convert_camelot_table(camelot_table, table_idx)
                    if table:
                        tables.append(table)
                
                # Get page count (camelot doesn't provide this directly)
                page_count = self._get_page_count(pdf_path)
                
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=page_count,
                    tables=tables,
                    extraction_metadata={
                        'method': self.method.value,
                        'mode': self.mode,
                        'pages_processed': pages_spec,
                        'camelot_version': camelot.__version__,
                        'total_tables_found': len(tables_list)
                    }
                )
                
                logger.info(
                    f"camelot-{self.mode} extraction complete: {len(tables)} tables"
                )
                
                return document
            
            except Exception as e:
                logger.error(f"Camelot extraction failed: {e}")
                # Return empty document on failure
                return Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=self._get_page_count(pdf_path),
                    extraction_metadata={
                        'method': self.method.value,
                        'mode': self.mode,
                        'error': str(e)
                    }
                )
    
    def _convert_camelot_table(self, camelot_table, table_idx: int) -> Optional[Table]:
        """Convert a camelot table to our Table schema."""
        try:
            # Get table data as DataFrame
            df = camelot_table.df
            page_num = camelot_table.page
            
            # Get table bounding box
            table_bbox = None
            if hasattr(camelot_table, '_bbox') and camelot_table._bbox:
                bbox_coords = camelot_table._bbox
                table_bbox = create_bbox_from_coords(
                    x0=bbox_coords[0], y0=bbox_coords[1],
                    x1=bbox_coords[2], y1=bbox_coords[3]
                )
            
            table_id = f"page_{page_num}_table_{table_idx}"
            cells = []
            
            # Convert DataFrame to cells
            for row_idx, (_, row) in enumerate(df.iterrows()):
                for col_idx, cell_value in enumerate(row):
                    # Estimate cell bbox within table
                    cell_bbox = self._estimate_cell_bbox(
                        table_bbox, row_idx, col_idx, len(df), len(df.columns)
                    )
                    
                    provenance = create_provenance(
                        method=self.method,
                        page=page_num,
                        bbox=cell_bbox,
                        raw_data={
                            'table_index': table_idx,
                            'row_index': row_idx,
                            'col_index': col_idx,
                            'camelot_accuracy': getattr(camelot_table, 'accuracy', None),
                            'camelot_whitespace': getattr(camelot_table, 'whitespace', None)
                        }
                    )
                    
                    cell = TableCell(
                        raw_text=str(cell_value).strip() if cell_value is not None else "",
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
                bbox=table_bbox,
                raw_data={
                    'table_index': table_idx,
                    'rows': len(df),
                    'cols': len(df.columns),
                    'camelot_accuracy': getattr(camelot_table, 'accuracy', None),
                    'camelot_whitespace': getattr(camelot_table, 'whitespace', None),
                    'parsing_report': getattr(camelot_table, 'parsing_report', None)
                }
            )
            
            table = Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )
            
            return table
        
        except Exception as e:
            logger.warning(f"Failed to convert camelot table {table_idx}: {e}")
            return None
    
    def _estimate_cell_bbox(
        self,
        table_bbox: Optional[BoundingBox],
        row_idx: int,
        col_idx: int,
        total_rows: int,
        total_cols: int
    ) -> Optional[BoundingBox]:
        """Estimate cell bounding box within table."""
        if not table_bbox or total_rows == 0 or total_cols == 0:
            return None
        
        try:
            table_width = table_bbox.x1 - table_bbox.x0
            table_height = table_bbox.y1 - table_bbox.y0
            
            cell_width = table_width / total_cols
            cell_height = table_height / total_rows
            
            x0 = table_bbox.x0 + (col_idx * cell_width)
            y0 = table_bbox.y0 + (row_idx * cell_height)
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
