"""
Quality scoring and metrics for PDFX-Bench.
Calculate quality metrics and heuristics for extracted data.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from .schema import Document, Table, TableCell, ExtractionResult, ExtractionMethod
from .utils.timers import time_operation

logger = logging.getLogger(__name__)


class QualityScorer:
    """Calculate quality metrics for extraction results."""
    
    def __init__(self):
        self.currency_pattern = re.compile(r'[\$€£¥]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?')
        self.date_patterns = [
            re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'),
            re.compile(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'),
            re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}\b', re.IGNORECASE)
        ]
    
    def score_extraction_result(self, result: ExtractionResult) -> Dict[str, Any]:
        """
        Calculate comprehensive quality scores for an extraction result.
        
        Args:
            result: ExtractionResult to score
            
        Returns:
            Dictionary of quality metrics
        """
        with time_operation("score_extraction_result"):
            document = result.document
            
            # Basic metrics
            basic_metrics = self._calculate_basic_metrics(result)
            
            # Table-specific metrics
            table_metrics = self._calculate_table_metrics(document.tables)
            
            # Text quality metrics
            text_metrics = self._calculate_text_metrics(document.text_blocks)
            
            # Cross-validation metrics
            cross_validation = self._calculate_cross_validation_metrics(document)
            
            # Confidence metrics
            confidence_metrics = self._calculate_confidence_metrics(result)
            
            # Overall quality score
            overall_score = self._calculate_overall_score(
                basic_metrics, table_metrics, text_metrics, 
                cross_validation, confidence_metrics
            )
            
            return {
                'method': result.method.value,
                'overall_score': overall_score,
                'basic_metrics': basic_metrics,
                'table_metrics': table_metrics,
                'text_metrics': text_metrics,
                'cross_validation': cross_validation,
                'confidence_metrics': confidence_metrics,
                'processing_time': result.processing_time
            }
    
    def _calculate_basic_metrics(self, result: ExtractionResult) -> Dict[str, Any]:
        """Calculate basic extraction metrics."""
        empty_cell_rate = result.empty_cells / max(result.total_cells, 1) if result.total_cells > 0 else 0
        return {
            'success': result.success,
            'total_text_blocks': result.total_text_blocks,
            'total_tables': result.total_tables,
            'total_cells': result.total_cells,
            'empty_cells': result.empty_cells,
            'empty_cell_rate': empty_cell_rate,
            'avg_confidence': result.avg_confidence
        }
    
    def _calculate_table_metrics(self, tables: List[Table]) -> Dict[str, Any]:
        """Calculate table-specific quality metrics."""
        if not tables:
            return {
                'table_count': 0,
                'avg_rows_per_table': 0,
                'avg_cols_per_table': 0,
                'header_detection_rate': 0,
                'numeric_cell_parse_rate': 0,
                'duplicate_cell_rate': 0,
                'table_completeness_score': 0,
                'empty_cell_rate': 0
            }
        
        total_rows = 0
        total_cols = 0
        header_cells = 0
        total_cells = 0
        numeric_cells = 0
        parsed_numeric_cells = 0
        all_cell_texts = []
        
        for table in tables:
            if table.cells:
                total_rows += table.rows
                total_cols += table.cols
                
                for cell in table.cells:
                    total_cells += 1
                    all_cell_texts.append(cell.raw_text.strip().lower())
                    
                    if cell.is_header:
                        header_cells += 1
                    
                    # Check if cell looks numeric
                    if self._is_numeric_text(cell.raw_text):
                        numeric_cells += 1
                        if cell.parsed_number is not None:
                            parsed_numeric_cells += 1
        
        # Calculate duplicate rate
        unique_texts = set(all_cell_texts)
        duplicate_rate = 1 - (len(unique_texts) / max(len(all_cell_texts), 1))
        
        # Calculate completeness (non-empty cells)
        non_empty_cells = sum(1 for text in all_cell_texts if text)
        completeness_score = non_empty_cells / max(total_cells, 1)
        empty_cell_rate = 1 - completeness_score

        return {
            'table_count': len(tables),
            'avg_rows_per_table': total_rows / len(tables),
            'avg_cols_per_table': total_cols / len(tables),
            'header_detection_rate': header_cells / max(total_cells, 1),
            'numeric_cell_parse_rate': parsed_numeric_cells / max(numeric_cells, 1),
            'duplicate_cell_rate': duplicate_rate,
            'table_completeness_score': completeness_score,
            'empty_cell_rate': empty_cell_rate
        }
    
    def _calculate_text_metrics(self, text_blocks: List[Any]) -> Dict[str, Any]:
        """Calculate text quality metrics."""
        if not text_blocks:
            return {
                'text_block_count': 0,
                'avg_text_length': 0,
                'total_characters': 0,
                'readable_text_rate': 0
            }
        
        total_chars = 0
        readable_blocks = 0
        
        for block in text_blocks:
            text = block.text if hasattr(block, 'text') else str(block)
            total_chars += len(text)
            
            # Check if text is readable (contains letters and reasonable structure)
            if self._is_readable_text(text):
                readable_blocks += 1
        
        return {
            'text_block_count': len(text_blocks),
            'avg_text_length': total_chars / len(text_blocks),
            'total_characters': total_chars,
            'readable_text_rate': readable_blocks / len(text_blocks)
        }
    
    def _calculate_cross_validation_metrics(self, document: Document) -> Dict[str, Any]:
        """Calculate cross-validation and consistency metrics."""
        metrics = {
            'numeric_consistency_score': 0,
            'date_format_consistency': 0,
            'currency_format_consistency': 0,
            'table_sum_validation': False
        }
        
        # Collect all numeric values from tables
        numeric_values = []
        currency_values = []
        date_values = []
        
        for table in document.tables:
            for cell in table.cells:
                text = cell.raw_text.strip()
                
                # Check for numeric values
                if cell.parsed_number is not None:
                    numeric_values.append(cell.parsed_number)
                
                # Check for currency values
                if self.currency_pattern.search(text):
                    currency_values.append(text)
                
                # Check for date values
                for pattern in self.date_patterns:
                    if pattern.search(text):
                        date_values.append(text)
                        break
        
        # Calculate consistency scores
        if numeric_values:
            # Simple consistency check: reasonable value ranges
            reasonable_values = [v for v in numeric_values if 0 <= abs(v) <= 1e9]
            metrics['numeric_consistency_score'] = len(reasonable_values) / len(numeric_values)
        
        if currency_values:
            # Check currency format consistency
            formats = set()
            for value in currency_values:
                if '$' in value:
                    formats.add('USD')
                elif '€' in value:
                    formats.add('EUR')
                elif '£' in value:
                    formats.add('GBP')
            metrics['currency_format_consistency'] = 1.0 if len(formats) <= 1 else 0.5
        
        if date_values:
            # Check date format consistency
            formats = set()
            for value in date_values:
                if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value):
                    formats.add('MDY')
                elif re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', value):
                    formats.add('YMD')
            metrics['date_format_consistency'] = 1.0 if len(formats) <= 1 else 0.5
        
        # Table sum validation (simple check for last row/column totals)
        metrics['table_sum_validation'] = self._validate_table_sums(document.tables)
        
        return metrics
    
    def _calculate_confidence_metrics(self, result: ExtractionResult) -> Dict[str, Any]:
        """Calculate confidence-related metrics."""
        confidences = []
        
        # Collect all confidence scores
        for table in result.document.tables:
            if table.provenance.confidence is not None:
                confidences.append(table.provenance.confidence)
            for cell in table.cells:
                if cell.provenance.confidence is not None:
                    confidences.append(cell.provenance.confidence)
        
        for text_block in result.document.text_blocks:
            if text_block.provenance.confidence is not None:
                confidences.append(text_block.provenance.confidence)
        
        for kv in result.document.key_values:
            if kv.provenance.confidence is not None:
                confidences.append(kv.provenance.confidence)
        
        if not confidences:
            return {
                'has_confidence_scores': False,
                'avg_confidence': None,
                'min_confidence': None,
                'max_confidence': None,
                'low_confidence_rate': 0
            }
        
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        low_conf_count = sum(1 for c in confidences if c < 0.8)
        
        return {
            'has_confidence_scores': True,
            'avg_confidence': avg_conf,
            'min_confidence': min_conf,
            'max_confidence': max_conf,
            'low_confidence_rate': low_conf_count / len(confidences)
        }
    
    def _calculate_overall_score(
        self,
        basic: Dict[str, Any],
        table: Dict[str, Any],
        text: Dict[str, Any],
        cross_val: Dict[str, Any],
        confidence: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score (0-1)."""
        score = 0.0
        weight_sum = 0.0
        
        # Basic success weight
        if basic['success']:
            score += 0.3
        weight_sum += 0.3
        
        # Table quality weight
        if table['table_count'] > 0:
            table_score = (
                (1 - table['empty_cell_rate']) * 0.3 +
                table['numeric_cell_parse_rate'] * 0.2 +
                table['table_completeness_score'] * 0.3 +
                (1 - table['duplicate_cell_rate']) * 0.2
            )
            score += table_score * 0.4
        weight_sum += 0.4
        
        # Text quality weight
        if text['text_block_count'] > 0:
            text_score = text['readable_text_rate']
            score += text_score * 0.2
        weight_sum += 0.2
        
        # Confidence weight
        if confidence['has_confidence_scores']:
            conf_score = confidence['avg_confidence'] or 0.5
            score += conf_score * 0.1
        weight_sum += 0.1
        
        return score / weight_sum if weight_sum > 0 else 0.0
    
    def _is_numeric_text(self, text: str) -> bool:
        """Check if text represents a numeric value."""
        if not text.strip():
            return False
        
        # Remove common non-numeric characters
        cleaned = re.sub(r'[\$€£¥,\s%]', '', text.strip())
        
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _is_readable_text(self, text: str) -> bool:
        """Check if text appears to be readable content."""
        if not text or len(text.strip()) < 3:
            return False
        
        # Check for reasonable character distribution
        letters = sum(1 for c in text if c.isalpha())
        total_chars = len(text)
        
        # At least 50% letters for readable text
        return letters / total_chars >= 0.5
    
    def _validate_table_sums(self, tables: List[Table]) -> bool:
        """Validate table sums (simple heuristic)."""
        for table in tables:
            if table.rows < 3 or table.cols < 3:
                continue  # Too small for sum validation
            
            # Look for potential sum rows/columns
            numeric_cells = defaultdict(list)
            
            for cell in table.cells:
                if cell.parsed_number is not None:
                    numeric_cells[(cell.row_idx, cell.col_idx)] = cell.parsed_number
            
            # Check last row for potential sums
            last_row = table.rows - 1
            for col in range(table.cols):
                if (last_row, col) in numeric_cells:
                    # Sum values in this column (excluding last row)
                    column_sum = sum(
                        numeric_cells.get((row, col), 0)
                        for row in range(last_row)
                    )
                    last_value = numeric_cells[(last_row, col)]
                    
                    # Check if last value is approximately the sum
                    if abs(column_sum - last_value) / max(abs(last_value), 1) < 0.1:
                        return True
        
        return False


