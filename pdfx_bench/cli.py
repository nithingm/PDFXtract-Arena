"""
Command-line interface for PDFX-Bench.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root where .env is located
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, skip

from .detectors import detect_pdf_type, should_use_ocr, get_recommended_extractors, parse_page_range
from .normalize import DataNormalizer
from .scoring import QualityScorer, compare_extraction_results
from .exporters import ResultExporter
from .schema import ExtractionMethod, ExtractionResult
from .utils.logging import setup_logging
from .utils.io import find_pdf_files, ensure_dir
from .utils.timers import time_operation, performance_tracker

# Import adapters (with graceful handling of optional dependencies)
from .adapters.pdfplumber_adapter import PDFPlumberAdapter
from .adapters.camelot_adapter import CamelotAdapter
from .adapters.tabula_adapter import TabulaAdapter

# Optional OCR adapters
try:
    from .adapters.tesseract_ocr import TesseractOCRAdapter
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from .adapters.poppler_adapter import PopplerAdapter
    POPPLER_AVAILABLE = True
except ImportError:
    POPPLER_AVAILABLE = False

# Optional cloud adapters
try:
    from .adapters.adobe_extract_adapter import AdobeExtractAdapter
    ADOBE_AVAILABLE = True
except ImportError:
    ADOBE_AVAILABLE = False

try:
    from .adapters.textract_adapter import TextractAdapter
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

# Set availability flags - imports will be done dynamically
DOCAI_AVAILABLE = True
AZURE_READ_AVAILABLE = True
AZURE_LAYOUT_AVAILABLE = True
LLM_AVAILABLE = True

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog='pdfx-bench',
        description='PDFX-Bench: No-hallucination PDF extraction benchmark',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdfx-bench --input document.pdf --method auto
  pdfx-bench --input docs/ --method pdfplumber,camelot-lattice --pages "1,2,5-7"
  pdfx-bench --input file.pdf --method textract --min-confidence 0.9
  pdfx-bench --input scanned.pdf --ocr force --method auto
        """
    )
    
    # Input/Output
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Input PDF file or directory'
    )
    
    parser.add_argument(
        '--out-dir', '-o',
        type=str,
        default=None,
        help='Output directory (default: ./outputs/<timestamp>/)'
    )
    
    # Extraction methods
    parser.add_argument(
        '--method', '-m',
        type=str,
        default='auto',
        help='Extraction method(s): auto, pdfplumber, camelot-lattice, camelot-stream, '
             'tabula, poppler, tesseract, adobe, textract, docai, azure, llm-openai, llm-anthropic, llm-google '
             '(comma-separated for multiple)'
    )
    
    # Page selection
    parser.add_argument(
        '--pages', '-p',
        type=str,
        default=None,
        help='Page range: "1,2,5-7" (default: all pages)'
    )
    
    # OCR options
    parser.add_argument(
        '--ocr',
        choices=['auto', 'force', 'off'],
        default='auto',
        help='OCR mode for scanned PDFs (default: auto)'
    )
    
    # Quality filtering
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.9,
        help='Minimum confidence threshold for cloud APIs (default: 0.9)'
    )
    
    # Schema validation
    parser.add_argument(
        '--schema',
        type=str,
        default=None,
        help='Path to custom JSON schema for validation'
    )
    
    # Cloud credentials
    parser.add_argument(
        '--adobe-cred-file',
        type=str,
        default=None,
        help='Adobe credentials JSON file path'
    )
    
    parser.add_argument(
        '--aws-profile',
        type=str,
        default=None,
        help='AWS profile name'
    )
    
    parser.add_argument(
        '--gcp-processor-id',
        type=str,
        default=None,
        help='Google Document AI processor ID'
    )
    
    parser.add_argument(
        '--gcp-location',
        type=str,
        default='us',
        help='Google Document AI location (default: us)'
    )
    
    parser.add_argument(
        '--azure-endpoint',
        type=str,
        default=None,
        help='Azure Document Intelligence endpoint'
    )
    
    parser.add_argument(
        '--azure-key',
        type=str,
        default=None,
        help='Azure Document Intelligence API key'
    )

    # LLM API keys
    parser.add_argument(
        '--openai-api-key',
        type=str,
        default=None,
        help='OpenAI API key for LLM extraction'
    )

    parser.add_argument(
        '--anthropic-api-key',
        type=str,
        default=None,
        help='Anthropic API key for LLM extraction'
    )

    parser.add_argument(
        '--google-api-key',
        type=str,
        default=None,
        help='Google API key for LLM extraction'
    )
    
    # Report options
    parser.add_argument(
        '--report',
        choices=['md', 'html'],
        default='md',
        help='Report format (default: md)'
    )
    
    # Logging
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Log file path (default: console only)'
    )
    
    return parser


