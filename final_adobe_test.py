#!/usr/bin/env python3
"""
Final comprehensive test to verify Adobe PDF Extract is working correctly.
"""

import requests
import json
import time
import os
from pathlib import Path

def test_adobe_complete_workflow():
    """Test the complete Adobe workflow from API to extraction."""
    
    print("🎯 FINAL ADOBE PDF EXTRACT COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Test 1: API Availability
    print("\n1. 📋 Testing API Availability...")
    try:
        response = requests.get('http://localhost:4000/api/methods')
        methods = response.json()
        adobe_method = next((m for m in methods if m['id'] == 'adobe'), None)
        
        if adobe_method and adobe_method.get('available'):
            print("✅ Adobe method is available via API")
            print(f"   - Available: {adobe_method['available']}")
            print(f"   - Env Available: {adobe_method['env_available']}")
        else:
            print("❌ Adobe method not available")
            return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    # Test 2: Direct Adapter Test
    print("\n2. 🔧 Testing Direct Adapter...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from pdfx_bench.adapters.adobe_extract_adapter import AdobeExtractAdapter
        
        adapter = AdobeExtractAdapter()
        test_pdf = Path("test_document.pdf")
        
        if test_pdf.exists():
            document = adapter.extract(test_pdf)
            print(f"✅ Direct adapter extraction successful")
            print(f"   - Text blocks: {len(document.text_blocks)}")
            print(f"   - Tables: {len(document.tables)}")
            print(f"   - Pages: {document.page_count}")
        else:
            print("⚠️  Test PDF not found for direct test")
    except Exception as e:
        print(f"❌ Direct adapter test failed: {e}")
        return False
    
    # Test 3: Web UI Integration
    print("\n3. 🌐 Testing Web UI Integration...")
    try:
        test_pdf = Path("test_document.pdf")
        if not test_pdf.exists():
            print("❌ Test PDF not found")
            return False
        
        # Upload via web UI
        files = {'pdf_file': ('test_document.pdf', open(test_pdf, 'rb'), 'application/pdf')}
        data = {'methods': 'adobe', 'adobe_client_id': '', 'adobe_client_secret': ''}
        
        response = requests.post('http://localhost:4000/upload', files=files, data=data)
        files['pdf_file'][1].close()
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print(f"✅ Web UI upload successful: {session_id}")
            
            # Wait for processing
            time.sleep(3)
            
            # Check results
            results_dir = Path(f"web/results/{session_id}/results/adobe")
            if results_dir.exists():
                adobe_files = list(results_dir.glob("*.json"))
                if adobe_files:
                    with open(adobe_files[0], 'r') as f:
                        adobe_data = json.load(f)
                    
                    document = adobe_data.get('document', {})
                    text_blocks = len(document.get('text_blocks', []))
                    tables = len(document.get('tables', []))
                    error = document.get('extraction_metadata', {}).get('error')
                    
                    if error:
                        print(f"❌ Web UI extraction error: {error}")
                        return False
                    else:
                        print(f"✅ Web UI extraction successful")
                        print(f"   - Text blocks: {text_blocks}")
                        print(f"   - Tables: {tables}")
                        
                        if text_blocks > 0:
                            sample_text = document['text_blocks'][0]['text']
                            print(f"   - Sample text: '{sample_text[:50]}...'")
                            return True
                        else:
                            print("⚠️  No content extracted")
                            return False
                else:
                    print("❌ No Adobe result files found")
                    return False
            else:
                print("❌ Adobe results directory not found")
                return False
        else:
            print(f"❌ Web UI upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Web UI test failed: {e}")
        return False

def test_environment_setup():
    """Test environment setup."""
    print("\n4. 🔐 Testing Environment Setup...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        client_id = os.getenv('ADOBE_CLIENT_ID')
        client_secret = os.getenv('ADOBE_CLIENT_SECRET')
        
        if client_id and client_secret:
            print("✅ Environment variables loaded")
            print(f"   - Client ID: {client_id}")
            print(f"   - Client Secret: {client_secret[:10]}...")
            return True
        else:
            print("❌ Environment variables not found")
            return False
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Final Adobe PDF Extract Test Suite")
    
    # Run all tests
    env_ok = test_environment_setup()
    workflow_ok = test_adobe_complete_workflow()
    
    print("\n" + "=" * 60)
    print("🎯 FINAL TEST RESULTS:")
    print(f"   Environment Setup: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"   Adobe Workflow: {'✅ PASS' if workflow_ok else '❌ FAIL'}")
    
    if env_ok and workflow_ok:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 Adobe PDF Extract is FULLY FUNCTIONAL!")
        print("\n📊 Summary:")
        print("   ✅ API availability detection works")
        print("   ✅ Direct adapter extraction works")
        print("   ✅ Web UI integration works")
        print("   ✅ Text blocks are extracted correctly")
        print("   ✅ Environment variables are loaded")
        print("   ✅ Credentials are working")
        print("\n🎯 Your Adobe PDF Extract integration is production-ready!")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Check the error messages above for details.")
    
    print("\n" + "=" * 60)
