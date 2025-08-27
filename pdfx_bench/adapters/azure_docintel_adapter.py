"""
Azure Document Intelligence adapter for PDFX-Bench.
Extracts text, tables, and structure using Azure AI Document Intelligence.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, Table, TableCell, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_dict, normalize_confidence, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class AzureDocIntelAdapter:
    """Adapter for Azure Document Intelligence."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Azure Document Intelligence adapter.
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            api_key: Azure API key
        """
        self.method = ExtractionMethod.AZURE_DOCINTEL
        self.endpoint = endpoint or os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        self.api_key = api_key or os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        self._setup_client()
    
    def _setup_client(self):
        """Set up Azure Document Intelligence client."""
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            if not self.endpoint or not self.api_key:
                raise ValueError(
                    "Azure endpoint and API key are required. "
                    "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and "
                    "AZURE_DOCUMENT_INTELLIGENCE_KEY environment variables."
                )
            
            # Initialize client
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
            
            logger.debug("Azure Document Intelligence client configured successfully")
            
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
        Extract content using Azure Document Intelligence.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Azure)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted content
        """
        logger.info(f"Starting Azure Document Intelligence extraction: {pdf_path}")
        
        if pages is not None:
            logger.warning("Azure Document Intelligence processes entire document, page filtering applied post-extraction")
        
        with time_operation("azure_docintel_extraction"):
            try:
                from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
                
                # Read PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_content = pdf_file.read()
                
                # Analyze document using layout model
                poller = self.client.begin_analyze_document(
                    model_id="prebuilt-layout",
                    analyze_request=AnalyzeDocumentRequest(bytes_source=pdf_content)
                )
                
                result = poller.result()
                
                # Convert Azure response to our schema
                document = self._convert_azure_document(
                    result, pdf_path, pages, min_confidence
                )
                
                logger.info(
                    f"Azure Document Intelligence extraction complete: "
                    f"{len(document.text_blocks)} text blocks, {len(document.tables)} tables"
                )
                
                return document
            
            except Exception as e:
                logger.error(f"Azure Document Intelligence extraction failed: {e}")
                return self._create_error_document(pdf_path, str(e))
    
    def _convert_azure_document(
        self,
        azure_result: Any,
        pdf_path: Path,
        pages: Optional[List[int]],
        min_confidence: float
    ) -> Document:
        """Convert Azure Document Intelligence result to our Document schema."""

        text_blocks = []
        tables = []
        key_values = []

        # Process pages
        for page_idx, page in enumerate(azure_result.pages):
            page_num = page_idx + 1

            # Skip if not in requested pages
            if pages and page_num not in pages:
                continue

            # Extract text lines as text blocks
            for line in page.lines:
                text_block = self._convert_text_line(line, page_num, min_confidence)
                if text_block:
                    text_blocks.append(text_block)

        # Process tables
        if hasattr(azure_result, 'tables'):
            for table_idx, table in enumerate(azure_result.tables):
                table_obj = self._convert_azure_table(table, table_idx, min_confidence)
                if table_obj:
                    tables.append(table_obj)

        # Process key-value pairs
        if hasattr(azure_result, 'key_value_pairs'):
            for kv_pair in azure_result.key_value_pairs:
                kv_obj = self._convert_key_value_pair(kv_pair, min_confidence)
                if kv_obj:
                    key_values.append(kv_obj)

        page_count = len(azure_result.pages) if hasattr(azure_result, 'pages') else 1

        return Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=page_count,
            text_blocks=text_blocks,
            tables=tables,
            key_values=key_values,
            extraction_metadata={
                'method': self.method.value,
                'total_pages': page_count,
                'total_tables': len(tables),
                'total_key_values': len(key_values)
            }
        )
    
    def _convert_text_line(self, line: Any, page_num: int, min_confidence: float) -> Optional[TextBlock]:
        """Convert Azure text line to TextBlock."""
        try:
            text = line.content
            if not text or not text.strip():
                return None

            # Get confidence
            confidence = getattr(line, 'confidence', None)

            # Filter by confidence
            if confidence is not None and confidence < min_confidence:
                return None

            # Get bounding box
            bbox = None
            if hasattr(line, 'polygon') and line.polygon:
                bbox = self._convert_polygon_to_bbox(line.polygon)

            provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=bbox,
                confidence=confidence,
                raw_data={'line_type': 'text_line'}
            )

            return TextBlock(
                text=text.strip(),
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Azure text line: {e}")
            return None

    def _convert_azure_table(self, table: Any, table_idx: int, min_confidence: float) -> Optional[Table]:
        """Convert Azure table to Table."""
        try:
            table_id = f"azure_table_{table_idx}"
            cells = []

            # Process table cells
            for cell in table.cells:
                # Get cell position
                row_idx = cell.row_index
                col_idx = cell.column_index

                # Get cell text
                cell_text = cell.content

                # Get confidence
                confidence = getattr(cell, 'confidence', None)

                # Filter by confidence
                if confidence is not None and confidence < min_confidence:
                    continue

                # Get cell bounding box
                cell_bbox = None
                if hasattr(cell, 'bounding_regions') and cell.bounding_regions:
                    # Use first bounding region
                    region = cell.bounding_regions[0]
                    if hasattr(region, 'polygon'):
                        cell_bbox = self._convert_polygon_to_bbox(region.polygon)

                # Determine if header (Azure may provide this info)
                is_header = getattr(cell, 'kind', '') == 'columnHeader'

                provenance = create_provenance(
                    method=self.method,
                    page=getattr(cell.bounding_regions[0], 'page_number', 1) if cell.bounding_regions else 1,
                    bbox=cell_bbox,
                    confidence=confidence,
                    raw_data={
                        'table_index': table_idx,
                        'row_index': row_idx,
                        'col_index': col_idx,
                        'cell_kind': getattr(cell, 'kind', 'content')
                    }
                )

                table_cell = TableCell(
                    raw_text=cell_text.strip() if cell_text else "",
                    row_idx=row_idx,
                    col_idx=col_idx,
                    is_header=is_header,
                    provenance=provenance
                )

                cells.append(table_cell)

            if not cells:
                return None

            # Create table provenance
            table_bbox = None
            if hasattr(table, 'bounding_regions') and table.bounding_regions:
                region = table.bounding_regions[0]
                if hasattr(region, 'polygon'):
                    table_bbox = self._convert_polygon_to_bbox(region.polygon)

            table_provenance = create_provenance(
                method=self.method,
                page=getattr(table.bounding_regions[0], 'page_number', 1) if table.bounding_regions else 1,
                bbox=table_bbox,
                raw_data={
                    'table_index': table_idx,
                    'row_count': table.row_count,
                    'column_count': table.column_count
                }
            )

            return Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Azure table: {e}")
            return None

    def _convert_key_value_pair(self, kv_pair: Any, min_confidence: float) -> Optional[KeyValue]:
        """Convert Azure key-value pair to KeyValue."""
        try:
            # Get key and value
            key_text = kv_pair.key.content if kv_pair.key else ""
            value_text = kv_pair.value.content if kv_pair.value else ""

            if not key_text.strip():
                return None

            # Get confidence (use key confidence)
            confidence = getattr(kv_pair.key, 'confidence', None) if kv_pair.key else None

            # Filter by confidence
            if confidence is not None and confidence < min_confidence:
                return None

            # Get bounding box (use key bbox)
            bbox = None
            if kv_pair.key and hasattr(kv_pair.key, 'bounding_regions') and kv_pair.key.bounding_regions:
                region = kv_pair.key.bounding_regions[0]
                if hasattr(region, 'polygon'):
                    bbox = self._convert_polygon_to_bbox(region.polygon)

            provenance = create_provenance(
                method=self.method,
                page=getattr(kv_pair.key.bounding_regions[0], 'page_number', 1) if kv_pair.key and kv_pair.key.bounding_regions else 1,
                bbox=bbox,
                confidence=confidence,
                raw_data={'pair_type': 'key_value'}
            )

            return KeyValue(
                key=key_text.strip(),
                value=value_text.strip(),
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Azure key-value pair: {e}")
            return None

    def _convert_polygon_to_bbox(self, polygon: List[Any]) -> Optional[BoundingBox]:
        """Convert Azure polygon to BoundingBox."""
        try:
            if not polygon:
                return None

            x_coords = [point.x for point in polygon if hasattr(point, 'x')]
            y_coords = [point.y for point in polygon if hasattr(point, 'y')]

            if x_coords and y_coords:
                return create_bbox_from_coords(
                    min(x_coords), min(y_coords),
                    max(x_coords), max(y_coords)
                )
            return None
        except Exception:
            return None

    def _create_error_document(self, pdf_path: Path, error_msg: str) -> Document:
        """Create an empty document with error information."""
        return Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=1,
            extraction_metadata={
                'method': self.method.value,
                'error': error_msg
            }
        )
