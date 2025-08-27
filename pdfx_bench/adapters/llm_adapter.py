"""
LLM adapter for PDFX-Bench.
Compares traditional extraction methods with Large Language Models.
"""

import logging
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from ..schema import (
    Document, Table, TableCell, TextBlock, KeyValue, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Adapter for LLM-based PDF extraction."""
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4-vision-preview",
        api_key: Optional[str] = None
    ):
        """
        Initialize LLM adapter.
        
        Args:
            provider: LLM provider (openai, anthropic, google, etc.)
            model: Model name
            api_key: API key for the provider
        """
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.method = ExtractionMethod.LLM_EXTRACTION
        self._setup_client()
    
    def _setup_client(self):
        """Set up LLM client based on provider."""
        try:
            if self.provider == "openai":
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
            elif self.provider == "anthropic":
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            elif self.provider == "google":
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            logger.debug(f"LLM client configured for {self.provider}")
            
        except ImportError as e:
            logger.error(f"Missing dependency for {self.provider}: {e}")
            raise RuntimeError(f"Install required package for {self.provider}")
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract content using LLM.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-based), None for all
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted content
        """
        logger.info(f"Starting LLM extraction with {self.provider}/{self.model}: {pdf_path}")
        
        with time_operation(f"llm_{self.provider}_extraction"):
            try:
                # Convert PDF to images
                images = self._pdf_to_images(pdf_path, pages)
                
                # Extract using LLM
                extraction_result = self._extract_with_llm(images, pdf_path)
                
                # Convert to our schema
                document = self._convert_llm_result(extraction_result, pdf_path, len(images))
                
                logger.info(
                    f"LLM extraction complete: {len(document.text_blocks)} text blocks, "
                    f"{len(document.tables)} tables, {len(document.key_values)} key-value pairs"
                )
                
                return document
            
            except Exception as e:
                logger.error(f"LLM extraction failed: {e}")
                return self._create_error_document(pdf_path, str(e))
    
    def _pdf_to_images(self, pdf_path: Path, pages: Optional[List[int]]) -> List[bytes]:
        """Convert PDF pages to images."""
        try:
            from pdf2image import convert_from_path
            import io
            
            # Convert PDF to images
            if pages:
                images = convert_from_path(
                    pdf_path,
                    first_page=min(pages),
                    last_page=max(pages),
                    dpi=150  # Lower DPI for faster processing
                )
                # Filter to requested pages
                page_indices = [p - min(pages) for p in pages]
                images = [images[i] for i in page_indices if i < len(images)]
            else:
                images = convert_from_path(pdf_path, dpi=150)
            
            # Convert to bytes
            image_bytes = []
            for img in images:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image_bytes.append(img_byte_arr.getvalue())
            
            return image_bytes
        
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            raise
    
    def _extract_with_llm(self, images: List[bytes], pdf_path: Path) -> Dict[str, Any]:
        """Extract content using LLM."""
        
        # Prepare extraction prompt
        prompt = self._get_extraction_prompt()
        
        if self.provider == "openai":
            return self._extract_openai(images, prompt)
        elif self.provider == "anthropic":
            return self._extract_anthropic(images, prompt)
        elif self.provider == "google":
            return self._extract_google(images, prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _get_extraction_prompt(self) -> str:
        """Get the extraction prompt for LLM."""
        return """
You are a precise PDF data extraction system. Extract ALL text, tables, and key-value pairs from this document.

CRITICAL RULES:
1. NEVER invent or guess data - only extract what you can clearly see
2. If text is unclear or unreadable, mark it as "[UNCLEAR]"
3. Preserve exact formatting and spacing
4. Extract tables with precise row/column structure
5. Identify key-value pairs (labels and their values)

Return your response as a JSON object with this exact structure:
{
    "text_blocks": [
        {
            "text": "exact text content",
            "page": 1,
            "type": "paragraph|heading|caption|other"
        }
    ],
    "tables": [
        {
            "table_id": "table_1",
            "page": 1,
            "rows": [
                ["cell1", "cell2", "cell3"],
                ["cell4", "cell5", "cell6"]
            ],
            "headers": ["header1", "header2", "header3"]
        }
    ],
    "key_values": [
        {
            "key": "Invoice Number",
            "value": "12345",
            "page": 1
        }
    ]
}

Extract everything visible in the document. Be thorough and accurate.
"""
    
    def _extract_openai(self, images: List[bytes], prompt: str) -> Dict[str, Any]:
        """Extract using OpenAI GPT-4 Vision."""
        try:
            # Prepare messages with images
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # Add images to message
            for img_bytes in images:
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}",
                        "detail": "high"
                    }
                })
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4000,
                temperature=0  # Deterministic output
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            return json.loads(content)
        
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            return {"text_blocks": [], "tables": [], "key_values": [], "error": str(e)}
    
    def _extract_anthropic(self, images: List[bytes], prompt: str) -> Dict[str, Any]:
        """Extract using Anthropic Claude."""
        try:
            # Prepare messages with images
            content = [{"type": "text", "text": prompt}]
            
            # Add images
            for img_bytes in images:
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64
                    }
                })
            
            # Call Anthropic API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0,
                messages=[{"role": "user", "content": content}]
            )
            
            # Parse JSON response
            content = response.content[0].text
            return json.loads(content)
        
        except Exception as e:
            logger.error(f"Anthropic extraction failed: {e}")
            return {"text_blocks": [], "tables": [], "key_values": [], "error": str(e)}
    
    def _extract_google(self, images: List[bytes], prompt: str) -> Dict[str, Any]:
        """Extract using Google Gemini."""
        try:
            # Convert images to PIL format for Gemini
            from PIL import Image
            import io
            
            pil_images = []
            for img_bytes in images:
                pil_images.append(Image.open(io.BytesIO(img_bytes)))
            
            # Create model
            model = self.client.GenerativeModel(self.model)
            
            # Prepare content
            content = [prompt] + pil_images
            
            # Generate response
            response = model.generate_content(
                content,
                generation_config=self.client.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=4000
                )
            )
            
            # Parse JSON response
            return json.loads(response.text)
        
        except Exception as e:
            logger.error(f"Google extraction failed: {e}")
            return {"text_blocks": [], "tables": [], "key_values": [], "error": str(e)}
    
    def _convert_llm_result(
        self,
        llm_result: Dict[str, Any],
        pdf_path: Path,
        page_count: int
    ) -> Document:
        """Convert LLM result to our Document schema."""
        
        text_blocks = []
        tables = []
        key_values = []
        
        # Convert text blocks
        for block_data in llm_result.get("text_blocks", []):
            text_block = self._convert_text_block(block_data)
            if text_block:
                text_blocks.append(text_block)
        
        # Convert tables
        for table_data in llm_result.get("tables", []):
            table = self._convert_table(table_data)
            if table:
                tables.append(table)
        
        # Convert key-value pairs
        for kv_data in llm_result.get("key_values", []):
            kv_pair = self._convert_key_value(kv_data)
            if kv_pair:
                key_values.append(kv_pair)
        
        return Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=page_count,
            text_blocks=text_blocks,
            tables=tables,
            key_values=key_values,
            extraction_metadata={
                'method': f'llm_{self.provider}',
                'model': self.model,
                'provider': self.provider,
                'has_error': 'error' in llm_result
            }
        )

    def _convert_text_block(self, block_data: Dict[str, Any]) -> Optional[TextBlock]:
        """Convert LLM text block to TextBlock."""
        try:
            text = block_data.get("text", "")
            if not text or text.strip() == "[UNCLEAR]":
                return None

            page = block_data.get("page", 1)

            # LLMs don't provide bounding boxes, so we use None
            provenance = create_provenance(
                method=self.method,
                page=page,
                bbox=None,
                confidence=0.8,  # Assume reasonable confidence for LLM
                raw_data={
                    'provider': self.provider,
                    'model': self.model,
                    'block_type': block_data.get("type", "text")
                }
            )

            return TextBlock(
                text=text.strip(),
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert LLM text block: {e}")
            return None

    def _convert_table(self, table_data: Dict[str, Any]) -> Optional[Table]:
        """Convert LLM table to Table."""
        try:
            table_id = table_data.get("table_id", "llm_table")
            rows = table_data.get("rows", [])
            headers = table_data.get("headers", [])
            page = table_data.get("page", 1)

            if not rows:
                return None

            cells = []

            # Add headers if present
            if headers:
                for col_idx, header_text in enumerate(headers):
                    provenance = create_provenance(
                        method=self.method,
                        page=page,
                        bbox=None,
                        confidence=0.8,
                        raw_data={
                            'provider': self.provider,
                            'model': self.model,
                            'table_id': table_id,
                            'is_header': True
                        }
                    )

                    cell = TableCell(
                        raw_text=str(header_text).strip(),
                        row_idx=0,
                        col_idx=col_idx,
                        is_header=True,
                        provenance=provenance
                    )
                    cells.append(cell)

            # Add data rows
            start_row = 1 if headers else 0
            for row_idx, row in enumerate(rows):
                for col_idx, cell_text in enumerate(row):
                    if cell_text and str(cell_text).strip() != "[UNCLEAR]":
                        provenance = create_provenance(
                            method=self.method,
                            page=page,
                            bbox=None,
                            confidence=0.8,
                            raw_data={
                                'provider': self.provider,
                                'model': self.model,
                                'table_id': table_id,
                                'is_header': False
                            }
                        )

                        cell = TableCell(
                            raw_text=str(cell_text).strip(),
                            row_idx=start_row + row_idx,
                            col_idx=col_idx,
                            is_header=False,
                            provenance=provenance
                        )
                        cells.append(cell)

            if not cells:
                return None

            # Create table provenance
            table_provenance = create_provenance(
                method=self.method,
                page=page,
                bbox=None,
                raw_data={
                    'provider': self.provider,
                    'model': self.model,
                    'table_id': table_id,
                    'total_rows': len(rows) + (1 if headers else 0),
                    'total_cols': max(len(row) for row in rows) if rows else 0
                }
            )

            return Table(
                cells=cells,
                table_id=table_id,
                provenance=table_provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert LLM table: {e}")
            return None

    def _convert_key_value(self, kv_data: Dict[str, Any]) -> Optional[KeyValue]:
        """Convert LLM key-value pair to KeyValue."""
        try:
            key = kv_data.get("key", "")
            value = kv_data.get("value", "")
            page = kv_data.get("page", 1)

            if not key.strip() or key.strip() == "[UNCLEAR]":
                return None

            # Clean up unclear values
            if value.strip() == "[UNCLEAR]":
                value = ""

            provenance = create_provenance(
                method=self.method,
                page=page,
                bbox=None,
                confidence=0.8,
                raw_data={
                    'provider': self.provider,
                    'model': self.model,
                    'extraction_type': 'key_value'
                }
            )

            return KeyValue(
                key=key.strip(),
                value=value.strip(),
                provenance=provenance
            )

        except Exception as e:
            logger.warning(f"Failed to convert LLM key-value: {e}")
            return None

    def _create_error_document(self, pdf_path: Path, error_msg: str) -> Document:
        """Create an empty document with error information."""
        return Document(
            id=pdf_path.stem,
            file_name=pdf_path.name,
            page_count=1,
            extraction_metadata={
                'method': f'llm_{self.provider}',
                'model': self.model,
                'provider': self.provider,
                'error': error_msg
            }
        )
