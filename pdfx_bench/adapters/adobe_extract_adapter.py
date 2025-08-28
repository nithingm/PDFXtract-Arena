"""
Adobe PDF Extract API adapter for PDFX-Bench.
Extracts structured JSON with text, tables, and layout information using Adobe PDF Services SDK v4.2.0.
"""

import logging
import os
import tempfile
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..schema import (
    Document, Table, TableCell, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_dict, normalize_confidence
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class AdobeExtractAdapter:
    """Adapter for Adobe PDF Extract API using the latest SDK v4.2.0."""

    def __init__(self, credentials_file: Optional[str] = None, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize Adobe Extract adapter.

        Args:
            credentials_file: Path to Adobe credentials JSON file
            client_id: Adobe client ID (overrides environment variable)
            client_secret: Adobe client secret (overrides environment variable)
        """
        self.method = ExtractionMethod.ADOBE_EXTRACT
        self.credentials_file = credentials_file
        self.client_id = client_id
        self.client_secret = client_secret
        self._setup_credentials()

    def _setup_credentials(self):
        """Set up Adobe API credentials using the latest SDK."""
        try:
            from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
            from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
            from adobe.pdfservices.operation.pdf_services import PDFServices

            # Check for credentials
            if self.credentials_file and Path(self.credentials_file).exists():
                # Use provided credentials file
                logger.info(f"Using Adobe credentials from file: {self.credentials_file}")
                # For JSON file, we need to read and extract client_id and client_secret
                with open(self.credentials_file, 'r') as f:
                    creds_data = json.load(f)
                    client_id = creds_data.get('client_credentials', {}).get('client_id')
                    client_secret = creds_data.get('client_credentials', {}).get('client_secret')

                if not client_id or not client_secret:
                    raise ValueError("Invalid credentials file format. Missing client_id or client_secret.")

                self.credentials = ServicePrincipalCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                )
            elif self.client_id and self.client_secret:
                # Use provided credentials
                logger.info("Using Adobe credentials from parameters")
                self.credentials = ServicePrincipalCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            elif os.getenv('ADOBE_CLIENT_ID') and os.getenv('ADOBE_CLIENT_SECRET'):
                # Use environment variables
                logger.info("Using Adobe credentials from environment variables")
                self.credentials = ServicePrincipalCredentials(
                    client_id=os.getenv('ADOBE_CLIENT_ID'),
                    client_secret=os.getenv('ADOBE_CLIENT_SECRET')
                )
            else:
                raise ValueError(
                    "Adobe credentials not found. Provide credentials file or set "
                    "ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET environment variables."
                )

            # Test credentials by creating PDFServices instance
            self.pdf_services = PDFServices(credentials=self.credentials)
            logger.info("Adobe PDF Services credentials configured successfully")

        except ImportError as e:
            logger.error(f"Adobe PDF Services SDK not installed: {e}")
            raise RuntimeError(
                "Adobe PDF Services SDK is required. Install with: "
                "pip install pdfservices-sdk"
            )
        except Exception as e:
            logger.error(f"Failed to setup Adobe credentials: {e}")
            raise

    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract content using Adobe PDF Extract API with the latest SDK.

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
                from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
                from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
                from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import ExtractElementType
                from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import ExtractPDFParams
                from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult
                from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
                from adobe.pdfservices.operation.io.stream_asset import StreamAsset

                # Read PDF file
                with open(pdf_path, 'rb') as file:
                    input_stream = file.read()

                # Upload the PDF to Adobe services
                input_asset = self.pdf_services.upload(
                    input_stream=input_stream,
                    mime_type=PDFServicesMediaType.PDF
                )

                # Create parameters for the job - extract text, tables, and styling info
                extract_pdf_params = ExtractPDFParams(
                    elements_to_extract=[
                        ExtractElementType.TEXT,
                        ExtractElementType.TABLES
                    ],
                    styling_info=True,  # Get styling information for better parsing
                )

                # Create the extraction job
                extract_pdf_job = ExtractPDFJob(
                    input_asset=input_asset,
                    extract_pdf_params=extract_pdf_params
                )

                # Submit the job and get the result
                location = self.pdf_services.submit(extract_pdf_job)
                pdf_services_response = self.pdf_services.get_job_result(location, ExtractPDFResult)

                # Get content from the resulting asset
                result_asset: CloudAsset = pdf_services_response.get_result().get_resource()
                stream_asset: StreamAsset = self.pdf_services.get_content(result_asset)

                # Save to temporary file and extract JSON
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                    temp_file.write(stream_asset.get_input_stream())
                    temp_file_path = temp_file.name

                # Extract and parse JSON from zip
                extract_data = None
                with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                    # Look for structuredData.json (the main extraction result)
                    if 'structuredData.json' in zip_ref.namelist():
                        with zip_ref.open('structuredData.json') as json_file:
                            extract_data = json.load(json_file)
                    else:
                        # Fallback: find any JSON file
                        json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
                        if not json_files:
                            raise ValueError("No JSON file found in Adobe Extract result")

                        with zip_ref.open(json_files[0]) as json_file:
                            extract_data = json.load(json_file)

                # Clean up temp file
                os.unlink(temp_file_path)

                if not extract_data:
                    raise ValueError("Failed to extract JSON data from Adobe result")

                # Convert Adobe data to our schema
                document = self._convert_adobe_data(extract_data, pdf_path)

                logger.info(
                    f"Adobe Extract API extraction complete: "
                    f"{len(document.text_blocks)} text blocks, {len(document.tables)} tables"
                )

                return document

            except Exception as e:
                logger.error(f"Adobe Extract API extraction failed: {e}")
                import traceback
                logger.debug(f"Full traceback: {traceback.format_exc()}")

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

        logger.debug(f"Processing {len(elements)} Adobe elements")

        # Process elements
        for i, element in enumerate(elements):
            try:
                element_path = element.get('Path', '')
                element_text = element.get('Text', '')

                # Skip empty elements
                if not element_text or not element_text.strip():
                    continue

                # Determine element type based on Path
                if self._is_text_element(element_path):
                    text_block = self._convert_text_element(element, i)
                    if text_block:
                        text_blocks.append(text_block)

                elif self._is_table_element(element_path):
                    # Tables are handled differently - they have child elements
                    table = self._convert_table_element(element, elements, i)
                    if table:
                        tables.append(table)

            except Exception as e:
                logger.warning(f"Failed to process Adobe element {i}: {e}")
                continue

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
                'total_elements': len(elements),
                'processed_text_blocks': len(text_blocks),
                'processed_tables': len(tables)
            }
        )

        logger.debug(f"Converted Adobe data: {len(text_blocks)} text blocks, {len(tables)} tables")
        return document

    def _is_text_element(self, path: str) -> bool:
        """Check if element is a text element based on its path."""
        text_indicators = ['/P', '/H1', '/H2', '/H3', '/H4', '/H5', '/H6', '/Span', '/Text']
        return any(indicator in path for indicator in text_indicators)

    def _is_table_element(self, path: str) -> bool:
        """Check if element is a table element based on its path."""
        return '/Table' in path and '/TR' not in path and '/TD' not in path
    
    def _convert_text_element(self, element: Dict[str, Any], element_index: int) -> Optional[TextBlock]:
        """Convert Adobe text element to TextBlock."""
        try:
            text = element.get('Text', '')
            if not text or not text.strip():
                return None

            # Get page number from element (Adobe uses 0-based, we need 1-based)
            page_num = element.get('Page', 0) + 1

            # Get bounding box from Bounds array [x0, y0, x1, y1]
            bbox = None
            if 'Bounds' in element and len(element['Bounds']) >= 4:
                bounds = element['Bounds']
                bbox = create_bbox_from_dict({
                    'x0': bounds[0], 'y0': bounds[1],
                    'x1': bounds[2], 'y1': bounds[3]
                })

            # Determine block type from path
            path = element.get('Path', '')
            block_type = 'paragraph'
            if '/H1' in path:
                block_type = 'heading1'
            elif '/H2' in path:
                block_type = 'heading2'
            elif '/H3' in path:
                block_type = 'heading3'
            elif '/H4' in path:
                block_type = 'heading4'
            elif '/H5' in path:
                block_type = 'heading5'
            elif '/H6' in path:
                block_type = 'heading6'

            # Get font information if available
            font_info = {}
            if 'attributes' in element:
                attrs = element['attributes']
                if 'FontSize' in attrs:
                    font_info['font_size'] = attrs['FontSize']
                if 'FontName' in attrs:
                    font_info['font_name'] = attrs['FontName']

            provenance = Provenance(
                method=self.method,
                page=page_num,
                bbox=bbox,
                confidence=None,  # Adobe doesn't provide confidence scores
                raw_data={
                    'element_index': element_index,
                    'path': path,
                    'font_info': font_info
                }
            )

            return TextBlock(
                text=text.strip(),
                bbox=bbox,
                page_number=page_num,
                block_type=block_type,
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert Adobe text element {element_index}: {e}")
            return None
    
    def _convert_table_element(self, element: Dict[str, Any], all_elements: List[Dict[str, Any]], element_index: int) -> Optional[Table]:
        """Convert Adobe table element to Table with proper cell structure."""
        try:
            # Get page number (Adobe uses 0-based, we need 1-based)
            page_num = element.get('Page', 0) + 1

            # Get table bounds
            bbox = None
            if 'Bounds' in element and len(element['Bounds']) >= 4:
                bounds = element['Bounds']
                bbox = create_bbox_from_dict({
                    'x0': bounds[0], 'y0': bounds[1],
                    'x1': bounds[2], 'y1': bounds[3]
                })

            # Find all table cells that belong to this table
            table_cells = []
            table_path = element.get('Path', '')

            # Look for child elements that are table rows and cells
            for i, child_element in enumerate(all_elements):
                child_path = child_element.get('Path', '')

                # Check if this element is a child of our table
                if child_path.startswith(table_path) and child_path != table_path:
                    if '/TR' in child_path and '/TD' in child_path:
                        # This is a table cell
                        cell = self._convert_table_cell(child_element, i)
                        if cell:
                            table_cells.append(cell)

            # If no cells found, try to extract from the table element itself
            if not table_cells and 'Text' in element and element['Text'].strip():
                # Create a single cell table
                cell = TableCell(
                    raw_text=element['Text'].strip(),
                    row_idx=0,
                    col_idx=0,
                    is_header=False,
                    provenance=Provenance(
                        method=self.method,
                        page=page_num,
                        bbox=bbox,
                        confidence=None,
                        raw_data={'element_index': element_index, 'path': table_path}
                    )
                )
                table_cells.append(cell)

            if not table_cells:
                return None

            # Calculate table dimensions
            max_row = max(cell.row_idx for cell in table_cells) + 1
            max_col = max(cell.col_idx for cell in table_cells) + 1

            table_id = f"adobe_table_p{page_num}_{element_index}"

            return Table(
                id=table_id,
                rows=max_row,
                cols=max_col,
                cells=table_cells,
                page_number=page_num,
                provenance=Provenance(
                    method=self.method,
                    page=page_num,
                    bbox=bbox,
                    confidence=None,
                    raw_data={'element_index': element_index, 'path': table_path, 'cell_count': len(table_cells)}
                )
            )

        except Exception as e:
            logger.warning(f"Failed to convert Adobe table element {element_index}: {e}")
            return None

    def _convert_table_cell(self, element: Dict[str, Any], element_index: int) -> Optional[TableCell]:
        """Convert Adobe table cell element to TableCell."""
        try:
            text = element.get('Text', '')
            if not text or not text.strip():
                return None

            path = element.get('Path', '')
            page_num = element.get('Page', 0) + 1  # Adobe uses 0-based, we need 1-based

            # Extract row and column indices from path
            # Adobe paths look like: /Document/Table/TR[0]/TD[1]
            row_idx = 0
            col_idx = 0

            import re
            tr_match = re.search(r'/TR\[(\d+)\]', path)
            td_match = re.search(r'/TD\[(\d+)\]', path)

            if tr_match:
                row_idx = int(tr_match.group(1))
            if td_match:
                col_idx = int(td_match.group(1))

            # Determine if this is a header cell (usually in first row or has specific styling)
            is_header = row_idx == 0 or '/TH' in path

            # Get cell bounds
            bbox = None
            if 'Bounds' in element and len(element['Bounds']) >= 4:
                bounds = element['Bounds']
                bbox = create_bbox_from_dict({
                    'x0': bounds[0], 'y0': bounds[1],
                    'x1': bounds[2], 'y1': bounds[3]
                })

            return TableCell(
                raw_text=text.strip(),
                row_idx=row_idx,
                col_idx=col_idx,
                is_header=is_header,
                provenance=Provenance(
                    method=self.method,
                    page=page_num,
                    bbox=bbox,
                    confidence=None,
                    raw_data={'element_index': element_index, 'path': path}
                )
            )

        except Exception as e:
            logger.warning(f"Failed to convert Adobe table cell {element_index}: {e}")
            return None
