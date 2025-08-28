"""
PDFX-Bench Web UI
A web interface for comparing PDF extraction methods.
"""

import os
import sys
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import markdown

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from parent directory where .env is located
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, skip

# Add parent directory to path to import pdfx_bench
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import dependency checker
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

# Update PATH to include Tesseract and Poppler locations from environment variables
tesseract_path = os.getenv('TESSERACT_CMD')
poppler_path = os.getenv('POPPLER_PATH')

# Add paths to environment if they exist and aren't already in PATH
for path in [tesseract_path, poppler_path]:
    if path and os.path.exists(path) and path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + path

try:
    from check_dependencies import DependencyChecker
    dependency_checker = DependencyChecker()
except ImportError:
    dependency_checker = None

app = Flask(__name__)
app.secret_key = 'pdfx-bench-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Configuration
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
RESULTS_FOLDER = Path(__file__).parent / 'results'
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure directories exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)

# Global storage for processing status
processing_status = {}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_available_methods():
    """Get list of available extraction methods."""
    # Check if Adobe credentials are available from environment
    adobe_available = bool(os.getenv('ADOBE_CLIENT_ID') and os.getenv('ADOBE_CLIENT_SECRET'))

    # Check if AWS credentials are available from environment
    aws_available = bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))

    methods = [
        {'id': 'pdfplumber', 'name': 'PDFplumber', 'description': 'Fast text and basic table extraction', 'type': 'local'},
        {'id': 'camelot-lattice', 'name': 'Camelot Lattice', 'description': 'Tables with visible borders', 'type': 'local'},
        {'id': 'camelot-stream', 'name': 'Camelot Stream', 'description': 'Tables without borders', 'type': 'local'},
        {'id': 'tabula', 'name': 'Tabula', 'description': 'Academic table extraction', 'type': 'local'},
        {'id': 'poppler', 'name': 'Poppler', 'description': 'PDF utilities for text extraction', 'type': 'local'},
        {'id': 'tesseract', 'name': 'Tesseract OCR', 'description': 'OCR for scanned PDFs', 'type': 'local'},
        {'id': 'adobe', 'name': 'Adobe PDF Extract', 'description': 'Advanced AI-powered text and table extraction', 'type': 'cloud', 'env_available': adobe_available},
        {'id': 'amazon-detect-text', 'name': 'Amazon Textract (DetectDocumentText)', 'description': 'Basic OCR - extracts lines and words from documents', 'type': 'cloud', 'env_available': aws_available},
        {'id': 'amazon-analyze-document', 'name': 'Amazon Textract (AnalyzeDocument)', 'description': 'Advanced extraction - forms, tables, signatures, and structure', 'type': 'cloud', 'env_available': aws_available},
        {'id': 'google-ocr', 'name': 'Google Document AI (OCR)', 'description': 'Google cloud text extraction', 'type': 'cloud'},
        {'id': 'google-form', 'name': 'Google Document AI (Form Parser)', 'description': 'Google cloud form and table extraction', 'type': 'cloud'},
        {'id': 'google-layout', 'name': 'Google Document AI (Layout Parser)', 'description': 'Google cloud layout understanding', 'type': 'cloud'},
        {'id': 'azure-read', 'name': 'Azure Document Intelligence (Read)', 'description': 'Microsoft cloud text extraction', 'type': 'cloud'},
        {'id': 'azure-layout', 'name': 'Azure Document Intelligence (Layout)', 'description': 'Microsoft cloud text and table extraction', 'type': 'cloud'},
        {'id': 'llm-openai', 'name': 'OpenAI GPT-4 Vision', 'description': 'AI-powered extraction', 'type': 'llm'},
        {'id': 'llm-anthropic', 'name': 'Anthropic Claude', 'description': 'AI document analysis', 'type': 'llm'},
        {'id': 'llm-google', 'name': 'Google Gemini', 'description': 'Multimodal AI extraction', 'type': 'llm'},
    ]

    # Set availability for all methods
    for method in methods:
        method_id = method['id']

        # Basic local methods are always available
        if method_id in ['pdfplumber', 'camelot-lattice', 'camelot-stream']:
            method['available'] = True
        # Tabula may require Java but is generally available
        elif method_id == 'tabula':
            method['available'] = True
            method['reason'] = 'May require Java installation'
        # Cloud and LLM methods require API keys
        elif method['type'] in ['cloud', 'llm']:
            # Check if environment credentials are available
            method['available'] = method.get('env_available', False)
            if method_id in ['google-ocr', 'google-form', 'google-layout']:
                method['reason'] = 'Requires Google Cloud Project ID and Processor ID'
            elif method_id in ['azure-read', 'azure-layout']:
                method['reason'] = 'Requires Azure Endpoint and API Key'
            elif method_id == 'llm-openai':
                method['reason'] = 'Requires OpenAI API key'
            elif method_id == 'llm-anthropic':
                method['reason'] = 'Requires Anthropic API key'
            elif method_id == 'llm-google':
                method['reason'] = 'Requires Google API key'
            elif method_id in ['amazon-detect-text', 'amazon-analyze-document']:
                method['reason'] = 'Requires AWS Access Key ID and Secret Access Key'

    # Check OCR dependencies availability dynamically
    if dependency_checker:
        dependency_checker.check_all()
        availability_status = dependency_checker.get_availability_status()
        tesseract_available = availability_status['tesseract_available']
        poppler_available = availability_status['poppler_available']

        # Update OCR method availability
        for method in methods:
            if method['id'] == 'tesseract':
                method['available'] = tesseract_available
                if not tesseract_available:
                    method['reason'] = 'Requires Tesseract OCR and Poppler installation'
            elif method['id'] == 'poppler':
                method['available'] = poppler_available
                if not poppler_available:
                    method['reason'] = 'Requires Poppler utilities and pdf2image installation'

    # Check Azure availability from environment variables
    azure_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
    azure_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
    azure_available = bool(azure_endpoint and azure_key)

    for method in methods:
        if method['id'] in ['azure-read', 'azure-layout']:
            method['available'] = azure_available
            if not azure_available:
                method['reason'] = 'Requires Azure Endpoint and API Key'

    # Check Adobe availability from environment variables
    for method in methods:
        if method['id'] == 'adobe':
            method['available'] = adobe_available
            if not adobe_available:
                method['reason'] = 'Requires Adobe Client ID and Client Secret'

    # Check Google availability from environment variables
    google_project_id = os.getenv('GCP_PROJECT_ID')
    google_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    google_ocr_processor = os.getenv('GCP_PROCESSOR_ID_OCR')
    google_form_processor = os.getenv('GCP_PROCESSOR_ID_FORM')
    google_layout_processor = os.getenv('GCP_PROCESSOR_ID_LAYOUT')

    # Debug logging
    app.logger.debug(f"Google env vars - Project: {google_project_id}, Creds: {google_credentials}, OCR: {google_ocr_processor}, Form: {google_form_processor}, Layout: {google_layout_processor}")

    for method in methods:
        if method['id'] == 'google-ocr':
            method['available'] = bool(google_project_id and google_credentials and google_ocr_processor)
            app.logger.debug(f"Google OCR availability: {method['available']}")
            if not method['available']:
                method['reason'] = 'Requires Google Cloud Project ID, Credentials, and OCR Processor ID'
        elif method['id'] == 'google-form':
            method['available'] = bool(google_project_id and google_credentials and google_form_processor)
            app.logger.debug(f"Google Form availability: {method['available']}")
            if not method['available']:
                method['reason'] = 'Requires Google Cloud Project ID, Credentials, and Form Processor ID'
        elif method['id'] == 'google-layout':
            method['available'] = bool(google_project_id and google_credentials and google_layout_processor)
            app.logger.debug(f"Google Layout availability: {method['available']}")
            if not method['available']:
                method['reason'] = 'Requires Google Cloud Project ID, Credentials, and Layout Processor ID'

    return methods

