"""
AWS Textract adapter for PDFX-Bench.
Extracts tables and key-value pairs with confidence scores.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from ..schema import (
    Document, Table, TableCell, KeyValue, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_dict, normalize_confidence
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class TextractAdapter:
    """Adapter for AWS Textract."""
    
    def __init__(self, aws_profile: Optional[str] = None):
        """
        Initialize Textract adapter.
        
        Args:
            aws_profile: AWS profile name to use
        """
        self.method = ExtractionMethod.AWS_TEXTRACT
        self.aws_profile = aws_profile
        self._setup_client()
    
    def _setup_client(self):
        """Set up AWS Textract client."""
        try:
            # Create session with profile if specified
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile)
                self.textract_client = session.client('textract')
            else:
                self.textract_client = boto3.client('textract')
            
            # Test credentials by listing available regions
            self.textract_client.describe_document_text_detection_job(JobId='test')
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise RuntimeError(
                "AWS credentials not configured. Set up AWS CLI or provide "
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
            )
        except ClientError as e:
            # Expected error for test call, but credentials are working
            if e.response['Error']['Code'] != 'InvalidJobIdException':
                logger.error(f"AWS Textract setup failed: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to setup Textract client: {e}")
            raise
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        min_confidence: float = 0.0,
        **kwargs
    ) -> Document:
        """
        Extract content using AWS Textract.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not directly supported by Textract)
            min_confidence: Minimum confidence threshold
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted content
        """
        logger.info(f"Starting AWS Textract extraction: {pdf_path}")
        
        if pages is not None:
            logger.warning("AWS Textract processes entire document, page filtering applied post-extraction")
        
        with time_operation("textract_extraction"):
            try:
                # Read PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_bytes = pdf_file.read()
                
                # Check file size (Textract has limits)
                if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB limit for synchronous
                    logger.warning("PDF file is large, consider using asynchronous Textract")
                
                # Call Textract analyze_document for tables and forms
                response = self.textract_client.analyze_document(
                    Document={'Bytes': pdf_bytes},
                    FeatureTypes=['TABLES', 'FORMS']
                )
                
                # Convert Textract response to our schema
                document = self._convert_textract_response(
                    response, pdf_path, pages, min_confidence
                )
                
                logger.info(
                    f"AWS Textract extraction complete: "
                    f"{len(document.tables)} tables, {len(document.key_values)} key-value pairs"
                )
                
                return document
            
            except ClientError as e:
                logger.error(f"AWS Textract API error: {e}")
                return self._create_error_document(pdf_path, str(e))
            except Exception as e:
                logger.error(f"Textract extraction failed: {e}")
                return self._create_error_document(pdf_path, str(e))
    
    def _convert_textract_response(
        self,
        response: Dict[str, Any],
        pdf_path: Path,
        pages: Optional[List[int]],
        min_confidence: float
    ) -> Document:
        """Convert Textract response to our Document schema."""
        blocks = response.get('Blocks', [])
        
        # Organize blocks by type
        blocks_by_id = {block['Id']: block for block in blocks}
        table_blocks = [b for b in blocks if b['BlockType'] == 'TABLE']
        key_value_blocks = [b for b in blocks if b['BlockType'] == 'KEY_VALUE_SET']
        
        tables = []
        key_values = []
        
        # Process tables
        for table_block in table_blocks:
            table = self._convert_table_block(table_block, blocks_by_id, min_confidence)
            if table and (pages is None or table.provenance.page in pages):
                tables.append(table)
        
        # Process key-value pairs
        for kv_block in key_value_blocks:
            if kv_block.get('EntityTypes') == ['KEY']:
                kv_pair = self._convert_key_value_block(kv_block, blocks_by_id, min_confidence)
                if kv_pair and (pages is None or kv_pair.provenance.page in pages):
                    key_values.append(kv_pair)
        
        # Get page count
        page_blocks = [b for b in blocks if b['BlockType'] == 'PAGE']
        page_count = len(page_blocks)
        
        document = Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=page_count,
            tables=tables,
            key_values=key_values,
            extraction_metadata={
                'method': self.method.value,
                'total_blocks': len(blocks),
                'min_confidence': min_confidence,
                'textract_job_status': response.get('JobStatus', 'SUCCEEDED')
            }
        )
        
        return document
    
    def _convert_table_block(
        self,
        table_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
        min_confidence: float
    ) -> Optional[Table]:
        """Convert Textract table block to Table."""
        try:
            page_num = table_block.get('Page', 1)
            table_id = f"textract_page_{page_num}_table_{table_block['Id']}"
            
            # Get table confidence
            table_confidence = normalize_confidence(
                table_block.get('Confidence'), self.method
            )
            
            if table_confidence is not None and table_confidence < min_confidence:
                logger.debug(f"Skipping table with low confidence: {table_confidence}")
                return None
            
            # Get table bounding box
            table_bbox = None
            if 'Geometry' in table_block:
                table_bbox = create_bbox_from_dict(
                    table_block['Geometry']['BoundingBox']
                )
            
            cells = []
            
            # Process table relationships to get cells
            if 'Relationships' in table_block:
                for relationship in table_block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for cell_id in relationship['Ids']:
                            cell_block = blocks_by_id.get(cell_id)
                            if cell_block and cell_block['BlockType'] == 'CELL':
                                cell = self._convert_cell_block(
                                    cell_block, blocks_by_id, page_num, min_confidence
                                )
                                if cell:
                                    cells.append(cell)
            
            if not cells:
                return None
            
            table_provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=table_bbox,
                confidence=table_confidence,
                raw_data=table_block
            )
            
            table = Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )
            
            return table
        
        except Exception as e:
            logger.warning(f"Failed to convert Textract table: {e}")
            return None
    
    def _convert_cell_block(
        self,
        cell_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
        page_num: int,
        min_confidence: float
    ) -> Optional[TableCell]:
        """Convert Textract cell block to TableCell."""
        try:
            # Get cell position
            row_idx = cell_block.get('RowIndex', 1) - 1  # Convert to 0-based
            col_idx = cell_block.get('ColumnIndex', 1) - 1  # Convert to 0-based
            
            # Get cell confidence
            cell_confidence = normalize_confidence(
                cell_block.get('Confidence'), self.method
            )
            
            if cell_confidence is not None and cell_confidence < min_confidence:
                return None
            
            # Get cell text
            cell_text = ""
            if 'Relationships' in cell_block:
                for relationship in cell_block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for word_id in relationship['Ids']:
                            word_block = blocks_by_id.get(word_id)
                            if word_block and word_block['BlockType'] == 'WORD':
                                if cell_text:
                                    cell_text += " "
                                cell_text += word_block.get('Text', '')
            
            # Get cell bounding box
            cell_bbox = None
            if 'Geometry' in cell_block:
                cell_bbox = create_bbox_from_dict(
                    cell_block['Geometry']['BoundingBox']
                )
            
            provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=cell_bbox,
                confidence=cell_confidence,
                raw_data=cell_block
            )
            
            cell = TableCell(
                raw_text=cell_text.strip(),
                row_idx=row_idx,
                col_idx=col_idx,
                is_header=cell_block.get('EntityTypes') == ['COLUMN_HEADER'],
                provenance=provenance
            )
            
            return cell
        
        except Exception as e:
            logger.warning(f"Failed to convert Textract cell: {e}")
            return None
    
    def _convert_key_value_block(
        self,
        key_block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]],
        min_confidence: float
    ) -> Optional[KeyValue]:
        """Convert Textract key-value block to KeyValue."""
        try:
            page_num = key_block.get('Page', 1)
            
            # Get key confidence
            key_confidence = normalize_confidence(
                key_block.get('Confidence'), self.method
            )
            
            if key_confidence is not None and key_confidence < min_confidence:
                return None
            
            # Get key text
            key_text = self._extract_text_from_block(key_block, blocks_by_id)
            
            # Find corresponding value block
            value_text = ""
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'VALUE':
                        for value_id in relationship['Ids']:
                            value_block = blocks_by_id.get(value_id)
                            if value_block:
                                value_text = self._extract_text_from_block(value_block, blocks_by_id)
                                break
            
            if not key_text.strip():
                return None
            
            # Get bounding box
            bbox = None
            if 'Geometry' in key_block:
                bbox = create_bbox_from_dict(
                    key_block['Geometry']['BoundingBox']
                )
            
            provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=bbox,
                confidence=key_confidence,
                raw_data=key_block
            )
            
            kv_pair = KeyValue(
                key=key_text.strip(),
                value=value_text.strip(),
                provenance=provenance
            )
            
            return kv_pair
        
        except Exception as e:
            logger.warning(f"Failed to convert Textract key-value: {e}")
            return None
    
    def _extract_text_from_block(
        self,
        block: Dict[str, Any],
        blocks_by_id: Dict[str, Dict[str, Any]]
    ) -> str:
        """Extract text from a block and its children."""
        text = ""
        
        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        child_block = blocks_by_id.get(child_id)
                        if child_block and child_block['BlockType'] == 'WORD':
                            if text:
                                text += " "
                            text += child_block.get('Text', '')
        
        return text
    
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
