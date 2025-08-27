"""
Adobe PDF Extract API adapter for PDFX-Bench.
Extracts structured JSON with text, tables, and layout information.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from ..schema import (
    Document, Table, TableCell, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_dict, normalize_confidence
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class AdobeExtractAdapter:
    """Adapter for Adobe PDF Extract API."""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize Adobe Extract adapter.
        
        Args:
            credentials_file: Path to Adobe credentials JSON file
        """
        self.method = ExtractionMethod.ADOBE_EXTRACT
        self.credentials_file = credentials_file
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Set up Adobe API credentials."""
        try:
            from adobe.pdfservices.operation.auth.credentials import Credentials
            from adobe.pdfservices.operation.exception.exceptions import ServiceApiException
            from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation
            from adobe.pdfservices.operation.io.file_ref import FileRef
            
            # Check for credentials
            if self.credentials_file and Path(self.credentials_file).exists():
                # Use provided credentials file
                self.credentials = Credentials.service_account_credentials_builder()\
                    .from_file(self.credentials_file)\
                    .build()
            elif os.getenv('ADOBE_CLIENT_ID') and os.getenv('ADOBE_CLIENT_SECRET'):
                # Use environment variables
                self.credentials = Credentials.service_account_credentials_builder()\
                    .with_client_id(os.getenv('ADOBE_CLIENT_ID'))\
                    .with_client_secret(os.getenv('ADOBE_CLIENT_SECRET'))\
                    .build()
            else:
                raise ValueError(
                    "Adobe credentials not found. Provide credentials file or set "
                    "ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET environment variables."
                )
            
            logger.debug("Adobe credentials configured successfully")
            
        except ImportError:
            logger.error("Adobe PDF Services SDK not installed")
            raise RuntimeError(
                "Adobe PDF Services SDK is required. Install with: "
                "pip install pdfservices-sdk"
            )
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract content using Adobe PDF Extract API.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (not supported by Adobe API)
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted content
        """
        logger.info(f"Starting Adobe Extract API extraction: {pdf_path}")
        
        if pages is not None:
            logger.warning("Adobe Extract API does not support page-specific extraction")
        
        with time_operation("adobe_extract_extraction"):
            try:
                from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation
                from adobe.pdfservices.operation.io.file_ref import FileRef
                from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions
                from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
                
                # Create operation
                extract_pdf_operation = ExtractPDFOperation.create_new()
                
                # Set input file
                source = FileRef.create_from_local_file(str(pdf_path))
                extract_pdf_operation.set_input(source)
                
                # Set options to extract text and tables
                extract_pdf_options = ExtractPDFOptions.builder()\
                    .add_elements_to_extract([
                        ExtractElementType.TEXT,
                        ExtractElementType.TABLES
                    ])\
                    .build()
                extract_pdf_operation.set_options(extract_pdf_options)
                
                # Execute operation
                result = extract_pdf_operation.execute(self.credentials)
                
                # Save result to temporary file and read JSON
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                    result.save_as(temp_file.name)
                    
                    # Extract and parse JSON from zip
                    import zipfile
                    with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                        # Find the JSON file in the zip
                        json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
                        if not json_files:
                            raise ValueError("No JSON file found in Adobe Extract result")
                        
                        with zip_ref.open(json_files[0]) as json_file:
                            extract_data = json.load(json_file)
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                # Convert Adobe data to our schema
                document = self._convert_adobe_data(extract_data, pdf_path)
                
                logger.info(
                    f"Adobe Extract API extraction complete: "
                    f"{len(document.text_blocks)} text blocks, {len(document.tables)} tables"
                )
                
                return document
            
            except Exception as e:
                logger.error(f"Adobe Extract API extraction failed: {e}")
                # Return empty document on failure
                return Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=1,  # Unknown
                    extraction_metadata={
                        'method': self.method.value,
                        'error': str(e)
                    }
                )
    
    def _convert_adobe_data(self, extract_data: Dict[str, Any], pdf_path: Path) -> Document:
        """Convert Adobe Extract data to our Document schema."""
        elements = extract_data.get('elements', [])
        
        text_blocks = []
        tables = []
        
        # Process elements
        for element in elements:
            element_type = element.get('Path', '')
            
            if 'Text' in element_type:
                text_block = self._convert_text_element(element)
                if text_block:
                    text_blocks.append(text_block)
            
            elif 'Table' in element_type:
                table = self._convert_table_element(element)
                if table:
                    tables.append(table)
        
        # Get page count from extract data
        page_count = len(extract_data.get('pages', []))
        if page_count == 0:
            page_count = 1
        
        document = Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=page_count,
            text_blocks=text_blocks,
            tables=tables,
            extraction_metadata={
                'method': self.method.value,
                'adobe_version': extract_data.get('version', 'unknown'),
                'total_elements': len(elements)
            }
        )
        
        return document
    
    def _convert_text_element(self, element: Dict[str, Any]) -> Optional[TextBlock]:
        """Convert Adobe text element to TextBlock."""
        try:
            text = element.get('Text', '')
            if not text or not text.strip():
                return None
            
            # Get page number
            page_num = element.get('Page', 1)
            
            # Get bounding box
            bbox = None
            if 'Bounds' in element:
                bounds = element['Bounds']
                bbox = create_bbox_from_dict({
                    'x0': bounds[0], 'y0': bounds[1],
                    'x1': bounds[2], 'y1': bounds[3]
                })
            
            provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=bbox,
                raw_data=element
            )
            
            return TextBlock(
                text=text.strip(),
                provenance=provenance
            )
        
        except Exception as e:
            logger.warning(f"Failed to convert Adobe text element: {e}")
            return None
    
    def _convert_table_element(self, element: Dict[str, Any]) -> Optional[Table]:
        """Convert Adobe table element to Table."""
        try:
            # Get page number
            page_num = element.get('Page', 1)
            
            # Get table data
            table_data = element.get('Table', {})
            if not table_data:
                return None
            
            table_id = f"adobe_page_{page_num}_table_{element.get('ObjectID', 'unknown')}"
            cells = []
            
            # Process table rows
            for row_idx, row in enumerate(table_data.get('Rows', [])):
                for col_idx, cell in enumerate(row.get('Cells', [])):
                    cell_text = cell.get('Text', '').strip()
                    
                    # Get cell bounding box
                    cell_bbox = None
                    if 'Bounds' in cell:
                        bounds = cell['Bounds']
                        cell_bbox = create_bbox_from_dict({
                            'x0': bounds[0], 'y0': bounds[1],
                            'x1': bounds[2], 'y1': bounds[3]
                        })
                    
                    provenance = create_provenance(
                        method=self.method,
                        page=page_num,
                        bbox=cell_bbox,
                        raw_data=cell
                    )
                    
                    table_cell = TableCell(
                        raw_text=cell_text,
                        row_idx=row_idx,
                        col_idx=col_idx,
                        is_header=cell.get('IsHeader', False),
                        provenance=provenance
                    )
                    
                    cells.append(table_cell)
            
            if not cells:
                return None
            
            # Create table provenance
            table_bbox = None
            if 'Bounds' in element:
                bounds = element['Bounds']
                table_bbox = create_bbox_from_dict({
                    'x0': bounds[0], 'y0': bounds[1],
                    'x1': bounds[2], 'y1': bounds[3]
                })
            
            table_provenance = create_provenance(
                method=self.method,
                page=page_num,
                bbox=table_bbox,
                raw_data=element
            )
            
            table = Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )
            
            return table
        
        except Exception as e:
            logger.warning(f"Failed to convert Adobe table element: {e}")
            return None
