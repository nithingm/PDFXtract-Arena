"""
Normalization utilities for PDFX-Bench.
Convert extractor-specific outputs to canonical schema.
"""

import logging
from typing import Dict, Any, List, Optional
from .schema import (
    Document, Table, TableCell, TextBlock, KeyValue,
    ExtractionMethod, ExtractionResult
)
from .utils.timers import time_operation

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes data from different extractors to canonical schema."""
    
    def __init__(self):
        self.quarantine_entries = []
    
    def normalize_extraction_result(
        self,
        raw_result: Any,
        method: ExtractionMethod,
        processing_time: float,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> ExtractionResult:
        """
        Normalize extraction result to standard format.
        
        Args:
            raw_result: Raw result from extractor
            method: Extraction method used
            processing_time: Time taken for extraction
            success: Whether extraction was successful
            error_message: Error message if extraction failed
            
        Returns:
            Normalized ExtractionResult
        """
        with time_operation("normalize_extraction_result"):
            if not success or not isinstance(raw_result, Document):
                # Create empty document for failed extractions
                document = Document(
                    id="unknown",
                    file_name="unknown",
                    page_count=1  # Must be at least 1 per schema requirement
                )
            else:
                document = raw_result
                # Apply normalization rules
                document = self._apply_normalization_rules(document, method)
            
            # Calculate quality metrics
            total_text_blocks = len(document.text_blocks)
            total_tables = len(document.tables)
            total_cells = sum(len(table.cells) for table in document.tables)
            empty_cells = sum(
                1 for table in document.tables
                for cell in table.cells
                if not cell.raw_text.strip()
            )
            
            # Calculate average confidence
            confidences = []
            for table in document.tables:
                if table.provenance.confidence is not None:
                    confidences.append(table.provenance.confidence)
                for cell in table.cells:
                    if cell.provenance.confidence is not None:
                        confidences.append(cell.provenance.confidence)
            
            for text_block in document.text_blocks:
                if text_block.provenance.confidence is not None:
                    confidences.append(text_block.provenance.confidence)
            
            for kv in document.key_values:
                if kv.provenance.confidence is not None:
                    confidences.append(kv.provenance.confidence)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else None
            
            result = ExtractionResult(
                document=document,
                method=method,
                success=success,
                error_message=error_message,
                processing_time=processing_time,
                total_text_blocks=total_text_blocks,
                total_tables=total_tables,
                total_cells=total_cells,
                empty_cells=empty_cells,
                avg_confidence=avg_confidence
            )
            
            return result
    
    def _apply_normalization_rules(
        self,
        document: Document,
        method: ExtractionMethod
    ) -> Document:
        """Apply method-specific normalization rules."""
        
        # Normalize text blocks
        normalized_text_blocks = []
        for text_block in document.text_blocks:
            normalized_block = self._normalize_text_block(text_block, method)
            if normalized_block:
                normalized_text_blocks.append(normalized_block)
        
        # Normalize tables
        normalized_tables = []
        for table in document.tables:
            normalized_table = self._normalize_table(table, method)
            if normalized_table:
                normalized_tables.append(normalized_table)
        
        # Normalize key-value pairs
        normalized_key_values = []
        for kv in document.key_values:
            normalized_kv = self._normalize_key_value(kv, method)
            if normalized_kv:
                normalized_key_values.append(normalized_kv)
        
        # Create normalized document
        normalized_document = Document(
            id=document.id,
            file_name=document.file_name,
            page_count=document.page_count,
            text_blocks=normalized_text_blocks,
            tables=normalized_tables,
            key_values=normalized_key_values,
            extraction_metadata=document.extraction_metadata
        )
        
        return normalized_document
    
    def _normalize_text_block(
        self,
        text_block: TextBlock,
        method: ExtractionMethod
    ) -> Optional[TextBlock]:
        """Normalize a text block."""
        try:
            # Clean up text
            normalized_text = self._clean_text(text_block.text)
            
            if not normalized_text.strip():
                logger.debug(f"Empty text block after normalization from {method}")
                return None
            
            # Create normalized text block
            normalized_block = TextBlock(
                text=normalized_text,
                provenance=text_block.provenance
            )
            
            return normalized_block
        
        except Exception as e:
            logger.warning(f"Failed to normalize text block from {method}: {e}")
            self._quarantine_data(text_block.dict(), method, str(e))
            return None
    
    def _normalize_table(
        self,
        table: Table,
        method: ExtractionMethod
    ) -> Optional[Table]:
        """Normalize a table."""
        try:
            normalized_cells = []
            
            for cell in table.cells:
                normalized_cell = self._normalize_table_cell(cell, method)
                if normalized_cell is not None:  # Allow empty cells
                    normalized_cells.append(normalized_cell)
            
            if not normalized_cells:
                logger.debug(f"No valid cells in table {table.table_id} from {method}")
                return None
            
            # Validate table structure
            if not self._validate_table_structure(normalized_cells):
                logger.warning(f"Invalid table structure for {table.table_id} from {method}")
                self._quarantine_data(table.dict(), method, "Invalid table structure")
                return None
            
            normalized_table = Table(
                cells=normalized_cells,
                table_id=table.table_id,
                caption=table.caption,
                provenance=table.provenance
            )
            
            return normalized_table
        
        except Exception as e:
            logger.warning(f"Failed to normalize table {table.table_id} from {method}: {e}")
            self._quarantine_data(table.dict(), method, str(e))
            return None
    
    def _normalize_table_cell(
        self,
        cell: TableCell,
        method: ExtractionMethod
    ) -> Optional[TableCell]:
        """Normalize a table cell."""
        try:
            # Clean up cell text
            normalized_text = self._clean_text(cell.raw_text)
            
            # Create normalized cell (allow empty cells)
            normalized_cell = TableCell(
                raw_text=normalized_text,
                row_idx=cell.row_idx,
                col_idx=cell.col_idx,
                is_header=cell.is_header,
                provenance=cell.provenance,
                parsed_number=cell.parsed_number,
                parsed_date=cell.parsed_date
            )
            
            return normalized_cell
        
        except Exception as e:
            logger.warning(f"Failed to normalize cell ({cell.row_idx}, {cell.col_idx}) from {method}: {e}")
            return None
    
    def _normalize_key_value(
        self,
        kv: KeyValue,
        method: ExtractionMethod
    ) -> Optional[KeyValue]:
        """Normalize a key-value pair."""
        try:
            # Clean up key and value
            normalized_key = self._clean_text(kv.key)
            normalized_value = self._clean_text(kv.value)
            
            if not normalized_key.strip():
                logger.debug(f"Empty key after normalization from {method}")
                return None
            
            normalized_kv = KeyValue(
                key=normalized_key,
                value=normalized_value,
                provenance=kv.provenance
            )
            
            return normalized_kv
        
        except Exception as e:
            logger.warning(f"Failed to normalize key-value pair from {method}: {e}")
            self._quarantine_data(kv.dict(), method, str(e))
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Remove control characters but keep newlines and tabs
        cleaned = "".join(char for char in cleaned if ord(char) >= 32 or char in '\n\t')
        
        return cleaned.strip()
    
    def _validate_table_structure(self, cells: List[TableCell]) -> bool:
        """Validate that table has a consistent structure."""
        if not cells:
            return False
        
        # Check for consistent row/column indices
        rows = set(cell.row_idx for cell in cells)
        cols = set(cell.col_idx for cell in cells)
        
        # Check for reasonable table dimensions
        max_row = max(rows) if rows else 0
        max_col = max(cols) if cols else 0
        
        # Table should not be too sparse
        expected_cells = (max_row + 1) * (max_col + 1)
        actual_cells = len(cells)
        
        # Allow up to 50% sparsity
        if actual_cells < expected_cells * 0.5:
            logger.debug(f"Table too sparse: {actual_cells}/{expected_cells} cells")
            return False
        
        return True
    
    def _quarantine_data(
        self,
        data: Dict[str, Any],
        method: ExtractionMethod,
        reason: str
    ) -> None:
        """Add data to quarantine for later review."""
        from datetime import datetime
        
        quarantine_entry = {
            'original_data': data,
            'method': method.value,
            'failure_reason': reason,
            'page': data.get('provenance', {}).get('page', 1),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        self.quarantine_entries.append(quarantine_entry)
        logger.debug(f"Data quarantined: {reason}")
    
    def get_quarantine_entries(self) -> List[Dict[str, Any]]:
        """Get all quarantine entries."""
        return self.quarantine_entries.copy()
    
    def clear_quarantine(self) -> None:
        """Clear quarantine entries."""
        self.quarantine_entries.clear()
