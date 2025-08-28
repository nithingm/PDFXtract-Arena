import requests
import json

# Get the results from the session
session_id = '34ca9974-f8cb-42bf-8d98-9ca72a318329'
r = requests.get(f'http://localhost:4000/results/{session_id}')
data = r.json()

print('=== PROCESSING RESULTS ANALYSIS ===')
print(f'Session ID: {session_id}')
print(f'Results keys: {list(data.keys())}')

if 'error' in data:
    print(f'GLOBAL ERROR: {data["error"]}')

if 'results' in data:
    results = data['results']
    print(f'Number of methods in results: {len(results)}')

    for method_id, result in results.items():
        print(f'\n--- {method_id} ---')
        if 'error' in result:
            print(f'  ERROR: {result["error"]}')
        else:
            print(f'  Text blocks: {len(result.get("text_blocks", []))}')
            print(f'  Tables: {len(result.get("tables", []))}')
            print(f'  Key-values: {len(result.get("key_values", []))}')
            print(f'  Metadata: {result.get("extraction_metadata", {})}')
else:
    print('No results found in response')

if 'pdf_info' in data:
    print(f'\nPDF Info: {data["pdf_info"]}')