def compare_extraction_results(results: List[ExtractionResult]) -> Dict[str, Any]:
    """
    Compare multiple extraction results and identify the best performers.
    
    Args:
        results: List of ExtractionResult objects to compare
        
    Returns:
        Comparison metrics and rankings
    """
    if not results:
        return {}
    
    scorer = QualityScorer()
    scored_results = []
    
    # Score each result
    for result in results:
        score_data = scorer.score_extraction_result(result)
        scored_results.append({
            'method': result.method,
            'scores': score_data,
            'result': result
        })
    
    # Sort by overall score
    scored_results.sort(key=lambda x: x['scores']['overall_score'], reverse=True)
    
    # Find best performers by category
    best_overall = scored_results[0]['method'] if scored_results else None
    
    best_tables = max(
        scored_results,
        key=lambda x: x['scores']['table_metrics']['table_count']
    )['method'] if scored_results else None
    
    best_text = max(
        scored_results,
        key=lambda x: x['scores']['text_metrics']['text_block_count']
    )['method'] if scored_results else None
    
    return {
        'total_methods': len(results),
        'best_overall': best_overall,
        'best_tables': best_tables,
        'best_text': best_text,
        'method_rankings': [sr['method'] for sr in scored_results],
        'detailed_scores': {sr['method'].value: sr['scores'] for sr in scored_results}
    }
