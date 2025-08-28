import os

print('=== CURRENT ENVIRONMENT VARIABLES ===')
print('GCP_PROJECT_ID:', repr(os.getenv('GCP_PROJECT_ID')))
print('GOOGLE_APPLICATION_CREDENTIALS:', repr(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')))
print('GCP_PROCESSOR_ID_OCR:', repr(os.getenv('GCP_PROCESSOR_ID_OCR')))
print('GCP_PROCESSOR_ID_FORM:', repr(os.getenv('GCP_PROCESSOR_ID_FORM')))
print('GCP_PROCESSOR_ID_LAYOUT:', repr(os.getenv('GCP_PROCESSOR_ID_LAYOUT')))

print()
print('=== CHECKING FILE EXISTENCE ===')
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if creds_path:
    print(f'Credentials file exists: {os.path.exists(creds_path)}')
    print(f'Credentials path: {creds_path}')
    if creds_path.startswith('"') and creds_path.endswith('"'):
        print('WARNING: Credentials path has quotes!')
        clean_path = creds_path.strip('"')
        print(f'Clean path: {clean_path}')
        print(f'Clean path exists: {os.path.exists(clean_path)}')
else:
    print('No GOOGLE_APPLICATION_CREDENTIALS found')

print()
print('=== CHECKING .env FILE ===')
env_file = '.env'
if os.path.exists(env_file):
    print('Found .env file. Contents:')
    with open(env_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if 'GOOGLE' in line or 'GCP' in line:
                print(f'Line {i}: {line.strip()}')
else:
    print('No .env file found')
