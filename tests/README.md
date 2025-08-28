# PDFX-Bench Tests

This directory contains integration tests and validation scripts for PDFX-Bench.

## Test Files

### Integration Tests
- `test_complete_workflow.py` - End-to-end workflow testing for Adobe PDF Extract
- `test_amazon_textract.py` - Amazon Textract integration testing
- `test_adobe_adapter.py` - Adobe PDF Extract adapter testing
- `test_adobe_credentials.py` - Adobe credentials validation
- `test_ocr.py` - OCR functionality testing

### Web UI Tests
- `test_adobe_ui.py` - Adobe integration web UI testing
- `test_web_amazon_textract.py` - Amazon Textract web UI testing

## Running Tests

### Prerequisites
1. Set up your environment variables in `.env` file
2. Ensure all required dependencies are installed
3. Have valid API credentials for cloud services

### Running Individual Tests
```bash
# Run a specific test
python tests/test_amazon_textract.py

# Run Adobe workflow test
python tests/test_complete_workflow.py
```

### Test Requirements
- Valid API credentials for cloud services (Adobe, Amazon, Google, Azure)
- Test PDF files in the `samples/` directory
- Proper environment configuration

## Test Data
Test PDFs are located in the `samples/` directory:
- `Holley_ Scott - IC scope.pdf` (4 pages)
- `Holley_ Scott - IC revised scope 6.12.25.pdf` (10 pages)

## Notes
- These are integration tests that require actual API access
- Tests may incur costs when using cloud APIs
- Ensure you have proper rate limiting and quotas configured