def setup_output_directory(out_dir: Optional[str]) -> Path:
    """Set up output directory."""
    if out_dir:
        output_path = Path(out_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"outputs/{timestamp}")
    
    ensure_dir(output_path)
    return output_path


def parse_methods(method_str: str) -> List[str]:
    """Parse method string into list of methods."""
    if method_str.lower() == 'auto':
        return ['auto']
    
    methods = [m.strip() for m in method_str.split(',')]
    
    # Validate methods
    valid_methods = {
        'pdfplumber', 'camelot-lattice', 'camelot-stream', 'tabula', 'poppler', 'tesseract',
        'adobe', 'textract', 'docai', 'azure-read', 'azure-layout',
        'llm-openai', 'llm-anthropic', 'llm-google'
    }
    
    for method in methods:
        if method not in valid_methods:
            raise ValueError(f"Invalid method: {method}")
    
    return methods


def create_adapter(method: str, **kwargs) -> Any:
    """Create adapter instance for the given method."""
    if method == 'pdfplumber':
        return PDFPlumberAdapter()
    elif method == 'camelot-lattice':
        return CamelotAdapter(mode='lattice')
    elif method == 'camelot-stream':
        return CamelotAdapter(mode='stream')
    elif method == 'tabula':
        return TabulaAdapter()
    elif method == 'poppler':
        if not POPPLER_AVAILABLE:
            raise RuntimeError("Poppler dependencies not installed. Install with: pip install pdf2image and ensure Poppler utilities are in PATH")
        return PopplerAdapter()
    elif method == 'tesseract':
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract OCR dependencies not installed. Install with: pip install pytesseract pdf2image")
        return TesseractOCRAdapter()
    elif method == 'adobe':
        if not ADOBE_AVAILABLE:
            raise RuntimeError("Adobe PDF Services SDK not installed. Install with: pip install pdfservices-sdk")
        return AdobeExtractAdapter(credentials_file=kwargs.get('adobe_cred_file'))
    elif method == 'textract':
        if not TEXTRACT_AVAILABLE:
            raise RuntimeError("AWS boto3 not installed. Install with: pip install boto3")
        return TextractAdapter(aws_profile=kwargs.get('aws_profile'))
    elif method == 'docai':
        try:
            from .adapters.docai_adapter import DocumentAIAdapter
            return DocumentAIAdapter(
                processor_id=kwargs.get('gcp_processor_id'),
                location=kwargs.get('gcp_location', 'us'),
                project_id=kwargs.get('gcp_project_id')
            )
        except ImportError:
            raise RuntimeError("Google Document AI library not installed. Install with: pip install google-cloud-documentai")
    elif method == 'azure-read':
        try:
            from .adapters.azure_read_adapter import AzureReadAdapter
            return AzureReadAdapter(
                endpoint=kwargs.get('azure_endpoint'),
                api_key=kwargs.get('azure_key')
            )
        except ImportError:
            raise RuntimeError("Azure Document Intelligence library not installed. Install with: pip install azure-ai-documentintelligence")
    elif method == 'azure-layout':
        try:
            from .adapters.azure_layout_adapter import AzureLayoutAdapter
            return AzureLayoutAdapter(
                endpoint=kwargs.get('azure_endpoint'),
                api_key=kwargs.get('azure_key')
            )
        except ImportError:
            raise RuntimeError("Azure Document Intelligence library not installed. Install with: pip install azure-ai-documentintelligence")
    elif method.startswith('llm-'):
        # LLM methods: llm-openai, llm-anthropic, llm-google
        try:
            from .adapters.llm_adapter import LLMAdapter

            provider = method.split('-')[1]  # Extract provider from method name
            model_map = {
                'openai': 'gpt-4-vision-preview',
                'anthropic': 'claude-3-sonnet-20240229',
                'google': 'gemini-pro-vision'
            }

            return LLMAdapter(
                provider=provider,
                model=model_map.get(provider, 'gpt-4-vision-preview'),
                api_key=kwargs.get(f'{provider}_api_key')
            )
        except ImportError:
            raise RuntimeError("LLM dependencies not installed. Install with: pip install openai anthropic google-generativeai")
    else:
        raise ValueError(f"Unknown method: {method}")


def extract_with_method(
    adapter: Any,
    pdf_path: Path,
    pages: Optional[List[int]],
    min_confidence: float,
    **kwargs
) -> ExtractionResult:
    """Extract content using a specific adapter."""
    method = adapter.method

    try:
        import time
        start_time = time.time()

        # Perform extraction
        document = adapter.extract(
            pdf_path=pdf_path,
            pages=pages,
            min_confidence=min_confidence,
            **kwargs
        )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Normalize result
        normalizer = DataNormalizer()
        result = normalizer.normalize_extraction_result(
            raw_result=document,
            method=method,
            processing_time=processing_time,
            success=True
        )

        return result

    except Exception as e:
        logger.error(f"Extraction failed with {method.value}: {e}")

        # Create failed result
        normalizer = DataNormalizer()
        result = normalizer.normalize_extraction_result(
            raw_result=None,
            method=method,
            processing_time=0,
            success=False,
            error_message=str(e)
        )

        return result


