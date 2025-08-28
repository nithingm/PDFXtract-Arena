#!/usr/bin/env python3
"""
Test script for Adobe PDF Extract API adapter.
"""

import os
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from pdfx_bench.adapters.adobe_extract_adapter import AdobeExtractAdapter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_adobe_credentials():
    """Test Adobe credentials setup."""
    try:
        logger.info("Testing Adobe PDF Extract API credentials...")
        
        # Test with environment variables
        adapter = AdobeExtractAdapter()
        logger.info("✅ Adobe adapter initialized successfully")
        
        # Test with credentials file if it exists
        creds_file = r"C:\Users\Nithin\Documents\PDFServicesSDK-PythonSamples\pdfservices-api-credentials.json"
        if Path(creds_file).exists():
            logger.info(f"Testing with credentials file: {creds_file}")
            adapter_file = AdobeExtractAdapter(credentials_file=creds_file)
            logger.info("✅ Adobe adapter with credentials file initialized successfully")
        else:
            logger.info(f"Credentials file not found: {creds_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Adobe credentials test failed: {e}")
        return False

def test_adobe_extraction():
    """Test Adobe PDF extraction with a sample document."""
    try:
        logger.info("Testing Adobe PDF extraction...")
        
        # Check if test document exists
        test_pdf = Path("test_document.pdf")
        if not test_pdf.exists():
            logger.warning(f"Test document not found: {test_pdf}")
            logger.info("Skipping extraction test")
            return True
        
        # Initialize adapter
        adapter = AdobeExtractAdapter()
        
        # Extract content
        logger.info(f"Extracting content from: {test_pdf}")
        document = adapter.extract(test_pdf)
        
        # Check results
        logger.info(f"✅ Extraction completed:")
        logger.info(f"  - Document ID: {document.id}")
        logger.info(f"  - File name: {document.file_name}")
        logger.info(f"  - Page count: {document.page_count}")
        logger.info(f"  - Text blocks: {len(document.text_blocks)}")
        logger.info(f"  - Tables: {len(document.tables)}")
        logger.info(f"  - Method: {document.extraction_metadata.get('method', 'unknown')}")
        
        # Show sample text blocks
        if document.text_blocks:
            logger.info("Sample text blocks:")
            for i, block in enumerate(document.text_blocks[:3]):
                logger.info(f"  Block {i+1}: '{block.text[:100]}...'")
        
        # Show sample tables
        if document.tables:
            logger.info("Sample tables:")
            for i, table in enumerate(document.tables[:2]):
                logger.info(f"  Table {i+1}: {table.rows}x{table.cols} cells")
                if table.cells:
                    logger.info(f"    First cell: '{table.cells[0].raw_text[:50]}...'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Adobe extraction test failed: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all Adobe adapter tests."""
    logger.info("🚀 Starting Adobe PDF Extract API tests...")
    
    # Test 1: Credentials
    creds_ok = test_adobe_credentials()
    
    # Test 2: Extraction (only if credentials work)
    extraction_ok = True
    if creds_ok:
        extraction_ok = test_adobe_extraction()
    
    # Summary
    logger.info("\n📊 Test Results:")
    logger.info(f"  Credentials: {'✅ PASS' if creds_ok else '❌ FAIL'}")
    logger.info(f"  Extraction: {'✅ PASS' if extraction_ok else '❌ FAIL'}")
    
    if creds_ok and extraction_ok:
        logger.info("🎉 All Adobe tests passed!")
        return 0
    else:
        logger.error("💥 Some Adobe tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
