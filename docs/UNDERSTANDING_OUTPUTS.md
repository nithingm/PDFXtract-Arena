# Understanding PDFX-Bench Outputs

This guide explains how to interpret PDFX-Bench results and use them to make informed decisions about PDF extraction methods.

## Why Use Deterministic Methods?

**Traditional Problem:** Many PDF extraction tools "hallucinate" or guess missing data, leading to:
- Invented numbers in financial documents
- Made-up text in contracts
- Unreliable data for business decisions

**PDFX-Bench Solution:** Zero-hallucination extraction that:
- Never invents data - flags unclear content instead
- Provides confidence scores from cloud APIs
- Tracks exactly where each piece of data came from
- Compares multiple methods to find the most reliable

## Output Structure Explained

```
outputs/YYYYMMDD_HHMMSS/
├── results/                    # Raw extraction data
│   ├── pdfplumber/            # Method-specific results
│   │   ├── document.json      # Complete extraction data
│   │   ├── document_tables.csv # Tables in spreadsheet format
│   │   └── document_text.jsonl # Text blocks with metadata
│   ├── camelot-lattice/
│   └── textract/
├── reports/                   # Human-readable analysis
│   ├── document_comparison.md # Markdown report
│   └── document_comparison.html # Styled HTML report
├── quarantine/               # Flagged/invalid data
│   └── document_quarantine.jsonl
└── summary.json             # Overall processing summary
```

## Reading the Comparison Report

### Quality Score (0-1 scale)
- **0.9-1.0:** Excellent - Highly reliable extraction
- **0.7-0.8:** Good - Minor issues, generally trustworthy
- **0.5-0.6:** Fair - Some problems, verify important data
- **0.0-0.4:** Poor - Significant issues, consider other methods

### Key Metrics Explained

**Tables Found:** Number of tables detected
- Higher isn't always better - accuracy matters more than quantity

**Text Blocks:** Number of text sections extracted
- Indicates how well the method handles document structure

**Confidence:** Average confidence from cloud APIs
- N/A for local methods (pdfplumber, camelot, tabula)
- 0.9+ is excellent for cloud APIs (AWS Textract, Google, etc.)

**Processing Time:** Seconds to complete extraction
- Local methods: Usually < 1 second
- Cloud APIs: 2-10 seconds depending on document size

## Method-Specific Strengths

### pdfplumber
- **Best for:** Digital PDFs with clear text
- **Strengths:** Fast, reliable text extraction
- **Limitations:** Basic table detection

### camelot-lattice
- **Best for:** Tables with clear borders/lines
- **Strengths:** Precise table structure detection
- **Limitations:** Requires visible table borders

### camelot-stream
- **Best for:** Tables without borders
- **Strengths:** Handles borderless tables
- **Limitations:** May create extra empty cells

### tabula
- **Best for:** Simple tables in academic papers
- **Strengths:** Good for research documents
- **Limitations:** Requires Java, less accurate than camelot

### AWS Textract
- **Best for:** Complex documents, forms
- **Strengths:** High confidence scores, handles scanned docs
- **Limitations:** Costs money, requires AWS account

### Google Document AI
- **Best for:** Forms, invoices, receipts
- **Strengths:** Excellent key-value extraction
- **Limitations:** Costs money, requires GCP account

## Business Use Cases

### Financial Documents
**Recommended:** AWS Textract + camelot-lattice
- Textract for confidence scores on critical numbers
- Camelot for precise table structure
- Cross-validate totals between methods

### Legal Contracts
**Recommended:** pdfplumber + Google Document AI
- pdfplumber for full text extraction
- Document AI for key terms and dates
- Manual review of low-confidence sections

### Research Papers
**Recommended:** pdfplumber + tabula
- pdfplumber for text and references
- tabula for data tables
- Cost-effective for academic use

### Invoices/Receipts
**Recommended:** Google Document AI + camelot-lattice
- Document AI for vendor info and totals
- Camelot for line item tables
- High accuracy for accounting systems

## Red Flags to Watch For

### Low Quality Scores (< 0.6)
- **Action:** Try different method or manual review
- **Cause:** Poor PDF quality, complex layout, scanned document

### High Empty Cell Rate (> 30%)
- **Action:** Switch to stream mode or different method
- **Cause:** Table detection issues, merged cells

### Processing Failures
- **Action:** Check logs, verify PDF isn't corrupted
- **Cause:** Unsupported PDF format, missing dependencies

### Confidence Scores < 0.8 (Cloud APIs)
- **Action:** Flag for manual review
- **Cause:** Poor scan quality, handwritten text, complex layout

## Using the Data

### CSV Files (Tables)
```csv
table_id,row,col,text,is_header,parsed_number,confidence,page
page_1_table_0,0,0,Item,true,,0.95,1
page_1_table_0,1,0,Widget A,false,,0.92,1
page_1_table_0,1,4,$100.00,false,100.0,0.98,1
```

**Key Columns:**
- `text`: Raw extracted text (never modified)
- `parsed_number`: Automatically parsed numeric value
- `confidence`: Reliability score (if available)
- `is_header`: Whether cell is a table header

### JSON Files (Complete Data)
Contains full extraction with provenance:
- Exact bounding box coordinates
- Page numbers
- Method used
- Original raw data from extractor

### JSONL Files (Text Blocks)
One text block per line with metadata:
```json
{"text": "Invoice #12345", "page": 1, "bbox": {"x0": 100, "y0": 50, "x1": 200, "y1": 70}, "confidence": 0.95}
```

## Troubleshooting Common Issues

### "No tables found"
- Try different method (camelot-stream vs lattice)
- Check if PDF has actual tables vs. formatted text
- Verify PDF isn't scanned (use OCR if needed)

### "Low confidence scores"
- Improve PDF quality (higher resolution scan)
- Try different cloud API
- Consider manual review for critical data

### "Processing too slow"
- Use local methods for speed
- Process specific pages only (`--pages 1,2,5-7`)
- Consider batch processing overnight

### "Inconsistent results"
- Compare multiple methods
- Use cross-validation features
- Flag discrepancies for manual review

## Best Practices

1. **Always compare multiple methods** for critical documents
2. **Set appropriate confidence thresholds** (0.9+ for financial data)
3. **Use quarantine reports** to review flagged data
4. **Validate totals and calculations** using cross-checks
5. **Keep original PDFs** for manual verification when needed
6. **Document your method selection** for audit trails

## Making the Business Case

### Cost Savings
- Reduce manual data entry by 80-95%
- Eliminate transcription errors
- Process documents 10x faster

### Risk Reduction
- Audit trail for every extracted value
- Confidence scores for quality control
- No hallucinated data in financial reports

### Scalability
- Process thousands of documents automatically
- Consistent quality across all extractions
- Easy integration with existing systems