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
        
        # Test with Layout Parser
        print("\n=== TESTING LAYOUT PARSER ===")
        processor_name = client.processor_path(project_id, location, processor_id_layout)
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
        print("Sending request to Layout Parser...")
        try:
            result = client.process_document(request=request)
            document_response = result.document
            print("Layout Parser request successful")
        except Exception as e:
            print(f"Layout Parser request failed: {e}")
            return

        print(f"Document text length: {len(document_response.text)}")
        print(f"Number of pages: {len(document_response.pages)}")

        if document_response.pages:
            page = document_response.pages[0]
            print(f"First page paragraphs: {len(page.paragraphs)}")
            print(f"First page tables: {len(page.tables)}")
            print(f"First page blocks: {len(page.blocks) if hasattr(page, 'blocks') else 'No blocks'}")
            print(f"First page lines: {len(page.lines) if hasattr(page, 'lines') else 'No lines'}")
            print(f"First page tokens: {len(page.tokens) if hasattr(page, 'tokens') else 'No tokens'}")

            # Check if there are any paragraphs with content
            if page.paragraphs:
                para = page.paragraphs[0]
                print(f"First paragraph has layout: {para.layout is not None}")
                if para.layout and para.layout.text_anchor:
                    print(f"Text anchor segments: {len(para.layout.text_anchor.text_segments)}")
                    if para.layout.text_anchor.text_segments:
                        segment = para.layout.text_anchor.text_segments[0]
                        print(f"First segment: {segment}")
                        if hasattr(segment, 'start_index'):
                            start_idx = segment.start_index if segment.start_index else 0
                            end_idx = segment.end_index if segment.end_index else len(document_response.text)
                            text_content = document_response.text[start_idx:end_idx]
                            print(f"First paragraph text: '{text_content[:100]}...'")
                else:
                    print("First paragraph has no text_anchor")

            # Check blocks if available
            if hasattr(page, 'blocks') and page.blocks:
                print(f"\nFirst block type: {page.blocks[0].layout}")

        else:
            print("No pages found in response!")

        # Check for Layout Parser specific fields
        print(f"\n=== LAYOUT PARSER SPECIFIC FIELDS ===")
        print(f"Has document_layout: {hasattr(document_response, 'document_layout')}")
        print(f"Has chunked_document: {hasattr(document_response, 'chunked_document')}")

        if hasattr(document_response, 'document_layout') and document_response.document_layout:
            layout = document_response.document_layout
            print(f"Document layout blocks: {len(layout.blocks) if hasattr(layout, 'blocks') else 'No blocks'}")

            if hasattr(layout, 'blocks') and layout.blocks:
                print(f"First block type: {type(layout.blocks[0])}")
                first_block = layout.blocks[0]
                print(f"First block attributes: {dir(first_block)}")

                # Check for different block types
                if hasattr(first_block, 'text_block'):
                    print(f"Has text_block: {first_block.text_block is not None}")
                if hasattr(first_block, 'table_block'):
                    print(f"Has table_block: {first_block.table_block is not None}")
                if hasattr(first_block, 'list_block'):
                    print(f"Has list_block: {first_block.list_block is not None}")

        if hasattr(document_response, 'chunked_document') and document_response.chunked_document:
            chunked = document_response.chunked_document
            print(f"Chunked document chunks: {len(chunked.chunks) if hasattr(chunked, 'chunks') else 'No chunks'}")

            if hasattr(chunked, 'chunks') and chunked.chunks:
                print(f"First chunk type: {type(chunked.chunks[0])}")
                first_chunk = chunked.chunks[0]
                print(f"First chunk attributes: {dir(first_chunk)}")
                if hasattr(first_chunk, 'content'):
                    print(f"First chunk content preview: '{first_chunk.content[:100]}...'")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_google_response()
