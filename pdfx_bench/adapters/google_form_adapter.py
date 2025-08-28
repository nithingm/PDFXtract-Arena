"""
Google Document AI Form Parser adapter for PDFX-Bench.
Extracts text, tables, and form fields using Google Document AI Form Parser processor.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, Table, TableCell, TextBlock, KeyValue, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords, normalize_confidence
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class GoogleFormAdapter:
    """Adapter for Google Document AI Form Parser processor."""
    
    def __init__(
        self,
        processor_id: Optional[str] = None,
        location: str = "us",
        project_id: Optional[str] = None
    ):
        """
        Initialize Google Document AI Form Parser adapter.
        
        Args:
            processor_id: Document AI Form Parser processor ID
            location: Processor location
            project_id: GCP project ID
        """
        self.method = ExtractionMethod.GOOGLE_DOCAI_FORM
        self.processor_id = processor_id or os.getenv('GCP_PROCESSOR_ID_FORM')
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
                    "Google Cloud project ID and Form Parser processor ID are required. "
                    "Set GCP_PROJECT_ID and GCP_PROCESSOR_ID_FORM environment variables "
                    "or provide them via UI."
                )
            
            # Initialize client
            self.client = documentai.DocumentProcessorServiceClient()
            
            # Build processor name
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            logger.debug("Google Document AI Form Parser client configured successfully")
            
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
        Extract text, tables, and form fields using Google Document AI Form Parser.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Document AI)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional arguments
            
        Returns:
            Document with extracted text blocks, tables, and key-value pairs
        """
        logger.info(f"Starting Google Form Parser extraction: {pdf_path}")
        
        with time_operation("google_form_extraction"):
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
                
                # Extract key-value pairs
                key_values = self._extract_key_values(document_response, min_confidence)
                
                # Create document
                page_count = len(document_response.pages) if document_response.pages else 1
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=page_count,
                    text_blocks=text_blocks,
                    tables=tables,
                    key_values=key_values,
                    extraction_metadata={
                        'method': self.method.value,
                        'processor_type': 'Form Parser',
                        'processor_id': self.processor_id,
                        'project_id': self.project_id,
                        'location': self.location,
                        'pages_processed': len(document_response.pages),
                        'total_paragraphs': sum(len(page.paragraphs) for page in document_response.pages),
                        'total_tables': len(document_response.pages[0].tables) if document_response.pages else 0,
                        'total_form_fields': len(document_response.pages[0].form_fields) if document_response.pages else 0
                    }
                )
                
                logger.info(f"Google Form Parser extraction complete: {len(text_blocks)} text blocks, {len(tables)} tables, {len(key_values)} key-value pairs")
                return document
                
            except Exception as e:
                logger.error(f"Google Form Parser extraction failed: {e}")
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
                            'processor_type': 'Form Parser',
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
                            is_header=False,  # Form parser doesn't distinguish headers
                            provenance=create_provenance(
                                method=self.method.value,
                                page=page_idx + 1,
                                bbox=bbox,
                                confidence=normalize_confidence(confidence, self.method),
                                raw_data={
                                    'table_index': table_idx,
                                    'processor_type': 'Form Parser',
                                    'processor_id': self.processor_id
                                }
                            )
                        )
                        cells.append(table_cell)
                
                if cells:
                    table_obj = Table(
                        cells=cells,
                        table_id=f"google_form_table_{table_idx}",
                        caption=None,
                        provenance=create_provenance(
                            method=self.method.value,
                            page=page_idx + 1,
                            bbox=create_bbox_from_coords(0, 0, page.dimension.width, page.dimension.height),
                            confidence=1.0,
                            raw_data={
                                'table_index': table_idx,
                                'processor_type': 'Form Parser',
                                'processor_id': self.processor_id
                            }
                        )
                    )
                    tables.append(table_obj)
        
        return tables
    
    def _extract_key_values(self, document_response, min_confidence: float) -> List[KeyValue]:
        """Extract key-value pairs from Document AI response."""
        key_values = []
        
        for page_idx, page in enumerate(document_response.pages):
            for field_idx, form_field in enumerate(page.form_fields):
                if not form_field.field_name or not form_field.field_value:
                    continue
                
                # Extract field name
                field_name_text = self._extract_text_from_layout(
                    form_field.field_name, document_response.text
                ).strip()
                
                # Extract field value
                field_value_text = self._extract_text_from_layout(
                    form_field.field_value, document_response.text
                ).strip()
                
                if not field_name_text or not field_value_text:
                    continue
                
                # Get confidence
                confidence = getattr(form_field.field_name, 'confidence', 1.0)
                if confidence < min_confidence:
                    continue
                
                # Create bounding box for the field name
                bbox = self._create_bbox_from_layout(form_field.field_name, page.dimension)
                
                key_value = KeyValue(
                    key=field_name_text,
                    value=field_value_text,
                    provenance=create_provenance(
                        method=self.method.value,
                        page=page_idx + 1,
                        bbox=bbox,
                        confidence=normalize_confidence(confidence, self.method),
                        raw_data={
                            'field_index': field_idx,
                            'processor_type': 'Form Parser',
                            'processor_id': self.processor_id
                        }
                    )
                )
                key_values.append(key_value)
        
        return key_values
    
    def _extract_text_from_layout(self, layout, document_text: str) -> str:
        """Extract text from a layout object."""
        if not layout or not layout.text_anchor:
            return ""
        
        text_segments = []
        for segment in layout.text_anchor.text_segments:
            try:
                start_idx = int(segment.start_index) if hasattr(segment, 'start_index') and segment.start_index is not None else 0
                end_idx = int(segment.end_index) if hasattr(segment, 'end_index') and segment.end_index is not None else len(document_text)
                text_segments.append(document_text[start_idx:end_idx])
            except (AttributeError, TypeError) as e:
                logger.warning(f"Error processing layout segment: {e}, segment: {segment}")
                continue
        
        return ''.join(text_segments)
    
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
        """Check if Google Form Parser adapter is available."""
        try:
            from google.cloud import documentai
            
            # Check credentials from parameters or environment
            processor_id = processor_id or os.getenv('GCP_PROCESSOR_ID_FORM')
            project_id = project_id or os.getenv('GCP_PROJECT_ID')
            
            return bool(processor_id and project_id and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
            
        except ImportError:
            return False
