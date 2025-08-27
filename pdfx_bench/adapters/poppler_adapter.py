"""
Poppler adapter for PDFX-Bench.
Uses Poppler utilities for PDF processing and basic text extraction.
"""

import logging
import os
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..schema import (
    Document, TextBlock, ExtractionMethod,
    BoundingBox, Provenance
)
from ..provenance import create_provenance, create_bbox_from_coords
from ..utils.timers import time_operation

logger = logging.getLogger(__name__)


class PopplerAdapter:
    """Adapter for Poppler utilities."""
    
    def __init__(self, dpi: int = 300):
        """
        Initialize Poppler adapter.
        
        Args:
            dpi: DPI for PDF processing
        """
        self.method = ExtractionMethod.POPPLER
        self.dpi = dpi
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            from pdf2image import convert_from_path
            
            # Check if poppler utilities are available
            result = subprocess.run(['pdftoppm', '-h'], 
                                  capture_output=True, text=True, timeout=10)
            if 'pdftoppm' not in result.stderr and 'pdftoppm' not in result.stdout:
                raise RuntimeError("pdftoppm not found")
                
            # Check if pdftotext is available
            result = subprocess.run(['pdftotext', '-h'], 
                                  capture_output=True, text=True, timeout=10)
            if 'pdftotext' not in result.stderr and 'pdftotext' not in result.stdout:
                raise RuntimeError("pdftotext not found")
                
            logger.debug("Poppler dependencies available")
            
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            raise RuntimeError(
                "Poppler dependencies not installed. "
                "Install with: pip install pdf2image"
            )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Poppler utilities not found: {e}")
            raise RuntimeError(
                "Poppler utilities not installed. "
                "Please install Poppler and ensure it's in your PATH."
            )
    
    def extract(self, pdf_path: Path, pages: Optional[List[int]] = None, **kwargs) -> Document:
        """
        Extract text from PDF using Poppler utilities.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-based)
            
        Returns:
            Document with extracted text blocks
        """
        logger.info(f"Starting Poppler extraction: {pdf_path}")

        with time_operation("poppler_extraction"):
            try:
                # Get PDF info
                pdf_info = self._get_pdf_info(pdf_path)
                total_pages = max(pdf_info.get('pages', 1), 1)  # Ensure at least 1 page

                # Determine pages to process
                if pages is None:
                    pages_to_process = list(range(1, total_pages + 1))
                else:
                    pages_to_process = [p for p in pages if 1 <= p <= total_pages]

                text_blocks = []

                # Extract text using pdftotext
                for page_num in pages_to_process:
                    page_text = self._extract_text_from_page(pdf_path, page_num)
                    if page_text.strip():
                        text_block = TextBlock(
                            text=page_text.strip(),
                            provenance=create_provenance(
                                method=self.method.value,
                                page=page_num,
                                bbox=create_bbox_from_coords(0, 0, 612, 792),  # Default page size
                                confidence=1.0,  # Poppler is deterministic
                                raw_data={
                                    'extraction_method': 'pdftotext',
                                    'character_count': len(page_text.strip())
                                }
                            )
                        )
                        text_blocks.append(text_block)

                # Create document
                document = Document(
                    id=pdf_path.stem,
                    file_name=pdf_path.name,
                    page_count=total_pages,
                    text_blocks=text_blocks,
                    tables=[],  # Poppler doesn't extract structured tables
                    key_values=[],
                    extraction_metadata={
                        'method': self.method.value,
                        'dpi': self.dpi,
                        'pages_processed': pages_to_process,
                        'poppler_version': self._get_poppler_version()
                    }
                )

                logger.info(f"Poppler extraction complete: {len(text_blocks)} text blocks")
                return document

            except Exception as e:
                logger.error(f"Poppler extraction failed: {e}")
                raise
    
    def _get_pdf_info(self, pdf_path: Path) -> Dict[str, Any]:
        """Get PDF information using pdfinfo."""
        try:
            result = subprocess.run(
                ['pdfinfo', str(pdf_path)],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"pdfinfo failed: {result.stderr}")
                return {'pages': 1}
            
            info = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'pages':
                        try:
                            info['pages'] = int(value)
                        except ValueError:
                            info['pages'] = 1
                    else:
                        info[key] = value
            
            return info
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Could not get PDF info: {e}")
            return {'pages': 1}
    
    def _extract_text_from_page(self, pdf_path: Path, page_num: int) -> str:
        """Extract text from a specific page using pdftotext."""
        try:
            result = subprocess.run(
                ['pdftotext', '-f', str(page_num), '-l', str(page_num), 
                 '-layout', str(pdf_path), '-'],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                logger.warning(f"pdftotext failed for page {page_num}: {result.stderr}")
                return ""
            
            return result.stdout
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Could not extract text from page {page_num}: {e}")
            return ""
    
    def _get_poppler_version(self) -> str:
        """Get Poppler version."""
        try:
            result = subprocess.run(
                ['pdftotext', '-v'],
                capture_output=True, text=True, timeout=10
            )
            
            # pdftotext outputs version to stderr
            version_output = result.stderr
            for line in version_output.split('\n'):
                if 'version' in line.lower():
                    return line.strip()
            
            return "Unknown version"
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return "Unknown version"
    
    def convert_to_images(self, pdf_path: Path, pages: Optional[List[int]] = None) -> List[Path]:
        """
        Convert PDF pages to images using pdf2image.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to convert (1-based)
            
        Returns:
            List of paths to generated image files
        """
        try:
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            if pages:
                # pdf2image uses 1-based page numbers
                images = convert_from_path(
                    pdf_path, 
                    dpi=self.dpi,
                    first_page=min(pages),
                    last_page=max(pages)
                )
            else:
                images = convert_from_path(pdf_path, dpi=self.dpi)
            
            # Save images to temporary files
            image_paths = []
            with tempfile.TemporaryDirectory() as temp_dir:
                for i, image in enumerate(images):
                    page_num = pages[i] if pages else i + 1
                    image_path = Path(temp_dir) / f"page_{page_num}.png"
                    image.save(image_path, 'PNG')
                    image_paths.append(image_path)
            
            return image_paths
            
        except ImportError:
            logger.error("pdf2image not available for image conversion")
            raise RuntimeError("pdf2image not installed")
        except Exception as e:
            logger.error(f"Image conversion failed: {e}")
            raise
