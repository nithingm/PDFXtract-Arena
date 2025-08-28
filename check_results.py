import json

# Load the Adobe results
with open('web/results/5504a148-c4fb-44f2-ae2c-14090239ef4b/results/adobe/5504a148-c4fb-44f2-ae2c-14090239ef4b_test_document_adobe.json', 'r') as f:
    data = json.load(f)

doc = data['document']
print(f'Text blocks: {len(doc["text_blocks"])}')
print(f'Tables: {len(doc["tables"])}')
print(f'Pages: {doc["page_count"]}')

if doc['text_blocks']:
    print(f'Sample text: {doc["text_blocks"][0]["text"]}')

if doc['tables']:
    print(f'Sample table: {len(doc["tables"][0]["rows"])} rows')
