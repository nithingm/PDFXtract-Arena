"""
Google Document AI adapter for PDFX-Bench.
Extracts key-value pairs and tables using Google Document AI Form Parser.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, Table, TableCell, KeyValue, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_dict, normalize_confidence, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class DocumentAIAdapter:
    """Adapter for Google Document AI."""
    
    def __init__(
        self,
        processor_id: Optional[str] = None,
        location: str = "us",
        project_id: Optional[str] = None
    ):
        """
        Initialize Document AI adapter.
        
        Args:
            processor_id: Document AI processor ID
            location: Processor location
            project_id: GCP project ID
        """
        self.method = ExtractionMethod.GOOGLE_DOCAI
        self.processor_id = processor_id
        self.location = location
        self.project_id = project_id
        self._setup_client()
    
    def _setup_client(self):
        """Set up Document AI client."""
        try:
            from google.cloud import documentai
            import os
            
            # Check for required configuration
            self.project_id = self.project_id or os.getenv('GCP_PROJECT_ID')
            self.processor_id = self.processor_id or os.getenv('GCP_PROCESSOR_ID')
            
            if not self.project_id or not self.processor_id:
                raise ValueError(
                    "GCP project ID and processor ID are required. "
                    "Set GCP_PROJECT_ID and GCP_PROCESSOR_ID environment variables."
                )
            
            # Initialize client
            self.client = documentai.DocumentProcessorServiceClient()
            
            # Build processor name
            self.processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
            
            logger.debug("Document AI client configured successfully")
            
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
        Extract content using Google Document AI.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Document AI)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted content
        """
        logger.info(f"Starting Google Document AI extraction: {pdf_path}")
        
        if pages is not None:
            logger.warning("Google Document AI processes entire document, page filtering applied post-extraction")
        
        with time_operation("docai_extraction"):
            try:
                from google.cloud import documentai
                
                # Read PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_content = pdf_file.read()
                
                # Create request
                raw_document = documentai.RawDocument(
                    content=pdf_content,
                    mime_type="application/pdf"
                )
                
                request = documentai.ProcessRequest(
                    name=self.processor_name,
                    raw_document=raw_document
                )
                
                # Process document
                result = self.client.process_document(request=request)
                document_ai_doc = result.document
                
                # Convert Document AI response to our schema
                document = self._convert_docai_document(
                    document_ai_doc, pdf_path, pages, min_confidence
                )
                
                logger.info(
                    f"Google Document AI extraction complete: "
                    f"{len(document.tables)} tables, {len(document.key_values)} key-value pairs"
                )
                
                return document
            
            except Exception as e:
                logger.error(f"Google Document AI extraction failed: {e}")
                return self._create_error_document(pdf_path, str(e))
    
    def _convert_docai_document(
        self,
        docai_doc: Any,
        pdf_path: Path,
        pages: Optional[List[int]],
        min_confidence: float
    ) -> Document:
        """Convert Document AI document to our Document schema."""

        text_blocks = []
        tables = []
        key_values = []

        # Process pages
        for page_idx, page in enumerate(docai_doc.pages):
            page_num = page_idx + 1

            # Skip if not in requested pages
            if pages and page_num not in pages:
                continue

            # Extract text blocks
            for block in page.blocks:
                text_block = self._convert_text_block(block, page_num, min_confidence)
                if text_block:
                    text_blocks.append(text_block)

            # Extract tables
            for table_idx, table in enumerate(page.tables):
                table_obj = self._convert_table(table, page_num, table_idx, min_confidence)
                if table_obj:
                    tables.append(table_obj)

        # Extract form fields (key-value pairs)
        for form_field in docai_doc.form_fields:
            kv_pair = self._convert_form_field(form_field, min_confidence)
            if kv_pair:
                key_values.append(kv_pair)

        return Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=len(docai_doc.pages),
            text_blocks=text_blocks,
            tables=tables,
            key_values=key_values,
            extraction_metadata={
                'method': self.method.value,
                'total_pages': len(docai_doc.pages),
                'total_form_fields': len(docai_doc.form_fields)
            }
        )
    
    def _convert_text_block(self, block: Any, page_num: int, min_confidence: float) -> Optional[TextBlock]:
        """Convert Document AI text block to TextBlock."""
        try:
            # Get text content
            text = ""
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    for symbol in word.symbols:
                        text += symbol.text
                    text += " "
                text += "\n"

            if not text.strip():
                return None

            # Get confidence (average of word confidences)
            confidences = []
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    if hasattr(word, 'confidence'):
                        confidences.append(word.confidence)

            avg_confidence = sum(confidences) / len(confidences) if confidences else None

            # Filter by confidence
            if avg_confidence is not None and avg_confidence < min_confidence:
                return None

            # Get bounding box
            bbox = None
            if hasattr(block, 'bounding_box') and block.bounding_box:
                bbox = self._convert_bounding_box(block.bounding_box)

            provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=bbox,
                confidence=avg_confidence,
                raw_data={'block_type': 'text_block'}
            )

            return TextBlock(
                text=text.strip(),
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Document AI text block: {e}")
            return None

    def _convert_table(self, table: Any, page_num: int, table_idx: int, min_confidence: float) -> Optional[Table]:
        """Convert Document AI table to Table."""
        try:
            table_id = f"docai_page_{page_num}_table_{table_idx}"
            cells = []

            # Process table rows
            for row_idx, row in enumerate(table.body_rows):
                for col_idx, cell in enumerate(row.cells):
                    cell_text = ""
                    confidences = []

                    # Extract text from cell
                    for element in cell.layout.text_anchor.text_segments:
                        # This would need the full document text to extract properly
                        # Simplified implementation
                        cell_text += getattr(element, 'content', '')

                    # Get cell confidence
                    if hasattr(cell, 'confidence'):
                        confidences.append(cell.confidence)

                    avg_confidence = sum(confidences) / len(confidences) if confidences else None

                    # Filter by confidence
                    if avg_confidence is not None and avg_confidence < min_confidence:
                        continue

                    # Get cell bounding box
                    cell_bbox = None
                    if hasattr(cell, 'layout') and hasattr(cell.layout, 'bounding_poly'):
                        cell_bbox = self._convert_bounding_box(cell.layout.bounding_poly)

                    provenance = create_provenance(
                        method=self.method,
                        page=page_num,
                        bbox=cell_bbox,
                        confidence=avg_confidence,
                        raw_data={'table_index': table_idx, 'row_index': row_idx, 'col_index': col_idx}
                    )

                    table_cell = TableCell(
                        raw_text=cell_text.strip(),
                        row_idx=row_idx,
                        col_idx=col_idx,
                        is_header=False,  # Document AI doesn't clearly distinguish headers
                        provenance=provenance
                    )

                    cells.append(table_cell)

            if not cells:
                return None

            # Create table provenance
            table_bbox = None
            if hasattr(table, 'layout') and hasattr(table.layout, 'bounding_poly'):
                table_bbox = self._convert_bounding_box(table.layout.bounding_poly)

            table_provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=table_bbox,
                raw_data={'table_index': table_idx, 'rows': len(table.body_rows)}
            )

            return Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Document AI table: {e}")
            return None

    def _convert_form_field(self, form_field: Any, min_confidence: float) -> Optional[KeyValue]:
        """Convert Document AI form field to KeyValue."""
        try:
            # Extract field name (key)
            field_name = ""
            if hasattr(form_field, 'field_name') and form_field.field_name:
                field_name = getattr(form_field.field_name, 'text_anchor', {}).get('content', '')

            # Extract field value
            field_value = ""
            if hasattr(form_field, 'field_value') and form_field.field_value:
                field_value = getattr(form_field.field_value, 'text_anchor', {}).get('content', '')

            if not field_name.strip():
                return None

            # Get confidence
            confidence = getattr(form_field, 'confidence', None)

            # Filter by confidence
            if confidence is not None and confidence < min_confidence:
                return None

            # Get bounding box (use field name bbox)
            bbox = None
            if hasattr(form_field, 'field_name') and hasattr(form_field.field_name, 'bounding_poly'):
                bbox = self._convert_bounding_box(form_field.field_name.bounding_poly)

            provenance = create_provenance(
                method=self.method,
                page=1,  # Form fields don't always have clear page numbers
                bbox=bbox,
                confidence=confidence,
                raw_data={'field_type': 'form_field'}
            )

            return KeyValue(
                key=field_name.strip(),
                value=field_value.strip(),
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Document AI form field: {e}")
            return None

    def _convert_bounding_box(self, bounding_poly: Any) -> Optional[BoundingBox]:
        """Convert Document AI bounding poly to BoundingBox."""
        try:
            if hasattr(bounding_poly, 'vertices') and bounding_poly.vertices:
                vertices = bounding_poly.vertices
                x_coords = [v.x for v in vertices if hasattr(v, 'x')]
                y_coords = [v.y for v in vertices if hasattr(v, 'y')]

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
