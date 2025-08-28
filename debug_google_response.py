import os
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

def debug_google_response():
    """Debug Google Document AI response structure."""
    
    try:
        from google.cloud import documentai
        
        # Setup client
        project_id = os.getenv('GCP_PROJECT_ID')
        processor_id_form = os.getenv('GCP_PROCESSOR_ID_FORM')
        processor_id_layout = os.getenv('GCP_PROCESSOR_ID_LAYOUT')
        location = os.getenv('GCP_LOCATION', 'us')
        
        print(f"Project ID: {project_id}")
        print(f"Form Processor ID: {processor_id_form}")
        print(f"Layout Processor ID: {processor_id_layout}")
        print(f"Location: {location}")
        
        client = documentai.DocumentProcessorServiceClient()
        
        # Test with Form Parser
        print("\n=== TESTING FORM PARSER ===")
        processor_name = client.processor_path(project_id, location, processor_id_form)
        print(f"Processor name: {processor_name}")
        
        # Read test PDF
        pdf_path = Path("test_document.pdf")
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Create request
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
        )
        
        # Process document
        result = client.process_document(request=request)
        document_response = result.document
        
        print(f"Document text length: {len(document_response.text)}")
        print(f"Number of pages: {len(document_response.pages)}")
        
        if document_response.pages:
            page = document_response.pages[0]
            print(f"First page paragraphs: {len(page.paragraphs)}")
            print(f"First page tables: {len(page.tables)}")
            print(f"First page form_fields: {len(page.form_fields)}")
            
            # Check text_anchor structure
            if page.paragraphs:
                para = page.paragraphs[0]
                print(f"First paragraph has layout: {para.layout is not None}")
                if para.layout and para.layout.text_anchor:
                    print(f"Text anchor segments: {len(para.layout.text_anchor.text_segments)}")
                    if para.layout.text_anchor.text_segments:
                        segment = para.layout.text_anchor.text_segments[0]
                        print(f"First segment type: {type(segment)}")
                        print(f"First segment: {segment}")
                        print(f"Has start_index: {hasattr(segment, 'start_index')}")
                        if hasattr(segment, 'start_index'):
                            print(f"start_index: {segment.start_index}")
                            print(f"end_index: {segment.end_index}")
        else:
            print("No pages found in response!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_google_response()
