#!/usr/bin/env python3
"""
Test script to verify Adobe PDF Extract is available in the UI when running python web/app.py
"""

import requests
import json
import sys
from pathlib import Path

def test_adobe_availability():
    """Test if Adobe PDF Extract is available via the API and UI"""
    
    print("🧪 Testing Adobe PDF Extract availability...")
    
    # Test 1: Check API endpoint
    print("\n1. Testing /api/methods endpoint...")
    try:
        response = requests.get('http://localhost:4000/api/methods')
        if response.status_code != 200:
            print(f"❌ API request failed with status {response.status_code}")
            return False
            
        methods = response.json()
        adobe_method = None
        for method in methods:
            if method['id'] == 'adobe':
                adobe_method = method
                break
                
        if not adobe_method:
            print("❌ Adobe method not found in API response")
            return False
            
        print(f"✅ Adobe method found:")
        print(f"   - Available: {adobe_method.get('available', False)}")
        print(f"   - Env Available: {adobe_method.get('env_available', False)}")
        
        if not adobe_method.get('available', False):
            print("❌ Adobe method is not available")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    # Test 2: Check main page HTML
    print("\n2. Testing main page HTML...")
    try:
        response = requests.get('http://localhost:4000')
        if response.status_code != 200:
            print(f"❌ Main page request failed with status {response.status_code}")
            return False
            
        content = response.text
        
        # Check if Adobe is in the HTML
        if 'Adobe PDF Extract' not in content:
            print("❌ Adobe PDF Extract not found in HTML")
            return False
        print("✅ Adobe PDF Extract found in HTML")
        
        # Check if adobeEnvAvailable is set to true
        if 'window.adobeEnvAvailable = true;' not in content:
            print("❌ window.adobeEnvAvailable not set to true")
            return False
        print("✅ window.adobeEnvAvailable = true found in HTML")
        
        # Check if Adobe checkbox is present
        if 'method-adobe' not in content:
            print("❌ Adobe checkbox not found in HTML")
            return False
        print("✅ Adobe checkbox found in HTML")
        
    except Exception as e:
        print(f"❌ HTML test failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Adobe PDF Extract is properly available.")
    return True

def test_environment_variables():
    """Test if environment variables are loaded correctly"""
    print("\n3. Testing environment variable loading...")
    
    try:
        import os
        from dotenv import load_dotenv
        
        # Load .env from parent directory (same as web app does)
        env_path = Path(__file__).parent / '.env'
        load_dotenv(env_path)
        
        adobe_client_id = os.getenv('ADOBE_CLIENT_ID')
        adobe_client_secret = os.getenv('ADOBE_CLIENT_SECRET')
        
        if not adobe_client_id:
            print("❌ ADOBE_CLIENT_ID not found in environment")
            return False
        print(f"✅ ADOBE_CLIENT_ID found: {adobe_client_id}")
        
        if not adobe_client_secret:
            print("❌ ADOBE_CLIENT_SECRET not found in environment")
            return False
        print(f"✅ ADOBE_CLIENT_SECRET found: {adobe_client_secret[:20]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment variable test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Adobe PDF Extract UI Test")
    print("=" * 50)
    
    # Test environment variables first
    env_test = test_environment_variables()
    
    # Test API and UI
    ui_test = test_adobe_availability()
    
    print("\n" + "=" * 50)
    if env_test and ui_test:
        print("🎉 ALL TESTS PASSED! Adobe PDF Extract is working correctly.")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Check the output above.")
        sys.exit(1)
