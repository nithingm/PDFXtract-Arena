"""
Google Document AI Layout Parser adapter for PDFX-Bench.
Extracts text and layout information using Google Document AI Layout Parser processor.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, Table, TableCell, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords, normalize_confidence
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class GoogleLayoutAdapter:
    """Adapter for Google Document AI Layout Parser processor."""
    
    def __init__(
        self,
        processor_id: Optional[str] = None,
        location: str = "us",
        project_id: Optional[str] = None
    ):
        """
        Initialize Google Document AI Layout Parser adapter.
        
        Args:
            processor_id: Document AI Layout Parser processor ID
            location: Processor location
            project_id: GCP project ID
        """
        self.method = ExtractionMethod.GOOGLE_DOCAI_LAYOUT
        self.processor_id = processor_id or os.getenv('GCP_PROCESSOR_ID_LAYOUT')
        self.location = location or os.getenv('GCP_LOCATION', 'us')
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        self._setup_client()
    
    def _setup_client(self):
        """Set up Document AI client."""
        try:
            from google.cloud import documentai
            
            # Check for required configuration
            if not self.project_id or not self.processor_id:
                raise ValueError(
                    "Google Cloud project ID and Layout Parser processor ID are required. "
                    "Set GCP_PROJECT_ID and GCP_PROCESSOR_ID_LAYOUT environment variables "
                    "or provide them via UI."
                )
            
            # Initialize client
            self.client = documentai.DocumentProcessorServiceClient()
            
            # Build processor name
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            logger.debug("Google Document AI Layout Parser client configured successfully")
            
        except ImportError:
            logger.error("Google Cloud Document AI library not installed")
            raise RuntimeError(
                "Google Cloud Document AI library is required. "
                "Install with: pip install google-cloud-documentai"
            )
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        min_confidence: float = 0.0,
        **kwargs
    ) -> Document:
        """
        Extract text and layout using Google Document AI Layout Parser.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Document AI)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional arguments
            
        Returns:
            Document with extracted text blocks and tables
        """
        logger.info(f"Starting Google Layout Parser extraction: {pdf_path}")
        
        with time_operation("google_layout_extraction"):
            try:
                from google.cloud import documentai
                
                # Read PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_content = pdf_file.read()
                
                # Create request
                request = documentai.ProcessRequest(
                    name=self.processor_name,
                    raw_document=documentai.RawDocument(
                        content=pdf_content,
                        mime_type="application/pdf"
                    )
                )
                
                # Process document
                result = self.client.process_document(request=request)
                document_response = result.document
                
                # Extract text blocks
                text_blocks = self._extract_text_blocks(document_response, min_confidence)
                
                # Extract tables
                tables = self._extract_tables(document_response, min_confidence)
                
                # Create document
                page_count = len(document_response.pages) if document_response.pages else 1
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=page_count,
                    text_blocks=text_blocks,
                    tables=tables,
                    key_values=[],  # Layout parser focuses on structure, not form fields
                    extraction_metadata={
                        'method': self.method.value,
                        'processor_type': 'Layout Parser',
                        'processor_id': self.processor_id,
                        'project_id': self.project_id,
                        'location': self.location,
                        'pages_processed': len(document_response.pages),
                        'total_paragraphs': sum(len(page.paragraphs) for page in document_response.pages),
                        'total_tables': len(document_response.pages[0].tables) if document_response.pages else 0
                    }
                )
                
                logger.info(f"Google Layout Parser extraction complete: {len(text_blocks)} text blocks, {len(tables)} tables")
                return document
                
            except Exception as e:
                logger.error(f"Google Layout Parser extraction failed: {e}")
                raise
    
    def _extract_text_blocks(self, document_response, min_confidence: float) -> List[TextBlock]:
        """Extract text blocks from Document AI response."""
        text_blocks = []
        
        for page_idx, page in enumerate(document_response.pages):
            page_num = page_idx + 1
            
            # Process paragraphs
            for para_idx, paragraph in enumerate(page.paragraphs):
                if not paragraph.layout or not paragraph.layout.text_anchor:
                    continue
                
                # Extract text from text segments
                text_segments = []
                for segment in paragraph.layout.text_anchor.text_segments:
                    try:
                        start_idx = int(segment.start_index) if hasattr(segment, 'start_index') and segment.start_index is not None else 0
                        end_idx = int(segment.end_index) if hasattr(segment, 'end_index') and segment.end_index is not None else len(document_response.text)
                        text_segments.append(document_response.text[start_idx:end_idx])
                    except (AttributeError, TypeError) as e:
                        logger.warning(f"Error processing text segment: {e}, segment: {segment}")
                        continue
                
                text_content = ''.join(text_segments).strip()
                if not text_content:
                    continue
                
                # Get confidence
                confidence = getattr(paragraph.layout, 'confidence', 1.0)
                if confidence < min_confidence:
                    continue
                
                # Create bounding box
                bbox = self._create_bbox_from_layout(paragraph.layout, page.dimension)
                
                text_block = TextBlock(
                    text=text_content,
                    provenance=create_provenance(
                        method=self.method.value,
                        page=page_num,
                        bbox=bbox,
                        confidence=normalize_confidence(confidence, self.method),
                        raw_data={
                            'paragraph_index': para_idx,
                            'processor_type': 'Layout Parser',
                            'processor_id': self.processor_id
                        }
                    )
                )
                text_blocks.append(text_block)
        
        return text_blocks
    
    def _extract_tables(self, document_response, min_confidence: float) -> List[Table]:
        """Extract tables from Document AI response."""
        tables = []
        
        for page_idx, page in enumerate(document_response.pages):
            for table_idx, table in enumerate(page.tables):
                cells = []
                
                # Process header rows
                for row in table.header_rows:
                    for cell in row.cells:
                        if not cell.layout or not cell.layout.text_anchor:
                            continue
                        
                        # Extract cell text
                        text_segments = []
                        for segment in cell.layout.text_anchor.text_segments:
                            try:
                                start_idx = int(segment.start_index) if hasattr(segment, 'start_index') and segment.start_index is not None else 0
                                end_idx = int(segment.end_index) if hasattr(segment, 'end_index') and segment.end_index is not None else len(document_response.text)
                                text_segments.append(document_response.text[start_idx:end_idx])
                            except (AttributeError, TypeError) as e:
                                logger.warning(f"Error processing table cell segment: {e}, segment: {segment}")
                                continue
                        
                        cell_text = ''.join(text_segments).strip()
                        
                        # Get confidence
                        confidence = getattr(cell.layout, 'confidence', 1.0)
                        if confidence < min_confidence:
                            continue
                        
                        # Create bounding box
                        bbox = self._create_bbox_from_layout(cell.layout, page.dimension)
                        
                        # Get row and column indices safely
                        try:
                            row_idx = cell.row_span.start_index if cell.row_span and hasattr(cell.row_span, 'start_index') else 0
                        except (AttributeError, TypeError):
                            row_idx = 0

                        try:
                            col_idx = cell.col_span.start_index if cell.col_span and hasattr(cell.col_span, 'start_index') else 0
                        except (AttributeError, TypeError):
                            col_idx = 0

                        table_cell = TableCell(
                            raw_text=cell_text,
                            row_idx=row_idx,
                            col_idx=col_idx,
                            is_header=True,  # This is from header_rows
                            provenance=create_provenance(
                                method=self.method.value,
                                page=page_idx + 1,
                                bbox=bbox,
                                confidence=normalize_confidence(confidence, self.method),
                                raw_data={
                                    'table_index': table_idx,
                                    'is_header': True,
                                    'processor_type': 'Layout Parser',
                                    'processor_id': self.processor_id
                                }
                            )
                        )
                        cells.append(table_cell)
                
                # Process body rows
                for row in table.body_rows:
                    for cell in row.cells:
                        if not cell.layout or not cell.layout.text_anchor:
                            continue
                        
                        # Extract cell text
                        text_segments = []
                        for segment in cell.layout.text_anchor.text_segments:
                            try:
                                start_idx = int(segment.start_index) if hasattr(segment, 'start_index') and segment.start_index is not None else 0
                                end_idx = int(segment.end_index) if hasattr(segment, 'end_index') and segment.end_index is not None else len(document_response.text)
                                text_segments.append(document_response.text[start_idx:end_idx])
                            except (AttributeError, TypeError) as e:
                                logger.warning(f"Error processing table cell segment: {e}, segment: {segment}")
                                continue
                        
                        cell_text = ''.join(text_segments).strip()
                        
                        # Get confidence
                        confidence = getattr(cell.layout, 'confidence', 1.0)
                        if confidence < min_confidence:
                            continue
                        
                        # Create bounding box
                        bbox = self._create_bbox_from_layout(cell.layout, page.dimension)
                        
                        # Get row and column indices safely
                        try:
                            row_idx = cell.row_span.start_index if cell.row_span and hasattr(cell.row_span, 'start_index') else 0
                        except (AttributeError, TypeError):
                            row_idx = 0

                        try:
                            col_idx = cell.col_span.start_index if cell.col_span and hasattr(cell.col_span, 'start_index') else 0
                        except (AttributeError, TypeError):
                            col_idx = 0

                        table_cell = TableCell(
                            raw_text=cell_text,
                            row_idx=row_idx,
                            col_idx=col_idx,
                            is_header=False,  # This is from body_rows
                            provenance=create_provenance(
                                method=self.method.value,
                                page=page_idx + 1,
                                bbox=bbox,
                                confidence=normalize_confidence(confidence, self.method),
                                raw_data={
                                    'table_index': table_idx,
                                    'is_header': False,
                                    'processor_type': 'Layout Parser',
                                    'processor_id': self.processor_id
                                }
                            )
                        )
                        cells.append(table_cell)
                
                if cells:
                    table_obj = Table(
                        cells=cells,
                        table_id=f"google_layout_table_{table_idx}",
                        caption=None,
                        provenance=create_provenance(
                            method=self.method.value,
                            page=page_idx + 1,
                            bbox=create_bbox_from_coords(0, 0, page.dimension.width, page.dimension.height),
                            confidence=1.0,
                            raw_data={
                                'table_index': table_idx,
                                'processor_type': 'Layout Parser',
                                'processor_id': self.processor_id
                            }
                        )
                    )
                    tables.append(table_obj)
        
        return tables
    
    def _create_bbox_from_layout(self, layout, page_dimension) -> BoundingBox:
        """Create bounding box from Document AI layout."""
        if not layout.bounding_poly or not layout.bounding_poly.vertices:
            return create_bbox_from_coords(0, 0, page_dimension.width, page_dimension.height)
        
        vertices = layout.bounding_poly.vertices
        x_coords = [v.x for v in vertices if hasattr(v, 'x')]
        y_coords = [v.y for v in vertices if hasattr(v, 'y')]
        
        if not x_coords or not y_coords:
            return create_bbox_from_coords(0, 0, page_dimension.width, page_dimension.height)
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        return create_bbox_from_coords(x_min, y_min, x_max, y_max)
    
    @staticmethod
    def is_available(
        processor_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> bool:
        """Check if Google Layout Parser adapter is available."""
        try:
            from google.cloud import documentai
            
            # Check credentials from parameters or environment
            processor_id = processor_id or os.getenv('GCP_PROCESSOR_ID_LAYOUT')
            project_id = project_id or os.getenv('GCP_PROJECT_ID')
            
            return bool(processor_id and project_id and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
            
        except ImportError:
            return False
