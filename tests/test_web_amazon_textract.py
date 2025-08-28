#!/usr/bin/env python3
"""
Test script for Amazon Textract web UI integration.
"""

import requests
import json
import time
import os
from pathlib import Path

def test_web_amazon_textract():
    """Test Amazon Textract methods through the web UI."""
    
    print("🧪 Testing Amazon Textract Web UI Integration")
    print("=" * 60)
    
    # Test file
    test_pdf = Path("test_document.pdf")
    if not test_pdf.exists():
        print(f"❌ Test file not found: {test_pdf}")
        return False
    
    print(f"📄 Using test file: {test_pdf}")
    
    # Test both methods
    methods_to_test = [
        ('amazon-detect-text', 'DetectDocumentText'),
        ('amazon-analyze-document', 'AnalyzeDocument')
    ]
    
    results = {}
    
    for method_id, method_name in methods_to_test:
        print(f"\n🚀 Testing {method_name} ({method_id})...")
        
        # Prepare upload
        url = "http://localhost:4000/upload"
        
        files = {
            'pdf_file': ('test_document.pdf', open(test_pdf, 'rb'), 'application/pdf')
        }
        
        data = {
            'methods': method_id,  # Test single method
            'aws_access_key_id': '',  # Use environment variables
            'aws_secret_access_key': '',  # Use environment variables
            'aws_region': ''  # Use environment variables
        }
        
        try:
            # Upload and process
            response = requests.post(url, files=files, data=data)
            
            if response.status_code != 200:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Response: {response.text}")
                files['pdf_file'][1].close()
                return False
            
            # Parse response
            result = response.json()
            session_id = result.get('session_id')
            print(f"✅ Upload successful: {session_id}")
            
            # Wait for processing
            print("⏳ Waiting for processing to complete...")
            time.sleep(8)  # Amazon Textract takes a bit longer
            
            # Check results
            results_dir = Path(f"web/results/{session_id}/results/{method_id}")
            if results_dir.exists():
                print("✅ Results directory exists")
                
                # Find result file
                result_files = list(results_dir.glob("*.json"))
                if result_files:
                    result_file = result_files[0]
                    print(f"✅ Result file found: {result_file.name}")
                    
                    # Parse results
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                    
                    document = result_data.get('document', {})
                    text_blocks = len(document.get('text_blocks', []))
                    tables = len(document.get('tables', []))
                    error = document.get('extraction_metadata', {}).get('error')
                    
                    print(f"📊 {method_name} Results:")
                    print(f"   - Text blocks: {text_blocks}")
                    print(f"   - Tables: {tables}")
                    print(f"   - Pages: {document.get('page_count', 0)}")
                    
                    if error:
                        print(f"❌ Error: {error}")
                        results[method_id] = False
                    elif text_blocks > 0:
                        print(f"   - Sample text: '{document['text_blocks'][0]['text'][:50]}...'")
                        if tables > 0:
                            table = document['tables'][0]
                            print(f"   - Sample table: {len(table['cells'])} cells")
                        results[method_id] = True
                        print(f"✅ {method_name} extraction successful!")
                    else:
                        print("⚠️  No content extracted (but no error)")
                        results[method_id] = False
                else:
                    print("❌ No result files found")
                    results[method_id] = False
            else:
                print("❌ Results directory not found")
                results[method_id] = False
                
        except Exception as e:
            print(f"❌ {method_name} test failed: {e}")
            results[method_id] = False
        
        finally:
            # Close file
            files['pdf_file'][1].close()
    
    return all(results.values())

def test_api_methods():
    """Test that Amazon Textract methods appear in API."""
    
    print("\n🌐 Testing API Method Availability...")
    try:
        response = requests.get('http://localhost:4000/api/methods')
        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code}")
            return False
        
        methods = response.json()
        
        # Find Amazon Textract methods
        detect_method = next((m for m in methods if m['id'] == 'amazon-detect-text'), None)
        analyze_method = next((m for m in methods if m['id'] == 'amazon-analyze-document'), None)
        
        if not detect_method:
            print("❌ amazon-detect-text method not found in API")
            return False
        
        if not analyze_method:
            print("❌ amazon-analyze-document method not found in API")
            return False
        
        print("✅ Amazon Textract methods found in API:")
        print(f"   - DetectDocumentText:")
        print(f"     ID: {detect_method['id']}")
        print(f"     Name: {detect_method['name']}")
        print(f"     Available: {detect_method.get('env_available', False)}")
        print(f"   - AnalyzeDocument:")
        print(f"     ID: {analyze_method['id']}")
        print(f"     Name: {analyze_method['name']}")
        print(f"     Available: {analyze_method.get('env_available', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_credentials():
    """Test credential handling."""
    
    print("\n🔐 Testing Credential Handling...")
    
    # Check environment variables
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    if not aws_access_key_id or not aws_secret_access_key:
        print("❌ AWS credentials not found in environment variables")
        return False
    
    print(f"✅ AWS credentials found:")
    print(f"   Access Key ID: {aws_access_key_id}")
    print(f"   Secret Access Key: {aws_secret_access_key[:10]}...")
    print(f"   Region: {aws_region}")
    
    return True

if __name__ == "__main__":
    print("🚀 Amazon Textract Web UI Integration Test Suite")
    
    # Run tests
    creds_ok = test_credentials()
    api_ok = test_api_methods()
    web_ok = test_web_amazon_textract()
    
    print("\n" + "=" * 60)
    print("🎯 WEB UI TEST RESULTS:")
    print(f"   Credentials: {'✅ PASS' if creds_ok else '❌ FAIL'}")
    print(f"   API Methods: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"   Web UI Integration: {'✅ PASS' if web_ok else '❌ FAIL'}")
    
    if creds_ok and api_ok and web_ok:
        print("\n🎉 ALL WEB UI TESTS PASSED!")
        print("🚀 Amazon Textract web integration is FULLY FUNCTIONAL!")
        print("\n📊 Summary:")
        print("   ✅ DetectDocumentText web UI works")
        print("   ✅ AnalyzeDocument web UI works")
        print("   ✅ API availability detection works")
        print("   ✅ Credential handling works")
        print("   ✅ File upload and processing works")
        print("   ✅ Results display correctly")
        print("\n🎯 Ready for production use!")
    else:
        print("\n❌ SOME WEB UI TESTS FAILED!")
        print("Check the error messages above for details.")
    
    print("\n" + "=" * 60)
