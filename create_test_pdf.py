"""
Create a simple test PDF with text and tables for demonstration.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_test_pdf():
    """Create a test PDF with text and tables."""
    
    # Create PDF
    doc = SimpleDocTemplate("test_invoice.pdf", pagesize=letter)
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph("INVOICE #12345", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Company info
    company_info = Paragraph("""
    <b>ABC Company Inc.</b><br/>
    123 Business Street<br/>
    City, State 12345<br/>
    Phone: (555) 123-4567
    """, styles['Normal'])
    story.append(company_info)
    story.append(Spacer(1, 12))
    
    # Invoice details
    invoice_details = Paragraph("""
    <b>Bill To:</b><br/>
    XYZ Corporation<br/>
    456 Client Avenue<br/>
    Town, State 67890<br/><br/>
    
    <b>Invoice Date:</b> January 15, 2024<br/>
    <b>Due Date:</b> February 15, 2024<br/>
    <b>Terms:</b> Net 30
    """, styles['Normal'])
    story.append(invoice_details)
    story.append(Spacer(1, 20))
    
    # Line items table
    line_items_data = [
        ['Item', 'Description', 'Qty', 'Unit Price', 'Total'],
        ['001', 'Professional Services', '10', '$150.00', '$1,500.00'],
        ['002', 'Software License', '1', '$500.00', '$500.00'],
        ['003', 'Training Session', '2', '$300.00', '$600.00'],
        ['004', 'Support Package', '1', '$200.00', '$200.00'],
    ]
    
    line_items_table = Table(line_items_data, colWidths=[0.8*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    line_items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Right align numbers
    ]))
    
    story.append(line_items_table)
    story.append(Spacer(1, 20))
    
    # Totals table
    totals_data = [
        ['', '', '', 'Subtotal:', '$2,800.00'],
        ['', '', '', 'Tax (8.5%):', '$238.00'],
        ['', '', '', 'Total:', '$3,038.00'],
    ]
    
    totals_table = Table(totals_data, colWidths=[0.8*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, -1), (-1, -1), 12),
        ('LINEABOVE', (3, -1), (-1, -1), 2, colors.black),
    ]))
    
    story.append(totals_table)
    story.append(Spacer(1, 20))
    
    # Payment terms
    payment_terms = Paragraph("""
    <b>Payment Terms:</b><br/>
    Payment is due within 30 days of invoice date.<br/>
    Please remit payment to: ABC Company Inc., Account #123456789<br/>
    Thank you for your business!
    """, styles['Normal'])
    story.append(payment_terms)
    
    # Build PDF
    doc.build(story)
    print("Test PDF created: test_invoice.pdf")

if __name__ == "__main__":
    try:
        create_test_pdf()
    except ImportError:
        print("reportlab not installed. Installing...")
        import subprocess
        subprocess.check_call(["pip", "install", "reportlab"])
        create_test_pdf()
