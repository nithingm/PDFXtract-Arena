"""
Tesseract OCR adapter for PDFX-Bench.
Rasterizes PDFs and performs OCR using Tesseract (no generation/guessing).
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class TesseractOCRAdapter:
    """Adapter for Tesseract OCR."""
    
    def __init__(self, dpi: int = 300, lang: str = 'eng'):
        """
        Initialize Tesseract OCR adapter.
        
        Args:
            dpi: DPI for PDF rasterization
            lang: Tesseract language code
        """
        self.method = ExtractionMethod.TESSERACT_OCR
        self.dpi = dpi
        self.lang = lang
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            # Check if tesseract is available
            pytesseract.get_tesseract_version()
            logger.debug("Tesseract OCR dependencies available")
            
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            raise RuntimeError(
                "Tesseract OCR dependencies not installed. "
                "Install with: pip install pytesseract pdf2image"
            )
        except Exception as e:
            logger.error(f"Tesseract not found: {e}")
            raise RuntimeError(
                "Tesseract OCR not found. Please install Tesseract and ensure "
                "it's available in your PATH."
            )
    
    def extract(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
        **kwargs
    ) -> Document:
        """
        Extract text using Tesseract OCR.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-based), None for all
            **kwargs: Additional parameters
            
        Returns:
            Document with extracted text
        """
        logger.info(f"Starting Tesseract OCR extraction: {pdf_path}")
        
        with time_operation("tesseract_ocr_extraction"):
            try:
                import pytesseract
                from pdf2image import convert_from_path
                
                # Convert PDF to images
                if pages:
                    # Convert specific pages (pdf2image uses 1-based indexing)
                    images = convert_from_path(
                        pdf_path,
                        dpi=self.dpi,
                        first_page=min(pages),
                        last_page=max(pages)
                    )
                    # Filter to requested pages
                    page_indices = [p - min(pages) for p in pages]
                    images = [images[i] for i in page_indices if i < len(images)]
                else:
                    images = convert_from_path(pdf_path, dpi=self.dpi)
                
                text_blocks = []
                
                # Process each page image
                for page_idx, image in enumerate(images):
                    actual_page = pages[page_idx] if pages else page_idx + 1
                    
                    # Perform OCR with bounding box data
                    ocr_data = pytesseract.image_to_data(
                        image,
                        lang=self.lang,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Extract text blocks from OCR data
                    page_text_blocks = self._extract_text_blocks_from_ocr(
                        ocr_data, actual_page, image.size
                    )
                    text_blocks.extend(page_text_blocks)
                
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=len(images),
                    text_blocks=text_blocks,
                    extraction_metadata={
                        'method': self.method.value,
                        'dpi': self.dpi,
                        'language': self.lang,
                        'pages_processed': pages or list(range(1, len(images) + 1))
                    }
                )
                
                logger.info(
                    f"Tesseract OCR extraction complete: {len(text_blocks)} text blocks"
                )
                
                return document
            
            except Exception as e:
                logger.error(f"Tesseract OCR extraction failed: {e}")
                return Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=1,
                    extraction_metadata={
                        'method': self.method.value,
                        'error': str(e)
                    }
                )
    
    def _extract_text_blocks_from_ocr(
        self,
        ocr_data: Dict[str, List],
        page_num: int,
        image_size: tuple
    ) -> List[TextBlock]:
        """Extract text blocks from Tesseract OCR data."""
        text_blocks = []
        
        # Group words into text blocks (simple approach: by line)
        current_line_text = []
        current_line_bbox = None
        current_line_conf = []
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            # Skip empty text or very low confidence
            if not text or conf < 0:
                continue
            
            # Get word bounding box
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]
            
            word_bbox = create_bbox_from_coords(x, y, x + w, y + h)
            
            # Check if this word is on a new line
            level = ocr_data['level'][i]
            
            if level == 5:  # Word level
                current_line_text.append(text)
                current_line_conf.append(conf / 100.0)  # Convert to 0-1 range
                
                # Expand line bounding box
                if current_line_bbox is None:
                    current_line_bbox = word_bbox
                else:
                    current_line_bbox = create_bbox_from_coords(
                        min(current_line_bbox.x0, word_bbox.x0),
                        min(current_line_bbox.y0, word_bbox.y0),
                        max(current_line_bbox.x1, word_bbox.x1),
                        max(current_line_bbox.y1, word_bbox.y1)
                    )
            
            # End of line or block - create text block
            if (level <= 4 and current_line_text) or i == len(ocr_data['text']) - 1:
                if current_line_text:
                    line_text = ' '.join(current_line_text)
                    avg_confidence = sum(current_line_conf) / len(current_line_conf)
                    
                    # Only include text blocks with reasonable confidence
                    if avg_confidence >= 0.3:  # 30% minimum confidence
                        provenance = create_provenance(
                            method=self.method,
                            page=page_num,
                            bbox=current_line_bbox,
                            confidence=avg_confidence,
                            raw_data={
                                'word_count': len(current_line_text),
                                'avg_word_confidence': avg_confidence
                            }
                        )
                        
                        text_block = TextBlock(
                            text=line_text,
                            provenance=provenance
                        )
                        
                        text_blocks.append(text_block)
                
                # Reset for next line
                current_line_text = []
                current_line_bbox = None
                current_line_conf = []
        
        return text_blocks