def process_pdf_async(session_id: str, pdf_path: Path, methods: List[str], options: Dict[str, Any]):
    """Process PDF asynchronously and update status."""
    # Initialize status first to ensure it exists
    processing_status[session_id] = {
        'status': 'starting',
        'progress': 0,
        'current_method': None,
        'completed_methods': [],
        'results': {},
        'error': None,
        'start_time': datetime.now().isoformat(),
        'pdf_path': str(pdf_path)  # Store PDF path for viewer
    }

    try:
        # Import here to avoid startup issues
        from pdfx_bench.cli import create_adapter, extract_with_method
        from pdfx_bench.detectors import detect_pdf_type
        from pdfx_bench.scoring import compare_extraction_results
        from pdfx_bench.exporters import ResultExporter

        # Detect PDF type
        processing_status[session_id]['status'] = 'analyzing'
        processing_status[session_id]['progress'] = 5

        pdf_info = detect_pdf_type(pdf_path)

        # Process each method
        total_methods = len(methods)
        results = {}

        for i, method in enumerate(methods):
            processing_status[session_id]['current_method'] = method
            processing_status[session_id]['progress'] = 10 + (i * 70 // total_methods)

            try:
                # Create adapter
                adapter = create_adapter(method, **options)

                # Extract content
                result = extract_with_method(
                    adapter=adapter,
                    pdf_path=pdf_path,
                    pages=options.get('pages'),
                    min_confidence=options.get('min_confidence', 0.0)
                )

                results[method] = result
                processing_status[session_id]['completed_methods'].append(method)

            except Exception as e:
                processing_status[session_id]['results'][method] = {'error': str(e)}

        # Generate comparison
        processing_status[session_id]['status'] = 'comparing'
        processing_status[session_id]['progress'] = 85

        if len(results) > 1:
            # Convert results dict to list for comparison function
            results_list = list(results.values())
            comparison = compare_extraction_results(results_list)
        else:
            comparison = {'single_method': True}

        # Export results
        processing_status[session_id]['status'] = 'exporting'
        processing_status[session_id]['progress'] = 95

        session_results_dir = RESULTS_FOLDER / session_id
        session_results_dir.mkdir(exist_ok=True)

        exporter = ResultExporter(session_results_dir)

        # Export individual results
        for method, result in results.items():
            exporter.export_extraction_result(result, pdf_path.stem)

        # Export comparison if multiple methods
        if len(results) > 1:
            comparison_report_path = exporter.export_comparison_report(comparison, pdf_path.stem)
            comparison_report = str(comparison_report_path)  # Convert Path to string for JSON serialization
        else:
            comparison_report = None

        # Calculate quality scores for each result
        from pdfx_bench.scoring import QualityScorer
        scorer = QualityScorer()

        # Convert results to serializable format
        serializable_results = {}
        for method, result in results.items():
            # Calculate quality score for this result
            quality_data = scorer.score_extraction_result(result)
            quality_score = quality_data.get('overall_score', 0.0)

            serializable_results[method] = {
                'id': result.document.id,
                'file_name': result.document.file_name,
                'page_count': result.document.page_count,
                'processing_time': result.processing_time,
                'success': result.success,
                'error_message': result.error_message,
                'quality_score': quality_score,
                'tables': [
                    {
                        'table_id': table.table_id,
                        'cells': [
                            {
                                'raw_text': cell.raw_text,
                                'row_idx': cell.row_idx,
                                'col_idx': cell.col_idx,
                                'is_header': cell.is_header,
                                'provenance': {
                                    'page': cell.provenance.page if cell.provenance else None,
                                    'confidence': cell.provenance.confidence if cell.provenance else None
                                }
                            } for cell in table.cells
                        ]
                    } for table in result.document.tables
                ],
                'text_blocks': [
                    {
                        'text': block.text,
                        'provenance': {
                            'page': block.provenance.page if block.provenance else None,
                            'confidence': block.provenance.confidence if block.provenance else None
                        }
                    } for block in result.document.text_blocks
                ],
                'key_values': [
                    {
                        'key': kv.key,
                        'value': kv.value,
                        'provenance': {
                            'page': kv.provenance.page if kv.provenance else None,
                            'confidence': kv.provenance.confidence if kv.provenance else None
                        }
                    } for kv in result.document.key_values
                ],
                'extraction_metadata': result.document.extraction_metadata or {}
            }

        # Update final status
        processing_status[session_id].update({
            'status': 'completed',
            'progress': 100,
            'results': serializable_results,
            'comparison': comparison,
            'comparison_report': comparison_report,
            'pdf_info': {
                'file_name': pdf_path.name,
                'page_count': pdf_info.page_count if pdf_info else 1,
                'is_scanned': pdf_info.is_scanned if pdf_info else False
            },
            'end_time': datetime.now().isoformat()
        })

    except Exception as e:
        # Ensure session exists before updating
        if session_id in processing_status:
            processing_status[session_id].update({
                'status': 'error',
                'error': str(e),
                'end_time': datetime.now().isoformat()
            })
        else:
            # Recreate session if it was lost
            processing_status[session_id] = {
                'status': 'error',
                'error': str(e),
                'progress': 0,
                'current_method': None,
                'completed_methods': [],
                'results': {},
                'start_time': datetime.now().isoformat(),
                'end_time': datetime.now().isoformat()
            }

@app.route('/')
def index():
    """Main page."""
    methods = get_available_methods()
    # Check if Adobe credentials are available from environment
    adobe_env_available = bool(os.getenv('ADOBE_CLIENT_ID') and os.getenv('ADOBE_CLIENT_SECRET'))
    # Check if AWS credentials are available from environment
    aws_env_available = bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
    return render_template('index.html', methods=methods, adobe_env_available=adobe_env_available, aws_env_available=aws_env_available)

@app.route('/api/methods')
def api_methods():
    """Get available extraction methods with dynamic availability checking."""
    try:
        methods = get_available_methods()
        return jsonify(methods)
    except Exception as e:
        app.logger.error(f"Error getting methods: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing."""
    # Check for both 'file' and 'pdf_file' for backward compatibility
    file = request.files.get('pdf_file') or request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    session['current_session'] = session_id
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    file_path = UPLOAD_FOLDER / f"{session_id}_{filename}"
    file.save(file_path)
    
    # Get processing options
    methods = request.form.getlist('methods')
    if not methods:
        return jsonify({'error': 'No extraction methods selected'}), 400
    
    # Parse options
    options = {
        'min_confidence': float(request.form.get('min_confidence', 0.0)),
        'pages': None,  # TODO: Parse page ranges
    }
    
    # Add API keys if provided, or use environment variables as defaults
    for key in ['aws_access_key_id', 'aws_secret_access_key', 'aws_region',
                'aws_access_key', 'aws_secret_key', 'google_application_credentials', 'gcp_project_id', 'gcp_processor_id_ocr',
                'gcp_processor_id_form', 'gcp_processor_id_layout', 'gcp_location',
                'azure_endpoint', 'azure_key', 'openai_api_key', 'anthropic_api_key', 'google_api_key',
                'adobe_client_id', 'adobe_client_secret']:
        value = request.form.get(key)
        if value:
            options[key] = value

    # Add environment variables as defaults for AWS credentials if not provided via UI
    if not options.get('aws_access_key_id') and os.getenv('AWS_ACCESS_KEY_ID'):
        options['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
    if not options.get('aws_secret_access_key') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        options['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
    if not options.get('aws_region') and os.getenv('AWS_DEFAULT_REGION'):
        options['aws_region'] = os.getenv('AWS_DEFAULT_REGION')

    # Add environment variables as defaults for Adobe credentials if not provided via UI
    if not options.get('adobe_client_id') and os.getenv('ADOBE_CLIENT_ID'):
        options['adobe_client_id'] = os.getenv('ADOBE_CLIENT_ID')
    if not options.get('adobe_client_secret') and os.getenv('ADOBE_CLIENT_SECRET'):
        options['adobe_client_secret'] = os.getenv('ADOBE_CLIENT_SECRET')
    
    # Start processing in background
    thread = threading.Thread(
        target=process_pdf_async,
        args=(session_id, file_path, methods, options)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'session_id': session_id,
        'filename': filename,
        'methods': methods
    })

@app.route('/status/<session_id>')
def get_status(session_id):
    """Get processing status."""
    status = processing_status.get(session_id, {'status': 'not_found'})
    return jsonify(status)

@app.route('/results/<session_id>')
def get_results(session_id):
    """Get processing results."""
    if session_id not in processing_status:
        return jsonify({'error': 'Session not found'}), 404
    
    status = processing_status[session_id]
    if status['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    return jsonify({
        'results': status['results'],
        'comparison': status.get('comparison'),
        'pdf_info': status.get('pdf_info')
    })

@app.route('/download/<session_id>/<method>/<format>')
def download_result(session_id, method, format):
    """Download result file."""
    try:
        if session_id not in processing_status:
            return jsonify({'error': 'Session not found'}), 404

        # For now, return the data directly as JSON since file export isn't fully implemented
        status = processing_status[session_id]
        if status['status'] != 'completed':
            return jsonify({'error': 'Processing not completed'}), 400

        result = status['results'].get(method)
        if not result:
            return jsonify({'error': 'Method not found'}), 404

        if format == 'json':
            response = app.response_class(
                response=json.dumps(result, indent=2),
                status=200,
                mimetype='application/json'
            )
            response.headers['Content-Disposition'] = f'attachment; filename={method}_result.json'
            return response
        elif format == 'csv':
            # Convert tables to CSV format
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(['table_id', 'row', 'col', 'text', 'is_header', 'page'])

            # Write table data
            for table in result.get('tables', []):
                for cell in table.get('cells', []):
                    writer.writerow([
                        table.get('table_id', ''),
                        cell.get('row_idx', ''),
                        cell.get('col_idx', ''),
                        cell.get('raw_text', ''),
                        cell.get('is_header', False),
                        cell.get('provenance', {}).get('page', '')
                    ])

            response = app.response_class(
                response=output.getvalue(),
                status=200,
                mimetype='text/csv'
            )
            response.headers['Content-Disposition'] = f'attachment; filename={method}_tables.csv'
            return response
        elif format == 'jsonl':
            # Convert text blocks to JSONL format
            lines = []
            for block in result.get('text_blocks', []):
                lines.append(json.dumps(block))

            response = app.response_class(
                response='\n'.join(lines),
                status=200,
                mimetype='application/x-jsonlines'
            )
            response.headers['Content-Disposition'] = f'attachment; filename={method}_text.jsonl'
            return response
        else:
            return jsonify({'error': 'Invalid format'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/report/<session_id>')
def get_report(session_id):
    """Get comparison report as HTML."""
    try:
        if session_id not in processing_status:
            return jsonify({'error': 'Session not found'}), 404

        status = processing_status[session_id]
        if status['status'] != 'completed':
            return jsonify({'error': 'Processing not completed'}), 400

        # Generate a simple HTML report
        results = status['results']
        comparison = status.get('comparison', {})

        html = f"""
        <div class="report-content">
            <h3> PDFXtract-Arena Extraction Comparison Report</h3>
            <p><strong> Document:</strong> {status['pdf_info']['file_name']}</p>
            <p><strong> Generated:</strong> {status['end_time']}</p>

            <h4> Executive Summary</h4>
            <p>This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms.</p>
            <ul>
                <li><strong> Methods Tested:</strong> {len(results)}</li>
                <li><strong> Best Overall:</strong> {comparison.get('best_overall', 'N/A')}</li>
                <li><strong> Best for Tables:</strong> {comparison.get('best_tables', 'N/A')}</li>
                <li><strong> Best for Text:</strong> {comparison.get('best_text', 'N/A')}</li>
            </ul>

            <h4> Performance Metrics</h4>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Tables Found</th>
                        <th>Text Blocks</th>
                        <th>Processing Time</th>
                    </tr>
                </thead>
                <tbody>
        """

        for method, result in results.items():
            html += f"""
                    <tr>
                        <td>{method}</td>
                        <td>{len(result.get('tables', []))}</td>
                        <td>{len(result.get('text_blocks', []))}</td>
                        <td>{result.get('processing_time', 0):.3f}s</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        """

        # Check for Amazon Textract multi-page warnings
        amazon_warnings = []
        for method, result in results.items():
            if method.startswith('amazon-') and result.get('extraction_metadata', {}).get('multipage_warning'):
                metadata = result['extraction_metadata']
                amazon_warnings.append({
                    'method': method,
                    'warning': metadata['multipage_warning'],
                    'original_pages': metadata.get('original_page_count', 'unknown'),
                    'processed_pages': metadata.get('processed_pages', 1)
                })

        # Add warnings section if any Amazon methods had multi-page limitations
        if amazon_warnings:
            html += """
            <div class="alert alert-warning mt-4">
                <h4><i class="fas fa-exclamation-triangle"></i> ⚠️ Important Processing Limitations</h4>
                <p><strong>Amazon Textract Multi-page PDF Limitations:</strong></p>
                <ul>
            """
            for warning in amazon_warnings:
                method_display = warning['method'].replace('amazon-', 'Amazon Textract ').replace('-', ' ').title()
                html += f"""
                    <li><strong>{method_display}:</strong> {warning['warning']}</li>
                """
            html += """
                </ul>
                <p><small><strong>Note:</strong> Amazon Textract's synchronous APIs (DetectDocumentText and AnalyzeDocument) only support single-page documents. For complete multi-page processing, consider using other extraction methods or Amazon Textract's asynchronous APIs.</small></p>
            </div>
            """

        html += """
            <h4>🔍 Key Findings</h4>
            <ul>
                <li>✅ Processing times show efficiency of each method</li>
                <li>✅ Multiple methods provide cross-validation opportunities</li>
                <li>✅ Complete provenance tracking for audit trails</li>
            </ul>
        </div>
        """

        return html

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf/<session_id>')
def get_pdf(session_id):
    """Serve the original PDF file for viewing."""
    try:
        if session_id not in processing_status:
            return jsonify({'error': 'Session not found'}), 404

        status = processing_status[session_id]
        pdf_path = status.get('pdf_path')

        if not pdf_path or not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF file not found'}), 404

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False,  # Display in browser, not download
            download_name=os.path.basename(pdf_path)
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
