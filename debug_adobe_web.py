#!/usr/bin/env python3
"""
Debug script to test Adobe integration in web UI context.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_adobe_web_integration():
    """Test Adobe integration as it would work in the web UI."""
    print("🔍 Testing Adobe Web UI Integration...")
    
    # Test 1: Check if Adobe adapter can be imported
    try:
        from pdfx_bench.adapters.adobe_extract_adapter import AdobeExtractAdapter
        print("✅ Adobe adapter import successful")
    except Exception as e:
        print(f"❌ Adobe adapter import failed: {e}")
        return False
    
    # Test 2: Check environment variables
    client_id = os.getenv('ADOBE_CLIENT_ID')
    client_secret = os.getenv('ADOBE_CLIENT_SECRET')
    print(f"📋 Environment variables:")
    print(f"  ADOBE_CLIENT_ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"  ADOBE_CLIENT_SECRET: {'✅ Set' if client_secret else '❌ Missing'}")
    
    # Test 3: Simulate web UI credential setting
    print("\n🌐 Simulating Web UI credential setting...")
    test_client_id = "ba9c41ced56f49c5bd68cbb578d28000"
    test_client_secret = "p8e-c-5vF2w4biNohFT_qv8jdd-ec-DT2To2"
    
    # Set credentials as web UI would
    os.environ['ADOBE_CLIENT_ID'] = test_client_id
    os.environ['ADOBE_CLIENT_SECRET'] = test_client_secret
    print(f"✅ Set ADOBE_CLIENT_ID: {test_client_id}")
    print(f"✅ Set ADOBE_CLIENT_SECRET: {test_client_secret[:20]}...")
    
    # Test 4: Test CLI create_adapter function
    try:
        from pdfx_bench.cli import create_adapter
        print("\n🔧 Testing CLI create_adapter...")
        
        # Simulate web UI options
        options = {
            'adobe_client_id': test_client_id,
            'adobe_client_secret': test_client_secret
        }
        
        adapter = create_adapter('adobe', **options)
        print("✅ Adobe adapter created successfully via CLI")
        
        # Test 5: Test actual extraction
        test_pdf = Path("test_document.pdf")
        if test_pdf.exists():
            print(f"\n📄 Testing extraction with: {test_pdf}")
            try:
                document = adapter.extract(test_pdf)
                print(f"✅ Extraction successful!")
                print(f"  - Text blocks: {len(document.text_blocks)}")
                print(f"  - Tables: {len(document.tables)}")
                print(f"  - Method: {document.extraction_metadata.get('method', 'unknown')}")
                return True
            except Exception as e:
                print(f"❌ Extraction failed: {e}")
                import traceback
                print(f"Full traceback: {traceback.format_exc()}")
                return False
        else:
            print(f"⚠️  Test PDF not found: {test_pdf}")
            print("✅ Adapter creation successful (extraction test skipped)")
            return True
            
    except Exception as e:
        print(f"❌ CLI create_adapter failed: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

def main():
    """Run the debug test."""
    print("🚀 Adobe Web UI Integration Debug")
    print("=" * 50)
    
    success = test_adobe_web_integration()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Adobe Web UI integration test PASSED!")
    else:
        print("💥 Adobe Web UI integration test FAILED!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
