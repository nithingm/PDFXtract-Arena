# Sample PDFs for Testing

This directory contains sample PDF files for testing PDFX-Bench extractors.

## Test Files

### Available PDFs
- `Holley_ Scott - IC scope.pdf` - 4-page business document with text and tables
- `Holley_ Scott - IC revised scope 6.12.25.pdf` - 10-page business document with complex layouts

### Document Characteristics
- **Multi-page documents**: Test pagination and page-specific extraction
- **Mixed content**: Text blocks, tables, and structured data
- **Business format**: Real-world document structure and formatting
- **Various complexity**: Different layout challenges for method comparison

## Usage

Test with a single file:
```bash
python -m pdfx_bench.cli --input "samples/Holley_ Scott - IC scope.pdf" --method auto
```

Test with all samples:
```bash
python -m pdfx_bench.cli --input samples/ --method pdfplumber,camelot-lattice,tabula
```

## Expected Results

Each sample PDF tests specific extraction capabilities:

- **Holley_ Scott - IC scope.pdf**: 4-page document with text blocks and tables, tests multi-page handling
- **Holley_ Scott - IC revised scope 6.12.25.pdf**: 10-page document with complex layouts, tests pagination and large document processing

### Multi-page Handling Notes
- Amazon Textract methods will process only the first page due to synchronous API limitations
- Other methods should process all pages
- Quality scores may vary based on document complexity and method capabilities

## Adding New Samples

When adding new test PDFs:

1. Use descriptive filenames
2. Include both digital and scanned versions when possible
3. Document expected extraction results
4. Keep file sizes reasonable (< 5MB)
5. Ensure no sensitive or copyrighted content

## Validation

Use these samples to validate:
- Extraction accuracy across methods
- Confidence score reliability
- Cross-validation logic
- Performance benchmarks
- Error handling for edge cases