def process_pdf_file(
    pdf_path: Path,
    methods: List[str],
    pages: Optional[List[int]],
    ocr_mode: str,
    min_confidence: float,
    output_dir: Path,
    **kwargs
) -> Dict[str, Any]:
    """Process a single PDF file with specified methods."""
    logger.info(f"Processing PDF: {pdf_path}")
    
    # Detect PDF characteristics
    pdf_info = detect_pdf_type(pdf_path)
    
    # Determine methods to use
    if 'auto' in methods:
        if should_use_ocr(pdf_info, ocr_mode):
            logger.info("Scanned PDF detected, OCR will be used")
        
        recommended_methods = get_recommended_extractors(pdf_info)
        # Filter to available methods (skip unimplemented ones)
        available_methods = [m for m in recommended_methods 
                           if m not in ['docai', 'azure', 'tesseract']]
        methods_to_use = available_methods[:4]  # Limit to 4 methods for auto mode
    else:
        methods_to_use = methods
    
    logger.info(f"Using extraction methods: {methods_to_use}")
    
    # Extract with each method
    results = []
    for method in methods_to_use:
        try:
            adapter = create_adapter(method, **kwargs)
            result = extract_with_method(
                adapter=adapter,
                pdf_path=pdf_path,
                pages=pages,
                min_confidence=min_confidence,
                **kwargs
            )
            results.append(result)
            
            logger.info(f"Completed {method}: {result.success}")
            
        except NotImplementedError as e:
            logger.warning(f"Skipping {method}: {e}")
        except Exception as e:
            logger.error(f"Failed to create adapter for {method}: {e}")
    
    # Export results
    exporter = ResultExporter(output_dir)
    
    # Save individual results
    for result in results:
        exporter.export_extraction_result(result, pdf_path.stem)
    
    # Create comparison report
    comparison = compare_extraction_results(results)
    report_path = exporter.export_comparison_report(
        comparison, pdf_path.stem, kwargs.get('report', 'md')
    )
    
    logger.info(f"Results exported to: {output_dir}")
    logger.info(f"Comparison report: {report_path}")
    
    return {
        'pdf_path': str(pdf_path),
        'pdf_info': pdf_info,
        'methods_used': methods_to_use,
        'results': results,
        'comparison': comparison,
        'output_dir': str(output_dir)
    }


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path(args.log_file) if args.log_file else None
    setup_logging(
        level=args.log_level,
        log_file=log_file,
        json_format=True,
        console_output=True
    )
    
    try:
        # Setup output directory
        output_dir = setup_output_directory(args.out_dir)
        logger.info(f"Output directory: {output_dir}")
        
        # Find PDF files
        input_path = Path(args.input)
        pdf_files = find_pdf_files(input_path)
        logger.info(f"Found {len(pdf_files)} PDF file(s)")
        
        # Parse methods
        methods = parse_methods(args.method)
        
        # Parse pages
        pages = None
        if args.pages:
            # We'll parse pages per PDF since page counts may differ
            pass
        
        # Process each PDF
        all_results = []
        for pdf_path in pdf_files:
            try:
                # Parse pages for this specific PDF
                pdf_pages = None
                if args.pages:
                    pdf_info = detect_pdf_type(pdf_path)
                    pdf_pages = parse_page_range(args.pages, pdf_info.page_count)
                
                result = process_pdf_file(
                    pdf_path=pdf_path,
                    methods=methods,
                    pages=pdf_pages,
                    ocr_mode=args.ocr,
                    min_confidence=args.min_confidence,
                    output_dir=output_dir,
                    adobe_cred_file=args.adobe_cred_file,
                    aws_profile=args.aws_profile,
                    gcp_processor_id=args.gcp_processor_id,
                    gcp_location=args.gcp_location,
                    azure_endpoint=args.azure_endpoint,
                    azure_key=args.azure_key,
                    report=args.report
                )
                
                all_results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
                continue
        
        # Save summary
        summary = {
            'total_pdfs': len(pdf_files),
            'successful_pdfs': len(all_results),
            'methods_used': methods,
            'output_directory': str(output_dir),
            'processing_time': performance_tracker.get_all_stats()
        }
        
        summary_path = output_dir / 'summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Processing complete. Summary saved to: {summary_path}")
        
    except Exception as e:
        logger.error(f"CLI execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
