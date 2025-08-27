"""
PDFX-Bench: A no-hallucination PDF extraction benchmark tool.

This package provides a comprehensive framework for extracting text and tables
from PDFs using multiple extraction methods, normalizing results to a canonical
schema, and comparing quality across methods.
"""

__version__ = "1.0.0"
__author__ = "PDFX-Bench Team"
__description__ = "No-hallucination PDF extraction benchmark"

from .schema import (
    Document,
    Table,
    TableCell,
    TextBlock,
    KeyValue,
    ExtractionResult,
    ComparisonReport,
    ExtractionMethod,
    BoundingBox,
    Provenance,
    QuarantineEntry
)

__all__ = [
    "Document",
    "Table", 
    "TableCell",
    "TextBlock",
    "KeyValue",
    "ExtractionResult",
    "ComparisonReport",
    "ExtractionMethod",
    "BoundingBox",
    "Provenance",
    "QuarantineEntry"
]
