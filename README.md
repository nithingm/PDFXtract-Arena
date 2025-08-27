# PDFXtract-Arena: No-Hallucination PDF Extraction Benchmark

A comprehensive PDF extraction benchmark tool that compares multiple extraction methods with zero-hallucination policy. Extract text and tables from PDFs using various extractors, normalize results to a canonical schema, and generate auditable quality reports.

## Quick Start

### Web UI (Recommended)

The easiest way to get started is with the web interface:

1. **Clone and Setup**
   ```bash
   git clone https://github.com/nithingm/PDFXtract-Arena.git
   cd pdfx-bench
   python -m venv venv

   # Windows
   venv\Scripts\activate
   pip install -r requirements.txt

   # macOS/Linux
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Automated OCR Setup (Windows)**
   ```cmd
   # Run automated setup for Tesseract OCR and Poppler
   powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1

   # Verify installation
   python scripts/check_dependencies.py
   ```

3. **Start Web Interface**
   ```bash
   cd web
   python app.py
   ```

4. **Open Browser**
   - Navigate to: http://localhost:4000
   - Drag & drop a PDF file
   - Select extraction methods (local methods work without API keys)
   - Tesseract OCR will be automatically enabled if properly installed
   - Click "Start Processing"

### Command Line Usage

```bash
# Basic extraction with local methods
python -m pdfx_bench.cli --input document.pdf --method pdfplumber

# Compare multiple methods
python -m pdfx_bench.cli --input document.pdf --method pdfplumber,poppler,tesseract

# Extract specific pages
python -m pdfx_bench.cli --input file.pdf --method auto --pages "1,2,5-7"
```

## Features

- **Web Interface**: Modern drag-and-drop UI with real-time progress tracking
- **Multiple Extractors**: pdfplumber, camelot (lattice/stream), tabula-py, Adobe PDF Extract API, AWS Textract, Google Document AI, Azure Document Intelligence, OpenAI GPT-4 Vision, Anthropic Claude, Google Gemini
- **Zero Hallucination**: Deterministic methods never invent or "fix" values - flags unreadable content instead
- **Confidence Filtering**: Honor per-element confidence scores from cloud APIs
- **Provenance Tracking**: Every extracted field carries method, page, bbox, and confidence
- **Schema Validation**: Pydantic models with automatic quarantine for invalid data
- **Cross-Validation**: Automatic checks for numeric consistency, date formats, currency patterns
- **Quality Scoring**: Comprehensive metrics and heuristics for extraction quality
- **Multiple Output Formats**: JSONL, CSV, Parquet, HTML/Markdown reports

## Requirements

- Python 3.10+
- Java 8+ (for tabula-py, optional)
- API keys for cloud services (optional)

---

## Detailed Installation

### Prerequisites

**Required:**
- Python 3.10+

**Optional (for specific methods):**
- Java 8+ (for tabula-py)
- Tesseract OCR (for scanned PDFs)
- Poppler (for pdf2image)

### Windows Setup

1. **Install Python 3.10+**
   ```cmd
   # Download from python.org or use winget
   winget install Python.Python.3.11
   ```

2. **Install Java (Optional - for Tabula)**
   ```cmd
   # Download from Oracle or use winget
   winget install Oracle.JavaRuntimeEnvironment
   # Verify installation
   java -version
   ```

3. **Install Dependencies**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

### macOS Setup

1. **Install Python 3.10+**
   ```bash
   # Using Homebrew
   brew install python@3.11
   ```

2. **Install Java (Optional - for Tabula)**
   ```bash
   brew install openjdk@11
   # Verify installation
   java -version
   ```

3. **Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Linux Setup (Ubuntu/Debian)

1. **Install Python 3.10+**
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3.11-dev
   ```

2. **Install Java (Optional - for Tabula)**
   ```bash
   sudo apt install openjdk-11-jre-headless
   # Verify installation
   java -version
   ```

3. **Install System Dependencies**
   ```bash
   sudo apt install python3-tk ghostscript
   ```

4. **Install Dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## API Keys Setup (Optional)

**Local methods work without any API keys!** Only set up API keys if you want to use cloud or LLM methods.

### Using the Web Interface

1. Click "API Keys (Optional)" in the web interface
2. Enter your API keys for the services you want to use
3. Keys are stored temporarily for your session only

### Using Environment Variables

```bash
# Cloud Services (Optional)
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-east-1"

export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export GCP_PROJECT_ID="your_project_id"

export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://your-resource.cognitiveservices.azure.com/"
export AZURE_DOCUMENT_INTELLIGENCE_KEY="your_api_key"

# LLM Services (Optional)
export OPENAI_API_KEY="your_openai_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export GOOGLE_API_KEY="your_google_api_key"
```

### Detailed Cloud Setup

<details>
<summary>Click to expand detailed cloud setup instructions</summary>

