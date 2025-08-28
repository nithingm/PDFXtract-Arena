#!/usr/bin/env python3
"""
Test script to verify Adobe PDF Extract API credentials are working.
Run this after updating your .env file with valid Adobe credentials.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_adobe_credentials():
    """Test if Adobe credentials are valid by attempting to create a PDFServices instance."""
    
    print("🧪 Testing Adobe PDF Extract API Credentials...")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if credentials are present
    client_id = os.getenv('ADOBE_CLIENT_ID')
    client_secret = os.getenv('ADOBE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Adobe credentials not found in environment variables")
        print("   Make sure ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET are set in .env")
        return False
    
    print(f"✅ Found Adobe credentials:")
    print(f"   Client ID: {client_id}")
    print(f"   Client Secret: {client_secret[:10]}...")
    
    # Test credentials by creating Adobe SDK instance
    try:
        from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
        from adobe.pdfservices.operation.pdf_services import PDFServices
        
        print("\n🔐 Testing credential validation...")
        
        # Create credentials
        credentials = ServicePrincipalCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Create PDF Services instance (this validates credentials)
        pdf_services = PDFServices(credentials=credentials)
        
        print("✅ Adobe credentials are VALID!")
        print("✅ Adobe PDF Services SDK initialized successfully")
        print("\n🎉 Your Adobe integration is ready to use!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Adobe PDF Services SDK not installed: {e}")
        print("   Run: pip install pdfservices-sdk")
        return False
        
    except Exception as e:
        print(f"❌ Adobe credential validation failed: {e}")
        print("\n💡 This usually means:")
        print("   1. Invalid Client ID or Client Secret")
        print("   2. Credentials have expired")
        print("   3. Adobe account doesn't have PDF Services API access")
        print("\n🔧 To fix this:")
        print("   1. Go to https://developer.adobe.com/console")
        print("   2. Create a new project with PDF Services API")
        print("   3. Generate new Service Account credentials")
        print("   4. Update your .env file with the new credentials")
        
        return False

def test_adobe_extraction():
    """Test actual PDF extraction if credentials are valid."""
    
    print("\n" + "=" * 50)
    print("🚀 Testing Adobe PDF Extraction...")
    
    # Check if test document exists
    test_pdf = Path("test_document.pdf")
    if not test_pdf.exists():
        print("⚠️  Test document not found - skipping extraction test")
        print(f"   Looking for: {test_pdf.absolute()}")
        return True
    
    try:
        # Import and test the Adobe adapter
        sys.path.insert(0, str(Path(__file__).parent))
        from pdfx_bench.adapters.adobe_extract_adapter import AdobeExtractAdapter
        
        print(f"📄 Testing extraction on: {test_pdf}")
        
        # Create adapter and extract
        adapter = AdobeExtractAdapter()
        document = adapter.extract(test_pdf)
        
        # Check results
        print(f"✅ Extraction completed successfully!")
        print(f"   📊 Results:")
        print(f"      - Text blocks: {len(document.text_blocks)}")
        print(f"      - Tables: {len(document.tables)}")
        print(f"      - Pages: {document.page_count}")
        
        if len(document.text_blocks) > 0:
            print(f"   📝 Sample text: '{document.text_blocks[0].text[:100]}...'")
        
        if 'error' in document.extraction_metadata:
            print(f"⚠️  Warning: {document.extraction_metadata['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Adobe extraction test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Adobe PDF Extract API Credential Tester")
    print("This script will verify your Adobe credentials are working correctly.\n")
    
    # Test credentials
    credentials_valid = test_adobe_credentials()
    
    if credentials_valid:
        # Test extraction if credentials work
        extraction_works = test_adobe_extraction()
        
        if extraction_works:
            print("\n🎉 ALL TESTS PASSED!")
            print("Your Adobe PDF Extract integration is fully functional!")
        else:
            print("\n⚠️  Credentials valid but extraction failed")
            print("Check the error messages above for details.")
    else:
        print("\n❌ CREDENTIAL TEST FAILED")
        print("Fix your Adobe credentials before testing extraction.")
    
    print("\n" + "=" * 50)
