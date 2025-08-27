"""
PDFPlumber adapter for PDFX-Bench.
Extracts text and simple tables using pdfplumber.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pdfplumber
from ..schema import (
    Document, Table, TableCell, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class PDFPlumberAdapter:
    """Adapter for pdfplumber extraction."""
    
    def __init__(self):
        self.method = ExtractionMethod.PDFPLUMBER
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract text and tables using pdfplumber.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-based), None for all
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted content
        """
        logger.info(f"Starting pdfplumber extraction: {pdf_path}")
        
        with time_operation("pdfplumber_extraction"):
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                
                # Determine pages to process
                if pages is None:
                    pages_to_process = list(range(1, page_count + 1))
                else:
                    pages_to_process = [p for p in pages if 1 <= p <= page_count]
                
                text_blocks = []
                tables = []
                
                for page_num in pages_to_process:
                    page = pdf.pages[page_num - 1]  # Convert to 0-based
                    
                    # Extract text blocks
                    page_text_blocks = self._extract_text_blocks(page, page_num)
                    text_blocks.extend(page_text_blocks)
                    
                    # Extract tables
                    page_tables = self._extract_tables(page, page_num)
                    tables.extend(page_tables)
                
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=page_count,
                    text_blocks=text_blocks,
                    tables=tables,
                    extraction_metadata={
                        'method': self.method.value,
                        'pages_processed': pages_to_process,
                        'pdfplumber_version': pdfplumber.__version__
                    }
                )
                
                logger.info(
                    f"pdfplumber extraction complete: {len(text_blocks)} text blocks, "
                    f"{len(tables)} tables"
                )
                
                return document
    
    def _extract_text_blocks(self, page, page_num: int) -> List[TextBlock]:
        """Extract text blocks from a page."""
        text_blocks = []
        
        try:
            # Get all text objects with their bounding boxes
            chars = page.chars
            
            if not chars:
                return text_blocks
            
            # Group characters into text blocks (simple approach)
            # In a more sophisticated implementation, you might group by
            # proximity, font, or other characteristics
            
            # For now, extract the full page text as one block
            page_text = page.extract_text()
            
            if page_text and page_text.strip():
                # Get page bbox
                page_bbox = create_bbox_from_coords(
                    x0=0, y0=0,
                    x1=page.width, y1=page.height
                )
                
                provenance = create_provenance(
                    method=self.method,
                    page=page_num,
                    bbox=page_bbox,
                    raw_data={'page_width': page.width, 'page_height': page.height}
                )
                
                text_block = TextBlock(
                    text=page_text.strip(),
                    provenance=provenance
                )
                
                text_blocks.append(text_block)
        
        except Exception as e:
            logger.warning(f"Failed to extract text from page {page_num}: {e}")
        
        return text_blocks
    
    def _extract_tables(self, page, page_num: int) -> List[Table]:
        """Extract tables from a page."""
        tables = []
        
        try:
            # Extract tables using pdfplumber
            page_tables = page.extract_tables()
            
            for table_idx, table_data in enumerate(page_tables):
                if not table_data:
                    continue
                
                table_id = f"page_{page_num}_table_{table_idx}"
                cells = []
                
                # Convert table data to cells
                for row_idx, row in enumerate(table_data):
                    if row is None:
                        continue
                    
                    for col_idx, cell_text in enumerate(row):
                        if cell_text is None:
                            cell_text = ""
                        
                        # Create cell bbox (approximate)
                        # pdfplumber doesn't provide exact cell bboxes easily
                        cell_bbox = self._estimate_cell_bbox(
                            page, row_idx, col_idx, len(table_data), len(row)
                        )
                        
                        provenance = create_provenance(
                            method=self.method,
                            page=page_num,
                            bbox=cell_bbox,
                            raw_data={
                                'table_index': table_idx,
                                'row_index': row_idx,
                                'col_index': col_idx
                            }
                        )
                        
                        cell = TableCell(
                            raw_text=str(cell_text).strip(),
                            row_idx=row_idx,
                            col_idx=col_idx,
                            is_header=(row_idx == 0),  # Assume first row is header
                            provenance=provenance
                        )
                        
                        cells.append(cell)
                
                if cells:
                    table_provenance = create_provenance(
                        method=self.method,
                        page=page_num,
                        raw_data={
                            'table_index': table_idx,
                            'rows': len(table_data),
                            'cols': len(table_data[0]) if table_data else 0
                        }
                    )
                    
                    table = Table(
                        cells=cells,
                        table_id=table_id,
                        provenance=table_provenance
                    )
                    
                    tables.append(table)
        
        except Exception as e:
            logger.warning(f"Failed to extract tables from page {page_num}: {e}")
        
        return tables
    
    def _estimate_cell_bbox(
        self,
        page,
        row_idx: int,
        col_idx: int,
        total_rows: int,
        total_cols: int
    ) -> Optional[BoundingBox]:
        """Estimate cell bounding box based on page dimensions."""
        try:
            # Simple estimation - divide page into grid
            page_width = page.width
            page_height = page.height
            
            cell_width = page_width / total_cols
            cell_height = page_height / total_rows
            
            x0 = col_idx * cell_width
            y0 = row_idx * cell_height
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            
            return create_bbox_from_coords(x0, y0, x1, y1)
        
        except Exception:
            return None
