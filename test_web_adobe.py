#!/usr/bin/env python3
"""
Test script to verify Adobe PDF Extract works through the web UI.
"""

import requests
import json
import time
from pathlib import Path

def test_web_adobe_extraction():
    """Test Adobe extraction through the web UI."""
    
    print("🧪 Testing Adobe PDF Extract via Web UI...")
    print("=" * 50)
    
    # Test file
    test_pdf = Path("test_document.pdf")
    if not test_pdf.exists():
        print(f"❌ Test file not found: {test_pdf}")
        return False
    
    print(f"📄 Using test file: {test_pdf}")
    
    # Prepare upload
    url = "http://localhost:4000/upload"
    
    files = {
        'pdf_file': ('test_document.pdf', open(test_pdf, 'rb'), 'application/pdf')
    }
    
    data = {
        'methods': 'adobe',  # Only test Adobe
        'adobe_client_id': '',  # Use environment variables
        'adobe_client_secret': ''  # Use environment variables
    }
    
    try:
        print("🚀 Uploading PDF and starting Adobe extraction...")
        
        # Upload and process
        response = requests.post(url, files=files, data=data)
        
        if response.status_code != 200:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse response
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Session ID: {result.get('session_id', 'unknown')}")
        
        # Wait a moment for processing
        print("⏳ Waiting for processing to complete...")
        time.sleep(5)
        
        # Check results
        session_id = result.get('session_id')
        if session_id:
            results_url = f"http://localhost:4000/results/{session_id}"
            results_response = requests.get(results_url)
            
            if results_response.status_code == 200:
                print("✅ Results page accessible")
                
                # Check if Adobe results exist
                results_dir = Path(f"web/results/{session_id}/results/adobe")
                if results_dir.exists():
                    print("✅ Adobe results directory exists")
                    
                    # Find Adobe result file
                    adobe_files = list(results_dir.glob("*.json"))
                    if adobe_files:
                        adobe_file = adobe_files[0]
                        print(f"✅ Adobe result file found: {adobe_file.name}")
                        
                        # Parse Adobe results
                        with open(adobe_file, 'r') as f:
                            adobe_data = json.load(f)
                        
                        document = adobe_data.get('document', {})
                        text_blocks = len(document.get('text_blocks', []))
                        tables = len(document.get('tables', []))
                        error = document.get('extraction_metadata', {}).get('error')
                        
                        print(f"📊 Adobe Extraction Results:")
                        print(f"   - Text blocks: {text_blocks}")
                        print(f"   - Tables: {tables}")
                        
                        if error:
                            print(f"❌ Error: {error}")
                            return False
                        elif text_blocks > 0 or tables > 0:
                            print("🎉 SUCCESS! Adobe extracted content successfully!")
                            return True
                        else:
                            print("⚠️  No content extracted (but no error)")
                            return False
                    else:
                        print("❌ No Adobe result files found")
                        return False
                else:
                    print("❌ Adobe results directory not found")
                    return False
            else:
                print(f"❌ Results page not accessible: {results_response.status_code}")
                return False
        else:
            print("❌ No session ID returned")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        # Close file
        files['pdf_file'][1].close()

if __name__ == "__main__":
    print("🔍 Adobe PDF Extract Web UI Integration Test")
    print("This script tests Adobe extraction through the web interface.\n")
    
    success = test_web_adobe_extraction()
    
    if success:
        print("\n🎉 WEB UI TEST PASSED!")
        print("Adobe PDF Extract is working correctly through the web interface!")
    else:
        print("\n❌ WEB UI TEST FAILED!")
        print("Check the error messages above for details.")
    
    print("\n" + "=" * 50)
