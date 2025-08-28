"""
Amazon Textract adapter for PDFX-Bench.
Supports both DetectDocumentText and AnalyzeDocument APIs.
"""

import os
import json
import logging
import io
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..schema import Document, TextBlock, Table, TableCell, ExtractionMethod
from ..utils.logging import setup_logging

logger = setup_logging(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
    logger.warning("Amazon Textract dependencies not available. Install with: pip install boto3")

try:
    import fitz  # PyMuPDF for PDF page manipulation
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. Multi-page PDF handling will be limited. Install with: pip install PyMuPDF")


@dataclass
class TextractMethod:
    """Enumeration of Textract methods."""
    DETECT_TEXT = "detect_text"
    ANALYZE_DOCUMENT = "analyze_document"


class AmazonTextractAdapter:
    """Adapter for Amazon Textract APIs."""

    def __init__(self, method: str = TextractMethod.DETECT_TEXT, 
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_region: Optional[str] = None):
        """
        Initialize Amazon Textract adapter.

        Args:
            method: Textract method to use ('detect_text' or 'analyze_document')
            aws_access_key_id: AWS access key ID (overrides environment variable)
            aws_secret_access_key: AWS secret access key (overrides environment variable)
            aws_region: AWS region (overrides environment variable)
        """
        if not TEXTRACT_AVAILABLE:
            raise RuntimeError("Amazon Textract dependencies not installed. Install with: pip install boto3")
        
        self.method_type = method
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        
        # Set extraction method based on Textract method
        if method == TextractMethod.DETECT_TEXT:
            self.method = ExtractionMethod.AMAZON_TEXTRACT_DETECT
        elif method == TextractMethod.ANALYZE_DOCUMENT:
            self.method = ExtractionMethod.AMAZON_TEXTRACT_ANALYZE
        else:
            raise ValueError(f"Invalid Textract method: {method}")
        
        self._setup_client()

    def _setup_client(self):
        """Set up Amazon Textract client with credentials."""
        try:
            # Use provided credentials or fall back to environment variables
            aws_access_key_id = self.aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = self.aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            
            if not aws_access_key_id or not aws_secret_access_key:
                raise ValueError("AWS credentials not found. Please provide AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            
            # Create Textract client
            self.client = boto3.client(
                'textract',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
            
            logger.info(f"Amazon Textract client initialized for method: {self.method_type}")
            
        except Exception as e:
            logger.error(f"Failed to setup Amazon Textract client: {e}")
            raise

    def extract(self, pdf_path: Path, pages: Optional[List[int]] = None, **kwargs) -> Document:
        """
        Extract content from PDF using Amazon Textract.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Document object with extracted content
        """
        try:
            logger.info(f"Starting Amazon Textract extraction: {pdf_path}")

            # Check if PDF is multi-page and convert to single page if needed
            pdf_bytes, is_multipage, original_page_count = self._prepare_pdf_for_textract(pdf_path)

            # Call appropriate Textract API
            if self.method_type == TextractMethod.DETECT_TEXT:
                response = self._detect_document_text(pdf_bytes)
            elif self.method_type == TextractMethod.ANALYZE_DOCUMENT:
                response = self._analyze_document(pdf_bytes)
            else:
                raise ValueError(f"Unknown method: {self.method_type}")

            # Parse response into Document
            document = self._parse_textract_response(response, pdf_path, is_multipage, original_page_count)

            logger.info(f"Amazon Textract extraction completed: {len(document.text_blocks)} text blocks, {len(document.tables)} tables")
            return document
            
        except Exception as e:
            logger.error(f"Amazon Textract extraction failed: {e}")
            # Return empty document with error metadata
            return Document(
                id=pdf_path.stem,
                file_name=pdf_path.name,
                page_count=1,  # Must be at least 1 per schema requirement
                text_blocks=[],
                tables=[],
                key_values=[],
                extraction_metadata={
                    'method': self.method.value,
                    'error': str(e)
                }
            )

    def _prepare_pdf_for_textract(self, pdf_path: Path) -> tuple[bytes, bool, int]:
        """
        Prepare PDF for Textract processing.
        For multi-page PDFs, extract only the first page since Textract synchronous APIs
        only support single-page documents.

        Returns:
            tuple: (pdf_bytes, is_multipage, original_page_count)
        """
        try:
            # First, try to get page count using PyMuPDF if available
            if PYMUPDF_AVAILABLE:
                doc = fitz.open(pdf_path)
                page_count = len(doc)

                if page_count == 1:
                    # Single page - read normally
                    doc.close()
                    with open(pdf_path, 'rb') as file:
                        return file.read(), False, 1
                else:
                    # Multi-page - extract first page only
                    logger.warning(f"Multi-page PDF detected ({page_count} pages). Amazon Textract synchronous APIs only support single-page documents. Extracting first page only.")

                    # Create new PDF with only first page
                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=0, to_page=0)

                    # Convert to bytes
                    pdf_bytes = new_doc.tobytes()

                    # Clean up
                    doc.close()
                    new_doc.close()

                    return pdf_bytes, True, page_count
            else:
                # PyMuPDF not available - read normally and let Textract handle the error
                logger.warning("PyMuPDF not available. Cannot detect multi-page PDFs. If this is a multi-page PDF, extraction may fail.")
                with open(pdf_path, 'rb') as file:
                    return file.read(), False, 1

        except Exception as e:
            logger.warning(f"Error preparing PDF for Textract: {e}. Reading PDF normally.")
            # Fallback to normal reading
            with open(pdf_path, 'rb') as file:
                return file.read(), False, 1

    def _detect_document_text(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Call DetectDocumentText API."""
        try:
            response = self.client.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            return response
        except ClientError as e:
            logger.error(f"DetectDocumentText API error: {e}")
            raise
        except Exception as e:
            logger.error(f"DetectDocumentText failed: {e}")
            raise

    def _analyze_document(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Call AnalyzeDocument API with TABLES and FORMS features."""
        try:
            response = self.client.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES', 'FORMS']
            )
            return response
        except ClientError as e:
            logger.error(f"AnalyzeDocument API error: {e}")
            raise
        except Exception as e:
            logger.error(f"AnalyzeDocument failed: {e}")
            raise

    def _parse_textract_response(self, response: Dict[str, Any], pdf_path: Path, is_multipage: bool = False, original_page_count: int = 1) -> Document:
        """Parse Textract response into Document object."""
        blocks = response.get('Blocks', [])
        document_metadata = response.get('DocumentMetadata', {})
        page_count = document_metadata.get('Pages', 1)
        
        # Group blocks by type
        blocks_by_type = {}
        blocks_by_id = {}
        
        for block in blocks:
            block_type = block['BlockType']
            block_id = block['Id']
            
            if block_type not in blocks_by_type:
                blocks_by_type[block_type] = []
            blocks_by_type[block_type].append(block)
            blocks_by_id[block_id] = block
        
        # Extract text blocks (from LINE blocks)
        text_blocks = self._extract_text_blocks(blocks_by_type.get('LINE', []))
        
        # Extract tables (from TABLE and CELL blocks)
        tables = self._extract_tables(blocks_by_type, blocks_by_id)
        
        # Prepare extraction metadata
        metadata = {
            'method': self.method.value,
            'total_blocks': len(blocks),
            'block_types': list(blocks_by_type.keys())
        }

        # Add multi-page warning if applicable
        if is_multipage:
            metadata['multipage_warning'] = f"Original PDF had {original_page_count} pages. Only first page was processed due to Amazon Textract synchronous API limitations."
            metadata['original_page_count'] = original_page_count
            metadata['processed_pages'] = 1

        return Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=1 if is_multipage else page_count,  # Always 1 for multi-page since we only process first page
            text_blocks=text_blocks,
            tables=tables,
            key_values=[],  # TODO: Implement key-value extraction from KEY_VALUE_SET blocks
            extraction_metadata=metadata
        )

    def _extract_text_blocks(self, line_blocks: List[Dict[str, Any]]) -> List[TextBlock]:
        """Extract text blocks from LINE blocks."""
        text_blocks = []
        
        for line_block in line_blocks:
            text = line_block.get('Text', '')
            if not text.strip():
                continue
            
            # Get geometry information
            geometry = line_block.get('Geometry', {})
            bbox = geometry.get('BoundingBox', {})
            page = line_block.get('Page', 1)
            confidence = line_block.get('Confidence')
            # Convert confidence from 0-100 to 0-1
            if confidence is not None:
                confidence = confidence / 100.0
            
            text_block = TextBlock(
                text=text,
                provenance={
                    'method': self.method.value,
                    'page': page,
                    'bbox': {
                        'x0': bbox.get('Left', 0),
                        'y0': bbox.get('Top', 0),
                        'x1': bbox.get('Left', 0) + bbox.get('Width', 0),
                        'y1': bbox.get('Top', 0) + bbox.get('Height', 0)
                    },
                    'confidence': confidence,
                    'raw_data': {
                        'block_id': line_block['Id'],
                        'block_type': line_block['BlockType']
                    }
                }
            )
            text_blocks.append(text_block)
        
        return text_blocks

    def _extract_tables(self, blocks_by_type: Dict[str, List], blocks_by_id: Dict[str, Dict]) -> List[Table]:
        """Extract tables from TABLE and CELL blocks."""
        tables = []
        table_blocks = blocks_by_type.get('TABLE', [])
        
        for table_block in table_blocks:
            # Get table cells through relationships
            cell_ids = []
            relationships = table_block.get('Relationships', [])
            
            for relationship in relationships:
                if relationship['Type'] == 'CHILD':
                    cell_ids.extend(relationship['Ids'])
            
            # Group cells by row
            cells_by_row = {}
            for cell_id in cell_ids:
                cell_block = blocks_by_id.get(cell_id)
                if cell_block and cell_block['BlockType'] == 'CELL':
                    row_index = cell_block.get('RowIndex', 1)
                    if row_index not in cells_by_row:
                        cells_by_row[row_index] = []
                    cells_by_row[row_index].append(cell_block)
            
            # Create table cells
            all_cells = []
            for row_index in sorted(cells_by_row.keys()):
                row_cells = sorted(cells_by_row[row_index], key=lambda c: c.get('ColumnIndex', 1))

                for col_idx, cell_block in enumerate(row_cells):
                    cell_text = cell_block.get('Text', '')
                    confidence = cell_block.get('Confidence')
                    # Convert confidence from 0-100 to 0-1
                    if confidence is not None:
                        confidence = confidence / 100.0
                    page = cell_block.get('Page', 1)

                    # Get cell geometry
                    geometry = cell_block.get('Geometry', {})
                    bbox = geometry.get('BoundingBox', {})

                    cell = TableCell(
                        raw_text=cell_text,
                        row_idx=row_index - 1,  # Convert to 0-based
                        col_idx=col_idx,
                        is_header=(row_index == 1),  # First row is header
                        provenance={
                            'method': self.method.value,
                            'page': page,
                            'bbox': {
                                'x0': bbox.get('Left', 0),
                                'y0': bbox.get('Top', 0),
                                'x1': bbox.get('Left', 0) + bbox.get('Width', 0),
                                'y1': bbox.get('Top', 0) + bbox.get('Height', 0)
                            },
                            'confidence': confidence,
                            'raw_data': {
                                'cell_id': cell_block['Id'],
                                'row_span': cell_block.get('RowSpan', 1),
                                'col_span': cell_block.get('ColumnSpan', 1)
                            }
                        }
                    )
                    all_cells.append(cell)
            
            if all_cells:  # Only add table if it has cells
                # Get table geometry
                geometry = table_block.get('Geometry', {})
                bbox = geometry.get('BoundingBox', {})
                page = table_block.get('Page', 1)
                confidence = table_block.get('Confidence')
                # Convert confidence from 0-100 to 0-1
                if confidence is not None:
                    confidence = confidence / 100.0

                table = Table(
                    cells=all_cells,
                    table_id=table_block['Id'],
                    provenance={
                        'method': self.method.value,
                        'page': page,
                        'bbox': {
                            'x0': bbox.get('Left', 0),
                            'y0': bbox.get('Top', 0),
                            'x1': bbox.get('Left', 0) + bbox.get('Width', 0),
                            'y1': bbox.get('Top', 0) + bbox.get('Height', 0)
                        },
                        'confidence': confidence,
                        'raw_data': {
                            'table_id': table_block['Id'],
                            'cell_count': len(cell_ids)
                        }
                    }
                )
                tables.append(table)
        
        return tables
