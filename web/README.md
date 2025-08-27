# PDFX-Bench Web UI

A modern web interface for comparing PDF extraction methods with real-time processing and interactive results.

## Quick Start

1. **Start the Web Server**
   ```bash
   cd web
   python app.py
   ```

2. **Open in Browser**
   - Navigate to: http://localhost:4000
   - The interface will load automatically

## Features

### Upload & Configuration
- **Drag & Drop Upload**: Simply drag PDF files onto the upload area
- **Method Selection**: Choose from 10+ extraction methods
  - **Local Methods**: pdfplumber, camelot, tabula (free, fast)
  - **Cloud APIs**: AWS Textract, Google Document AI, Azure (accurate, costs money)
  - **LLM Methods**: OpenAI GPT-4, Anthropic Claude, Google Gemini (AI-powered)
- **One-Click All Methods**: Select all available methods instantly
- **API Key Management**: Secure input for cloud service credentials
- **Processing Options**: Confidence thresholds, page ranges

### Real-Time Processing
- **Live Progress Bar**: See extraction progress in real-time
- **Method-by-Method Updates**: Track which method is currently running
- **Error Handling**: Clear error messages and recovery options
- **Background Processing**: Non-blocking UI during extraction

### Interactive Results
- **Multi-Tab Interface**: Organized view of all results
- **Overview Dashboard**: Summary metrics and method rankings
- **Table Viewer**: Interactive table display with proper formatting
- **Text Block Explorer**: Browse extracted text with page information
- **Raw Data Inspector**: JSON view of complete extraction data
- **Comparison Report**: Business-friendly analysis and recommendations

### Export & Download
- **Multiple Formats**: JSON, CSV, JSONL downloads
- **Per-Method Exports**: Download results for specific extraction methods
- **Comparison Reports**: Formatted reports for stakeholders
- **Audit Trail**: Complete provenance information

## Use Cases

### Business Demonstrations
- **Stakeholder Presentations**: Visual comparison of extraction quality
- **ROI Analysis**: Processing time vs. accuracy trade-offs
- **Method Selection**: Data-driven decisions on which tools to use
- **Quality Assurance**: Cross-validation between multiple methods

### Research & Development
- **Algorithm Comparison**: Benchmark different extraction approaches
- **Document Analysis**: Understand PDF structure and complexity
- **Performance Testing**: Measure processing times and resource usage
- **Error Analysis**: Identify failure modes and edge cases

### Production Planning
- **Capacity Planning**: Estimate processing times for large batches
- **Cost Analysis**: Compare cloud API costs vs. local processing
- **Integration Testing**: Validate extraction quality before deployment
- **Workflow Design**: Optimize document processing pipelines

## Technical Details

### Architecture
- **Backend**: Flask web server with async processing
- **Frontend**: Bootstrap 5 + vanilla JavaScript
- **Processing**: Direct integration with PDFX-Bench CLI
- **Storage**: Session-based results with automatic cleanup

### API Endpoints
- `POST /upload` - Upload PDF and start processing
- `GET /status/<session_id>` - Get processing status
- `GET /results/<session_id>` - Get extraction results
- `GET /download/<session_id>/<method>/<format>` - Download files
- `GET /report/<session_id>` - Get comparison report

### Security Features
- **File Type Validation**: Only PDF files accepted
- **Size Limits**: 50MB maximum file size
- **Session Isolation**: Each upload gets unique session ID
- **API Key Protection**: Credentials not stored permanently

## User Interface

### Design Principles
- **Mobile-First**: Responsive design works on all devices
- **Accessibility**: WCAG compliant with keyboard navigation
- **Performance**: Optimized for fast loading and smooth interactions
- **Clarity**: Clear visual hierarchy and intuitive workflows

### Visual Indicators
- **Green**: High quality results (>0.8 score)
- **Yellow**: Good results (0.6-0.8 score)
- **Red**: Poor results (<0.6 score)
- **Badges**: Method types (local/cloud/LLM)
- **Timing**: Real-time processing duration

## Troubleshooting

### Common Issues

**Server Won't Start**
```bash
# Install dependencies
pip install flask markdown

# Check port availability
netstat -an | findstr :4000
```

**Upload Fails**
- Ensure file is a valid PDF
- Check file size (max 50MB)
- Verify network connection

**Processing Errors**
- Check API keys for cloud methods
- Ensure all dependencies installed
- Review browser console for errors

**No Results Displayed**
- Wait for processing to complete
- Check browser network tab
- Refresh page and try again

### Performance Tips
- **Local Methods Only**: Fastest processing, no API costs
- **Specific Pages**: Use page ranges for large documents
- **Confidence Thresholds**: Filter low-quality extractions
- **Method Selection**: Choose appropriate methods for document type

## Future Enhancements

- **Batch Processing**: Upload multiple PDFs at once
- **Result Comparison**: Side-by-side method comparisons
- **Custom Schemas**: User-defined validation rules
- **Export Templates**: Customizable report formats
- **User Accounts**: Save sessions and preferences
- **API Integration**: RESTful API for programmatic access

## Support

For issues or questions:
1. Check the main PDFX-Bench documentation
2. Review the troubleshooting section above
3. Check browser console for error messages
4. Verify all dependencies are installed correctly

The web interface provides a user-friendly way to demonstrate PDFX-Bench capabilities and make data-driven decisions about PDF extraction methods!