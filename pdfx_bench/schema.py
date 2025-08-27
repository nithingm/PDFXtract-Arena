"""
Pydantic models for PDFX-Bench canonical schema.
All extractors normalize their outputs to these models.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import re


class ExtractionMethod(str, Enum):
    """Supported extraction methods."""
    PDFPLUMBER = "pdfplumber"
    CAMELOT_LATTICE = "camelot-lattice"
    CAMELOT_STREAM = "camelot-stream"
    TABULA = "tabula"
    POPPLER = "poppler"
    ADOBE_EXTRACT = "adobe"
    AWS_TEXTRACT = "textract"
    GOOGLE_DOCAI = "docai"
    AZURE_READ = "azure-read"
    AZURE_LAYOUT = "azure-layout"
    TESSERACT_OCR = "tesseract"
    LLM_EXTRACTION = "llm"


class BoundingBox(BaseModel):
    """Bounding box coordinates (x0, y0, x1, y1)."""
    x0: float = Field(..., description="Left coordinate")
    y0: float = Field(..., description="Top coordinate")
    x1: float = Field(..., description="Right coordinate")
    y1: float = Field(..., description="Bottom coordinate")
    
    @validator('x1')
    def x1_greater_than_x0(cls, v, values):
        if 'x0' in values and v <= values['x0']:
            raise ValueError('x1 must be greater than x0')
        return v
    
    @validator('y1')
    def y1_greater_than_y0(cls, v, values):
        if 'y0' in values and v <= values['y0']:
            raise ValueError('y1 must be greater than y0')
        return v


class Provenance(BaseModel):
    """Provenance information for extracted data."""
    method: ExtractionMethod = Field(..., description="Extraction method used")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    bbox: Optional[BoundingBox] = Field(None, description="Bounding box if available")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score if available")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Original extractor-specific data")


class TextBlock(BaseModel):
    """A block of extracted text."""
    text: str = Field(..., description="Extracted text content")
    provenance: Provenance = Field(..., description="Extraction provenance")
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Text content cannot be empty')
        return v


class TableCell(BaseModel):
    """A single cell in a table."""
    raw_text: str = Field("", description="Raw text content (empty if unreadable)")
    row_idx: int = Field(..., ge=0, description="Row index (0-based)")
    col_idx: int = Field(..., ge=0, description="Column index (0-based)")
    is_header: bool = Field(False, description="Whether this cell is a header")
    provenance: Provenance = Field(..., description="Extraction provenance")
    
    # Parsed values (optional, derived from raw_text)
    parsed_number: Optional[float] = Field(None, description="Parsed numeric value if applicable")
    parsed_date: Optional[str] = Field(None, description="Parsed date in ISO format if applicable")
    
    @validator('parsed_number', pre=True)
    def parse_number(cls, v, values):
        if v is not None:
            return v
        
        raw_text = values.get('raw_text', '')
        if not raw_text:
            return None
            
        # Try to extract number from text
        number_pattern = r'[-+]?(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?'
        match = re.search(number_pattern, raw_text.replace('$', '').replace('%', ''))
        if match:
            try:
                return float(match.group().replace(',', ''))
            except ValueError:
                pass
        return None


class Table(BaseModel):
    """A table with cells."""
    cells: List[TableCell] = Field(..., description="List of table cells")
    table_id: str = Field(..., description="Unique identifier for this table")
    caption: Optional[str] = Field(None, description="Table caption if available")
    provenance: Provenance = Field(..., description="Table-level provenance")
    
    @property
    def rows(self) -> int:
        """Number of rows in the table."""
        return max((cell.row_idx for cell in self.cells), default=-1) + 1
    
    @property
    def cols(self) -> int:
        """Number of columns in the table."""
        return max((cell.col_idx for cell in self.cells), default=-1) + 1
    
    def get_cell(self, row: int, col: int) -> Optional[TableCell]:
        """Get cell at specific row/column."""
        for cell in self.cells:
            if cell.row_idx == row and cell.col_idx == col:
                return cell
        return None


class KeyValue(BaseModel):
    """A key-value pair extracted from the document."""
    key: str = Field(..., description="Key text")
    value: str = Field(..., description="Value text")
    provenance: Provenance = Field(..., description="Extraction provenance")
    
    @validator('key')
    def key_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Key cannot be empty')
        return v


class Document(BaseModel):
    """Complete document extraction result."""
    id: str = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original file name")
    page_count: int = Field(..., ge=1, description="Number of pages")
    
    # Extracted content
    text_blocks: List[TextBlock] = Field(default_factory=list, description="Extracted text blocks")
    tables: List[Table] = Field(default_factory=list, description="Extracted tables")
    key_values: List[KeyValue] = Field(default_factory=list, description="Extracted key-value pairs")
    
    # Metadata
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")
    
    @validator('file_name')
    def valid_filename(cls, v):
        if not v or '/' in v or '\\' in v:
            raise ValueError('Invalid file name')
        return v


class ExtractionResult(BaseModel):
    """Result from a single extraction method."""
    document: Document = Field(..., description="Extracted document")
    method: ExtractionMethod = Field(..., description="Extraction method used")
    success: bool = Field(..., description="Whether extraction was successful")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")
    
    # Quality metrics
    total_text_blocks: int = Field(0, ge=0, description="Number of text blocks extracted")
    total_tables: int = Field(0, ge=0, description="Number of tables extracted")
    total_cells: int = Field(0, ge=0, description="Total number of table cells")
    empty_cells: int = Field(0, ge=0, description="Number of empty table cells")
    avg_confidence: Optional[float] = Field(None, ge=0, le=1, description="Average confidence score")


class ComparisonReport(BaseModel):
    """Comparison report across multiple extraction methods."""
    document_id: str = Field(..., description="Document identifier")
    file_name: str = Field(..., description="Original file name")
    methods_compared: List[ExtractionMethod] = Field(..., description="Methods included in comparison")
    
    # Per-method results
    results: List[ExtractionResult] = Field(..., description="Results from each method")
    
    # Comparison metrics
    best_method_overall: Optional[ExtractionMethod] = Field(None, description="Best performing method overall")
    best_method_tables: Optional[ExtractionMethod] = Field(None, description="Best method for table extraction")
    best_method_text: Optional[ExtractionMethod] = Field(None, description="Best method for text extraction")
    
    # Cross-validation results
    table_count_consensus: Optional[int] = Field(None, description="Consensus table count across methods")
    numeric_validation_passed: bool = Field(False, description="Whether numeric cross-checks passed")
    
    generation_time: str = Field(..., description="Report generation timestamp")


class QuarantineEntry(BaseModel):
    """Entry for data that failed validation or quality checks."""
    original_data: Dict[str, Any] = Field(..., description="Original data that failed validation")
    method: ExtractionMethod = Field(..., description="Extraction method")
    failure_reason: str = Field(..., description="Reason for quarantine")
    page: int = Field(..., ge=1, description="Page number")
    timestamp: str = Field(..., description="Quarantine timestamp")
