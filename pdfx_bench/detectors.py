"""
PDF detection utilities for PDFX-Bench.
Detect whether PDFs are digital or scanned, page count, etc.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import fitz  # PyMuPDF
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PDFInfo:
    """Information about a PDF file."""
    file_path: Path
    page_count: int
    is_scanned: bool
    has_text: bool
    has_images: bool
    file_size: int
    pdf_version: str
    is_encrypted: bool
    metadata: Dict[str, Any]
    text_density_per_page: List[float]  # Characters per page
    image_density_per_page: List[int]   # Number of images per page


def detect_pdf_type(pdf_path: Path) -> PDFInfo:
    """
    Detect PDF characteristics to determine extraction strategy.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        PDFInfo with detection results
    """
    logger.debug(f"Analyzing PDF: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        
        # Basic info
        page_count = len(doc)
        file_size = pdf_path.stat().st_size
        pdf_version = getattr(doc, 'pdf_version', lambda: '1.4')()  # Default to 1.4 if not available
        is_encrypted = getattr(doc, 'is_encrypted', False)
        metadata = getattr(doc, 'metadata', {})
        
        # Analyze each page
        text_density_per_page = []
        image_density_per_page = []
        total_text_chars = 0
        total_images = 0
        
        for page_num in range(page_count):
            page = doc[page_num]
            
            # Text analysis
            text = page.get_text()
            text_chars = len(text.strip())
            text_density_per_page.append(text_chars)
            total_text_chars += text_chars
            
            # Image analysis
            image_list = page.get_images()
            image_count = len(image_list)
            image_density_per_page.append(image_count)
            total_images += image_count
        
        doc.close()
        
        # Determine if scanned
        avg_text_per_page = total_text_chars / page_count if page_count > 0 else 0
        avg_images_per_page = total_images / page_count if page_count > 0 else 0
        
        # Heuristics for scanned detection
        # If very little text but many images, likely scanned
        # If no text at all, definitely scanned
        is_scanned = (
            avg_text_per_page < 100 and avg_images_per_page > 0.5
        ) or total_text_chars == 0
        
        has_text = total_text_chars > 0
        has_images = total_images > 0
        
        pdf_info = PDFInfo(
            file_path=pdf_path,
            page_count=page_count,
            is_scanned=is_scanned,
            has_text=has_text,
            has_images=has_images,
            file_size=file_size,
            pdf_version=pdf_version,
            is_encrypted=is_encrypted,
            metadata=metadata,
            text_density_per_page=text_density_per_page,
            image_density_per_page=image_density_per_page
        )
        
        logger.info(
            f"PDF analysis complete: {pdf_path.name} - "
            f"Pages: {page_count}, Scanned: {is_scanned}, "
            f"Text chars: {total_text_chars}, Images: {total_images}"
        )
        
        return pdf_info
        
    except Exception as e:
        logger.error(f"Failed to analyze PDF {pdf_path}: {e}")
        raise


def should_use_ocr(pdf_info: PDFInfo, ocr_mode: str = "auto") -> bool:
    """
    Determine if OCR should be used based on PDF characteristics.
    
    Args:
        pdf_info: PDF information from detection
        ocr_mode: OCR mode ("auto", "force", "off")
        
    Returns:
        Whether to use OCR
    """
    if ocr_mode == "force":
        return True
    elif ocr_mode == "off":
        return False
    elif ocr_mode == "auto":
        # Use OCR if PDF appears to be scanned
        return pdf_info.is_scanned
    else:
        raise ValueError(f"Invalid OCR mode: {ocr_mode}")


def get_recommended_extractors(pdf_info: PDFInfo) -> List[str]:
    """
    Get recommended extractors based on PDF characteristics.
    
    Args:
        pdf_info: PDF information from detection
        
    Returns:
        List of recommended extractor names
    """
    extractors = []
    
    if pdf_info.has_text and not pdf_info.is_scanned:
        # Digital PDF with text - use text-based extractors
        extractors.extend([
            "pdfplumber",
            "camelot-lattice",
            "camelot-stream",
            "tabula"
        ])
    
    if pdf_info.is_scanned or not pdf_info.has_text:
        # Scanned PDF - OCR will be needed
        extractors.append("tesseract")
    
    # Cloud extractors can handle both types
    extractors.extend([
        "adobe",
        "textract", 
        "docai",
        "azure"
    ])
    
    return extractors


def validate_pdf(pdf_path: Path) -> bool:
    """
    Validate that the file is a readable PDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Whether the PDF is valid and readable
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count > 0
    except Exception as e:
        logger.error(f"PDF validation failed for {pdf_path}: {e}")
        return False


def parse_page_range(page_range: Optional[str], total_pages: int) -> List[int]:
    """
    Parse page range string into list of page numbers.
    
    Args:
        page_range: Page range string like "1,2,5-7" or None for all pages
        total_pages: Total number of pages in document
        
    Returns:
        List of 1-based page numbers
    """
    if not page_range:
        return list(range(1, total_pages + 1))
    
    pages = set()
    
    for part in page_range.split(','):
        part = part.strip()
        
        if '-' in part:
            # Range like "5-7"
            start, end = part.split('-', 1)
            start = int(start.strip())
            end = int(end.strip())
            
            if start < 1 or end > total_pages or start > end:
                raise ValueError(f"Invalid page range: {part}")
            
            pages.update(range(start, end + 1))
        else:
            # Single page
            page = int(part)
            if page < 1 or page > total_pages:
                raise ValueError(f"Invalid page number: {page}")
            pages.add(page)
    
    return sorted(list(pages))
