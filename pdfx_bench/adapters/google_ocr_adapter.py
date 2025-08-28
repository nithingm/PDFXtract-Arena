"""
Google Document AI OCR adapter for PDFX-Bench.
Extracts text using Google Document AI Document OCR processor.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords, normalize_confidence
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class GoogleOCRAdapter:
    """Adapter for Google Document AI OCR processor."""
    
    def __init__(
        self,
        processor_id: Optional[str] = None,
        location: str = "us",
        project_id: Optional[str] = None
    ):
        """
        Initialize Google Document AI OCR adapter.
        
        Args:
            processor_id: Document AI OCR processor ID
            location: Processor location
            project_id: GCP project ID
        """
        self.method = ExtractionMethod.GOOGLE_DOCAI_OCR
        self.processor_id = processor_id or os.getenv('GCP_PROCESSOR_ID_OCR')
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
                    "Google Cloud project ID and OCR processor ID are required. "
                    "Set GCP_PROJECT_ID and GCP_PROCESSOR_ID_OCR environment variables "
                    "or provide them via UI."
                )
            
            # Initialize client
            self.client = documentai.DocumentProcessorServiceClient()
            
            # Build processor name
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            logger.debug("Google Document AI OCR client configured successfully")
            
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
        Extract text using Google Document AI OCR processor.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Document AI)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional arguments
            
        Returns:
            Document with extracted text blocks
        """
        logger.info(f"Starting Google OCR extraction: {pdf_path}")
        
        with time_operation("google_ocr_extraction"):
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
                text_blocks = []
                
                # Process pages
                for page_idx, page in enumerate(document_response.pages):
                    page_num = page_idx + 1
                    
                    # Process paragraphs (text blocks)
                    for para_idx, paragraph in enumerate(page.paragraphs):
                        if not paragraph.layout or not paragraph.layout.text_anchor:
                            continue
                        
                        # Extract text from text segments
                        text_segments = []
                        for segment in paragraph.layout.text_anchor.text_segments:
                            start_idx = int(segment.start_index) if segment.start_index else 0
                            end_idx = int(segment.end_index) if segment.end_index else len(document_response.text)
                            text_segments.append(document_response.text[start_idx:end_idx])
                        
                        text_content = ''.join(text_segments).strip()
                        if not text_content:
                            continue
                        
                        # Get confidence
                        confidence = getattr(paragraph.layout, 'confidence', 1.0)
                        if confidence < min_confidence:
                            continue
                        
                        # Create bounding box from layout
                        bbox = self._create_bbox_from_layout(
                            paragraph.layout, page.dimension
                        )
                        
                        text_block = TextBlock(
                            text=text_content,
                            provenance=create_provenance(
                                method=self.method.value,
                                page=page_num,
                                bbox=bbox,
                                confidence=normalize_confidence(confidence, self.method),
                                raw_data={
                                    'paragraph_index': para_idx,
                                    'processor_type': 'OCR',
                                    'processor_id': self.processor_id
                                }
                            )
                        )
                        text_blocks.append(text_block)
                
                # Create document
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=len(document_response.pages),
                    text_blocks=text_blocks,
                    tables=[],  # OCR processor doesn't extract tables
                    key_values=[],
                    extraction_metadata={
                        'method': self.method.value,
                        'processor_type': 'OCR',
                        'processor_id': self.processor_id,
                        'project_id': self.project_id,
                        'location': self.location,
                        'pages_processed': len(document_response.pages),
                        'total_paragraphs': sum(len(page.paragraphs) for page in document_response.pages)
                    }
                )
                
                logger.info(f"Google OCR extraction complete: {len(text_blocks)} text blocks")
                return document
                
            except Exception as e:
                logger.error(f"Google OCR extraction failed: {e}")
                raise
    
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
        """Check if Google OCR adapter is available."""
        try:
            from google.cloud import documentai
            
            # Check credentials from parameters or environment
            processor_id = processor_id or os.getenv('GCP_PROCESSOR_ID_OCR')
            project_id = project_id or os.getenv('GCP_PROJECT_ID')
            
            return bool(processor_id and project_id and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
            
        except ImportError:
            return False
