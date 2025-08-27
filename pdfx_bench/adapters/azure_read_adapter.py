"""
Azure Document Intelligence Read adapter for PDFX-Bench.
Extracts text using Azure AI Document Intelligence prebuilt-read model.
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


class AzureReadAdapter:
    """Adapter for Azure Document Intelligence Read model."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Azure Document Intelligence Read adapter.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            api_key: Azure API key
        """
        self.method = ExtractionMethod.AZURE_READ
        self.endpoint = endpoint or os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        self.api_key = api_key or os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        self._setup_client()
    
    def _setup_client(self):
        """Set up Azure Document Intelligence client."""
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
            from azure.core.credentials import AzureKeyCredential
            
            if not self.endpoint or not self.api_key:
                raise ValueError(
                    "Azure endpoint and API key are required. "
                    "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
                    "AZURE_DOCUMENT_INTELLIGENCE_KEY environment variables "
                    "or provide them via UI."
                )
            
            # Initialize client
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            
            logger.debug("Azure Document Intelligence Read client configured successfully")
            
        except ImportError:
            logger.error("Azure Document Intelligence library not installed")
            raise RuntimeError(
                "Azure Document Intelligence library is required. "
                "Install with: pip install azure-ai-documentintelligence"
            )
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        min_confidence: float = 0.0,
        **kwargs
    ) -> Document:
        """
        Extract text using Azure Document Intelligence Read model.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Azure)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional arguments
            
        Returns:
            Document with extracted text blocks
        """
        logger.info(f"Starting Azure Read extraction: {pdf_path}")
        
        with time_operation("azure_read_extraction"):
            try:
                from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
                
                # Read PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_content = pdf_file.read()
                
                # Analyze document using read model
                poller = self.client.begin_analyze_document(
                    "prebuilt-read",
                    AnalyzeDocumentRequest(bytes_source=pdf_content)
                )
                
                result = poller.result()
                
                # Extract text blocks
                text_blocks = []
                
                # Process pages
                for page in result.pages:
                    page_num = page.page_number
                    
                    # Process lines on this page
                    for line_idx, line in enumerate(page.lines):
                        if line.content and line.content.strip():
                            # Check confidence threshold
                            confidence = getattr(line, 'confidence', 1.0)
                            if confidence < min_confidence:
                                continue
                            
                            # Create bounding box from polygon
                            bbox = self._create_bbox_from_polygon(
                                line.polygon, page.width, page.height
                            )
                            
                            text_block = TextBlock(
                                text=line.content.strip(),
                                provenance=create_provenance(
                                    method=self.method.value,
                                    page=page_num,
                                    bbox=bbox,
                                    confidence=normalize_confidence(confidence, self.method),
                                    raw_data={
                                        'line_index': line_idx,
                                        'model': 'prebuilt-read',
                                        'polygon': line.polygon
                                    }
                                )
                            )
                            text_blocks.append(text_block)
                
                # Create document
                page_count = len(result.pages) if result.pages else 1
                pages_processed = len(result.pages) if result.pages else 1
                total_lines = sum(len(page.lines) for page in result.pages) if result.pages else 0

                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=page_count,
                    text_blocks=text_blocks,
                    tables=[],  # Read model doesn't extract tables
                    key_values=[],
                    extraction_metadata={
                        'method': self.method.value,
                        'model': 'prebuilt-read',
                        'endpoint': self.endpoint,
                        'pages_processed': pages_processed,
                        'total_lines': total_lines
                    }
                )
                
                logger.info(f"Azure Read extraction complete: {len(text_blocks)} text blocks")
                return document
                
            except Exception as e:
                logger.error(f"Azure Read extraction failed: {e}")
                raise
    
    def _create_bbox_from_polygon(self, polygon: List[float], page_width: float, page_height: float) -> BoundingBox:
        """Create bounding box from polygon coordinates."""
        if not polygon or len(polygon) < 8:
            return create_bbox_from_coords(0, 0, page_width, page_height)
        
        # Polygon is [x1, y1, x2, y2, x3, y3, x4, y4]
        x_coords = [polygon[i] for i in range(0, len(polygon), 2)]
        y_coords = [polygon[i] for i in range(1, len(polygon), 2)]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        return create_bbox_from_coords(x_min, y_min, x_max, y_max)
    
    @staticmethod
    def is_available(endpoint: Optional[str] = None, api_key: Optional[str] = None) -> bool:
        """Check if Azure Read adapter is available."""
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            # Check credentials from parameters or environment
            endpoint = endpoint or os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
            api_key = api_key or os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
            
            return bool(endpoint and api_key)
            
        except ImportError:
            return False
