# Sample PDFs for Testing

This directory contains sample PDF files for testing PDFX-Bench extractors.

## Test Files

### Digital PDFs
- `invoice_digital.pdf` - Digital invoice with tables and text
- `report_digital.pdf` - Multi-page report with complex tables
- `form_digital.pdf` - Form with key-value pairs

### Scanned PDFs  
- `invoice_scanned.pdf` - Scanned invoice requiring OCR
- `form_scanned.pdf` - Scanned form with handwritten elements

### Complex Layouts
- `financial_statement.pdf` - Financial statement with nested tables
- `scientific_paper.pdf` - Academic paper with figures and tables
- `multi_column.pdf` - Multi-column layout document

## Usage

Test with a single file:
```bash
pdfx-bench --input samples/invoice_digital.pdf --method auto
```

Test with all samples:
```bash
pdfx-bench --input samples/ --method pdfplumber,camelot-lattice,tabula
```

## Expected Results

Each sample PDF is designed to test specific extraction capabilities:

- **invoice_digital.pdf**: Should extract line items table, totals, and header information
- **report_digital.pdf**: Should handle multi-page tables and preserve table structure
- **form_digital.pdf**: Should extract key-value pairs and form fields
- **invoice_scanned.pdf**: Requires OCR, may have lower confidence scores
- **financial_statement.pdf**: Tests complex table layouts and numeric parsing

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