#### AWS Textract
1. Create AWS account and get access keys
2. Install AWS CLI: `pip install awscli`
3. Configure: `aws configure`

#### Google Document AI
1. Create GCP project at [Google Cloud Console](https://console.cloud.google.com)
2. Enable Document AI API
3. Create service account and download JSON key

#### Azure Document Intelligence
1. Create resource at [Azure Portal](https://portal.azure.com)
2. Get endpoint URL and API key from resource page

#### Adobe PDF Extract API
1. Create account at [Adobe Developer Console](https://developer.adobe.com/console)
2. Create project and add PDF Services API
3. Download credentials JSON

</details>

---

## Web Interface Features

The web interface provides an intuitive way to compare PDF extraction methods:

- **Drag & Drop Upload**: Simply drag PDF files onto the upload area
- **Method Selection**: Choose from 10+ extraction methods including local, cloud, and LLM-based extractors
- **Real-Time Progress**: Track extraction progress with live updates
- **Interactive Results**: View and compare results in organized, multi-tab interface
- **Export & Download**: Download results in various formats (JSON, CSV, etc.)
- **API Key Management**: Secure, session-only storage of API credentials
- **Quality Metrics**: Visual quality scores and performance comparisons

### Available Methods

**Local Methods (No API keys required):**
- PDFplumber - Fast text and basic table extraction
- Camelot Lattice - Tables with visible borders
- Camelot Stream - Tables without borders
- Tabula - Academic table extraction (requires Java)
- Poppler - PDF utilities for text extraction (requires setup)
- Tesseract OCR - OCR for scanned PDFs (requires setup)

**Cloud Methods (API keys required):**
- AWS Textract - Advanced OCR and form extraction
- Google Document AI - Advanced document understanding
- Azure Document Intelligence - Microsoft cloud extraction

**LLM Methods (API keys required):**
- OpenAI GPT-4 Vision - AI-powered extraction
- Anthropic Claude - AI document analysis
- Google Gemini - Multimodal AI extraction

### Method Comparison

| Method | Speed | Text Quality | Table Support | OCR Support | Setup Required |
|--------|-------|--------------|---------------|-------------|----------------|
| PDFplumber | ⚡⚡⚡ | ⭐⭐⭐ | ⭐⭐ | ❌ | None |
| Poppler | ⚡⚡⚡ | ⭐⭐⭐⭐ | ❌ | ❌ | Poppler utilities |
| Tesseract OCR | ⚡ | ⭐⭐⭐⭐ | ❌ | ✅ | Tesseract + Poppler |
| Camelot | ⚡⚡ | ⭐⭐ | ⭐⭐⭐⭐ | ❌ | None |
| Tabula | ⚡⚡ | ⭐⭐ | ⭐⭐⭐ | ❌ | Java |

**Recommendations:**
- **Text-heavy PDFs**: Use Poppler for best quality and speed
- **Scanned documents**: Use Tesseract OCR
- **Complex tables**: Use Camelot or Tabula
- **Quick analysis**: Use PDFplumber
- **Best results**: Compare multiple methods

---

## Command Line Usage

### Basic Examples

```bash
# Extract using local methods only
python -m pdfx_bench.cli --input document.pdf --method pdfplumber

# Compare multiple local methods
python -m pdfx_bench.cli --input document.pdf --method pdfplumber,poppler,tesseract

# Extract specific pages
python -m pdfx_bench.cli --input file.pdf --method auto --pages "1,2,5-7"

# Process directory of PDFs
python -m pdfx_bench.cli --input pdfs/ --method pdfplumber
```

### Advanced Examples

```bash
# Compare with cloud methods (requires API keys)
python -m pdfx_bench.cli --input document.pdf --method pdfplumber,textract --aws-access-key YOUR_KEY

# Compare with LLM methods
python -m pdfx_bench.cli --input document.pdf --method auto,llm-openai --openai-api-key YOUR_KEY

# Custom output directory with confidence filtering
python -m pdfx_bench.cli --input file.pdf --method auto --out-dir ./results --min-confidence 0.9

# Batch processing with logging
python -m pdfx_bench.cli --input pdfs/ --method auto --log-level DEBUG
```

---

## Output Structure

```
results/
├── session_id/                # Unique session directory
│   ├── document_pdfplumber.json         # Full extraction data
│   ├── document_pdfplumber_tables.csv   # Table data in CSV
│   ├── document_pdfplumber_text.jsonl   # Text blocks
│   ├── document_camelot-lattice.json    # Camelot results
│   ├── document_comparison.md           # Comparison report
│   └── document_comparison.html         # HTML report
```

**File Types:**
- **`.json`** - Complete extraction data with provenance
- **`.csv`** - Table data for spreadsheet import
- **`.jsonl`** - Text blocks (one per line)
- **`.md/.html`** - Human-readable comparison reports

---

## Understanding Results

### Web Interface Results

The web interface displays results in organized tabs:

- **Overview** - Summary statistics and quality scores
- **Tables** - Extracted table data with formatting
- **Text Blocks** - Text content with page references
- **Raw Data** - Complete JSON data for developers
- **Comparison Report** - Side-by-side method comparison

### Quality Metrics

**Quality Score (0-1)**: Higher = better extraction quality
- 🟢 0.8-1.0: Excellent, production-ready
- 🟡 0.6-0.8: Good, minor issues
- 🔴 <0.6: Poor, needs review
- ⚠️ Note: Quality scoring is still being refined

**Other Metrics:**
- **Tables Found**: Number of tables detected
- **Text Blocks**: Number of text sections extracted
- **Processing Time**: Extraction speed in seconds
- **Success Rate**: Percentage of successful extractions

### Zero-Hallucination Policy

**Deterministic methods NEVER invent data:**
- No guessing missing values
- No "fixing" unclear text
- No assumptions about data
- Flags unreadable content as empty
- Provides confidence scores when available
- Complete provenance for every data point

**LLM methods may hallucinate** - always cross-validate with deterministic methods for critical documents!

---

## Troubleshooting

### Common Issues

**Tesseract OCR or Poppler not working:**
```bash
# Check installation status
python scripts/check_dependencies.py

# Automated setup (Windows)
powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1

# Manual verification
tesseract --version
pdftoppm -h
pdftotext -v
```

**"Java not found" error:**
```bash
# Check Java installation
java -version
# If not found, install Java 8+ for Tabula support
```

**Camelot/Ghostscript issues:**
```bash
# Linux/macOS
sudo apt install ghostscript  # Ubuntu
brew install ghostscript      # macOS

# Windows: Download from https://www.ghostscript.com/
```

**Web interface not loading:**
```bash
# Check if Flask is installed
pip install flask

# Check if port 4000 is available
netstat -an | grep 4000
```

**API key errors:**
- Verify API keys are correct
- Check service quotas and billing
- Ensure proper permissions are set

---

## Advanced Usage

### LLM Integration

```bash
# Compare traditional vs AI methods
python -m pdfx_bench.cli --input invoice.pdf --method pdfplumber,llm-openai

# Use LLM for complex layouts
python -m pdfx_bench.cli --input complex.pdf --method llm-anthropic

# Cross-validate with multiple LLMs
python -m pdfx_bench.cli --input document.pdf --method llm-openai,llm-anthropic,llm-google
```

**LLM vs Traditional:**
- **Traditional**: Fast, deterministic, no hallucination, free
- **LLM**: Handles complex layouts, understands context, costs money
- **Best Practice**: Use both and compare for critical documents

---

## Testing

Run the test suite to verify your installation:

```bash
# Install test dependencies
pip install pytest

# Run basic tests
pytest tests/ -v

# Test specific methods
pytest tests/test_pdfplumber.py -v
```

---

## API Reference

### Supported Methods

| Method | Description | Requirements | Type |
|--------|-------------|--------------|------|
| `pdfplumber` | Text and simple tables | None | Local |
| `camelot-lattice` | Tables with visible borders | None | Local |
| `camelot-stream` | Tables without borders | None | Local |
| `tabula` | Academic table extraction | Java 8+ | Local |
| `textract` | AWS Textract | AWS credentials | Cloud |
| `docai` | Google Document AI | GCP credentials | Cloud |
| `azure` | Azure Document Intelligence | Azure credentials | Cloud |
| `llm-openai` | OpenAI GPT-4 Vision | OpenAI API key | LLM |
| `llm-anthropic` | Anthropic Claude | Anthropic API key | LLM |
| `llm-google` | Google Gemini | Google API key | LLM |

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--input` | PDF file or directory | `document.pdf` |
| `--method` | Extraction methods | `pdfplumber,camelot-lattice` |
| `--pages` | Page range | `"1,2,5-7"` |
| `--min-confidence` | Confidence threshold | `0.9` |
| `--out-dir` | Output directory | `./results/` |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [pdfplumber](https://github.com/jsvine/pdfplumber) - PDF text and table extraction
- [camelot](https://github.com/camelot-dev/camelot) - Table extraction library
- [tabula-py](https://github.com/chezou/tabula-py) - Python wrapper for tabula-java
- [Poppler](https://poppler.freedesktop.org/) - PDF rendering library and utilities
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - Open source OCR engine
- Cloud providers for their well-documented AI services
- Open source community for continuous improvements

---

## Support

- **Issues**: [GitHub Issues](https://github.com/nithingm/PDFXtract-Arena/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nithingm/PDFXtract-Arena/discussions)
- **Documentation**: This README and inline code comments
- **Web Interface**: Built-in help and tooltips

**Quick Help:**
- Start with local methods (no API keys needed)
- Use the web interface for easiest experience
- Check troubleshooting section for common issues
- Compare multiple methods for best results