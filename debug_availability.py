import os

def debug_google_availability():
    """Debug Google method availability checking."""
    
    # Check environment variables
    google_project_id = os.getenv('GCP_PROJECT_ID')
    google_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    google_ocr_processor = os.getenv('GCP_PROCESSOR_ID_OCR')
    google_form_processor = os.getenv('GCP_PROCESSOR_ID_FORM')
    google_layout_processor = os.getenv('GCP_PROCESSOR_ID_LAYOUT')
    
    print("=== ENVIRONMENT VARIABLES ===")
    print(f"GCP_PROJECT_ID: {repr(google_project_id)}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {repr(google_credentials)}")
    print(f"GCP_PROCESSOR_ID_OCR: {repr(google_ocr_processor)}")
    print(f"GCP_PROCESSOR_ID_FORM: {repr(google_form_processor)}")
    print(f"GCP_PROCESSOR_ID_LAYOUT: {repr(google_layout_processor)}")
    
    print("\n=== BOOLEAN CHECKS ===")
    ocr_available = bool(google_project_id and google_credentials and google_ocr_processor)
    form_available = bool(google_project_id and google_credentials and google_form_processor)
    layout_available = bool(google_project_id and google_credentials and google_layout_processor)
    
    print(f"OCR available: {ocr_available}")
    print(f"Form available: {form_available}")
    print(f"Layout available: {layout_available}")
    
    # Simulate the web app logic
    methods = [
        {'id': 'google-ocr', 'name': 'Google Document AI (OCR)', 'type': 'cloud'},
        {'id': 'google-form', 'name': 'Google Document AI (Form Parser)', 'type': 'cloud'},
        {'id': 'google-layout', 'name': 'Google Document AI (Layout Parser)', 'type': 'cloud'},
    ]
    
    print("\n=== SIMULATING WEB APP LOGIC ===")
    
    # Step 1: Set cloud methods to False
    for method in methods:
        if method['type'] == 'cloud':
            method['available'] = False
            method['reason'] = 'Requires Google Cloud Project ID and Processor ID'
            print(f"Step 1 - {method['id']}: available = {method['available']}")
    
    # Step 2: Check Google availability
    for method in methods:
        if method['id'] == 'google-ocr':
            method['available'] = bool(google_project_id and google_credentials and google_ocr_processor)
            if not method['available']:
                method['reason'] = 'Requires Google Cloud Project ID, Credentials, and OCR Processor ID'
            print(f"Step 2 - {method['id']}: available = {method['available']}")
        elif method['id'] == 'google-form':
            method['available'] = bool(google_project_id and google_credentials and google_form_processor)
            if not method['available']:
                method['reason'] = 'Requires Google Cloud Project ID, Credentials, and Form Processor ID'
            print(f"Step 2 - {method['id']}: available = {method['available']}")
        elif method['id'] == 'google-layout':
            method['available'] = bool(google_project_id and google_credentials and google_layout_processor)
            if not method['available']:
                method['reason'] = 'Requires Google Cloud Project ID, Credentials, and Layout Processor ID'
            print(f"Step 2 - {method['id']}: available = {method['available']}")
    
    print("\n=== FINAL RESULTS ===")
    for method in methods:
        print(f"{method['id']}: available = {method['available']}, reason = {method.get('reason', 'None')}")

if __name__ == '__main__':
    debug_google_availability()
