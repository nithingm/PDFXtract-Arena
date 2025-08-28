import requests
import json

# Get all methods
r = requests.get('http://localhost:4000/api/methods')
methods = r.json()

print('=== DETAILED GOOGLE METHODS STATUS ===')
google_methods = [m for m in methods if 'google' in m['id'] and m['id'] != 'llm-google']

for method in google_methods:
    status = '✅' if method['available'] else '❌'
    print(f'{status} {method["id"]}: {method["name"]}')
    print(f'   Type: {method["type"]}')
    print(f'   Available: {method["available"]}')
    print(f'   Reason: {method.get("reason", "No reason provided")}')
    print()

print(f'Total Google methods: {len(google_methods)}')
available_google = [m for m in google_methods if m['available']]
print(f'Available Google methods: {len(available_google)}')

if available_google:
    print('\nAvailable Google method IDs:')
    for method in available_google:
        print(f'  - {method["id"]}')
