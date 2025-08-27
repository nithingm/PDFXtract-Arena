"""
Export utilities for PDFX-Bench.
Save results in JSONL/CSV/Parquet formats and generate HTML/Markdown reports.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from .schema import ExtractionResult, ExtractionMethod
from .utils.io import save_json, save_jsonl, save_csv, ensure_dir

logger = logging.getLogger(__name__)


class ResultExporter:
    """Export extraction results in various formats."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize exporter.
        
        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)
        
        # Create subdirectories
        self.results_dir = self.output_dir / "results"
        self.reports_dir = self.output_dir / "reports"
        self.quarantine_dir = self.output_dir / "quarantine"
        
        ensure_dir(self.results_dir)
        ensure_dir(self.reports_dir)
        ensure_dir(self.quarantine_dir)
    
    def export_extraction_result(
        self,
        result: ExtractionResult,
        document_id: str
    ) -> Dict[str, Path]:
        """
        Export a single extraction result in multiple formats.
        
        Args:
            result: ExtractionResult to export
            document_id: Document identifier for file naming
            
        Returns:
            Dictionary of format -> file path
        """
        method_name = result.method.value
        base_name = f"{document_id}_{method_name}"
        
        exported_files = {}
        
        # Create method-specific directory
        method_dir = self.results_dir / method_name
        ensure_dir(method_dir)
        
        # Export as JSON
        json_path = method_dir / f"{base_name}.json"
        save_json(result.dict(), json_path)
        exported_files['json'] = json_path
        
        # Export tables as CSV
        if result.document.tables:
            csv_data = self._tables_to_csv_data(result.document.tables)
            csv_path = method_dir / f"{base_name}_tables.csv"
            save_csv(csv_data, csv_path)
            exported_files['tables_csv'] = csv_path
        
        # Export text blocks as JSONL
        if result.document.text_blocks:
            text_data = [
                {
                    'text': block.text,
                    'page': block.provenance.page,
                    'bbox': block.provenance.bbox.dict() if block.provenance.bbox else None,
                    'confidence': block.provenance.confidence
                }
                for block in result.document.text_blocks
            ]
            jsonl_path = method_dir / f"{base_name}_text.jsonl"
            save_jsonl(text_data, jsonl_path)
            exported_files['text_jsonl'] = jsonl_path
        
        # Export key-value pairs
        if result.document.key_values:
            kv_data = [
                {
                    'key': kv.key,
                    'value': kv.value,
                    'page': kv.provenance.page,
                    'bbox': kv.provenance.bbox.dict() if kv.provenance.bbox else None,
                    'confidence': kv.provenance.confidence
                }
                for kv in result.document.key_values
            ]
            kv_path = method_dir / f"{base_name}_keyvalues.jsonl"
            save_jsonl(kv_data, kv_path)
            exported_files['keyvalues_jsonl'] = kv_path
        
        logger.debug(f"Exported {method_name} results to {len(exported_files)} files")
        return exported_files
    
    def export_comparison_report(
        self,
        comparison: Dict[str, Any],
        document_id: str,
        format: str = 'md'
    ) -> Path:
        """
        Export comparison report.
        
        Args:
            comparison: Comparison results
            document_id: Document identifier
            format: Report format ('md' or 'html')
            
        Returns:
            Path to generated report
        """
        if format == 'md':
            return self._export_markdown_report(comparison, document_id)
        elif format == 'html':
            return self._export_html_report(comparison, document_id)
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    def export_quarantine_data(
        self,
        quarantine_entries: List[Dict[str, Any]],
        document_id: str
    ) -> Path:
        """
        Export quarantined data.
        
        Args:
            quarantine_entries: List of quarantine entries
            document_id: Document identifier
            
        Returns:
            Path to quarantine file
        """
        quarantine_path = self.quarantine_dir / f"{document_id}_quarantine.jsonl"
        save_jsonl(quarantine_entries, quarantine_path)
        
        logger.info(f"Exported {len(quarantine_entries)} quarantine entries to {quarantine_path}")
        return quarantine_path
    
    def _tables_to_csv_data(self, tables: List[Any]) -> List[Dict[str, Any]]:
        """Convert tables to CSV-friendly data."""
        csv_data = []
        
        for table in tables:
            for cell in table.cells:
                csv_data.append({
                    'table_id': table.table_id,
                    'row': cell.row_idx,
                    'col': cell.col_idx,
                    'text': cell.raw_text,
                    'is_header': cell.is_header,
                    'parsed_number': cell.parsed_number,
                    'parsed_date': cell.parsed_date,
                    'page': cell.provenance.page,
                    'confidence': cell.provenance.confidence,
                    'bbox_x0': cell.provenance.bbox.x0 if cell.provenance.bbox else None,
                    'bbox_y0': cell.provenance.bbox.y0 if cell.provenance.bbox else None,
                    'bbox_x1': cell.provenance.bbox.x1 if cell.provenance.bbox else None,
                    'bbox_y1': cell.provenance.bbox.y1 if cell.provenance.bbox else None
                })
        
        return csv_data
    
    def _export_markdown_report(
        self,
        comparison: Dict[str, Any],
        document_id: str
    ) -> Path:
        """Export comparison report as Markdown."""
        report_path = self.reports_dir / f"{document_id}_comparison.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 📊 PDFX-Bench Extraction Comparison Report\n\n")
            f.write(f"**📄 Document:** `{document_id}.pdf`\n")
            f.write(f"**🕒 Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Executive Summary
            f.write("## 🎯 Executive Summary\n\n")
            f.write("This report compares multiple PDF extraction methods using deterministic, ")
            f.write("no-hallucination algorithms. Each method is scored on accuracy, completeness, ")
            f.write("and data quality.\n\n")

            f.write(f"- **📈 Methods Tested:** {comparison.get('total_methods', 0)}\n")
            best_overall = comparison.get('best_overall', 'N/A')
            if hasattr(best_overall, 'value'):
                best_overall = best_overall.value
            f.write(f"- **🏆 Best Overall:** {best_overall}\n")

            best_tables = comparison.get('best_tables', 'N/A')
            if hasattr(best_tables, 'value'):
                best_tables = best_tables.value
            f.write(f"- **📋 Best for Tables:** {best_tables}\n")

            best_text = comparison.get('best_text', 'N/A')
            if hasattr(best_text, 'value'):
                best_text = best_text.value
            f.write(f"- **📝 Best for Text:** {best_text}\n\n")
            
            # Method Rankings
            f.write("## 🏅 Method Rankings\n\n")
            f.write("Methods ranked by overall extraction quality:\n\n")
            rankings = comparison.get('method_rankings', [])
            for i, method in enumerate(rankings, 1):
                method_name = method.value if hasattr(method, 'value') else method
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                f.write(f"{emoji} **{i}. {method_name}**\n")
            f.write("\n")

            # Detailed Scores
            f.write("## 📈 Performance Metrics\n\n")
            detailed_scores = comparison.get('detailed_scores', {})

            if detailed_scores:
                # Create table header
                f.write("| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |\n")
                f.write("|--------|---------------|--------------|-------------|------------|------------|\n")

                for method, scores in detailed_scores.items():
                    overall = scores.get('overall_score', 0)
                    tables = scores.get('basic_metrics', {}).get('total_tables', 0)
                    text_blocks = scores.get('basic_metrics', {}).get('total_text_blocks', 0)
                    confidence = scores.get('basic_metrics', {}).get('avg_confidence')
                    proc_time = scores.get('processing_time', 0)

                    # Format confidence
                    if confidence is None:
                        conf_str = "N/A*"
                    else:
                        conf_str = f"{confidence:.3f}"

                    # Add quality indicator
                    quality_emoji = "🟢" if overall >= 0.8 else "🟡" if overall >= 0.6 else "🔴"

                    f.write(f"| {quality_emoji} {method} | {overall:.3f} | {tables} | {text_blocks} | {conf_str} | {proc_time:.3f} |\n")
            
            f.write("\n")
            f.write("**Notes:**\n")
            f.write("- *Quality Score: 0-1 scale (higher is better)\n")
            f.write("- *N/A: Local extractors don't provide confidence scores (cloud APIs do)\n")
            f.write("- *Time: Processing time in seconds\n\n")

            # Quality Metrics
            f.write("## 🔍 Detailed Quality Analysis\n\n")
            for method, scores in detailed_scores.items():
                f.write(f"### {method}\n\n")
                
                basic = scores.get('basic_metrics', {})
                table_metrics = scores.get('table_metrics', {})
                text_metrics = scores.get('text_metrics', {})
                
                f.write("**Basic Metrics:**\n")
                f.write(f"- Success: {basic.get('success', False)}\n")
                f.write(f"- Empty Cell Rate: {basic.get('empty_cell_rate', 0):.3f}\n")
                f.write(f"- Average Confidence: {basic.get('avg_confidence', 'N/A')}\n\n")
                
                if table_metrics.get('table_count', 0) > 0:
                    f.write("**Table Metrics:**\n")
                    f.write(f"- Table Count: {table_metrics.get('table_count', 0)}\n")
                    f.write(f"- Avg Rows per Table: {table_metrics.get('avg_rows_per_table', 0):.1f}\n")
                    f.write(f"- Avg Cols per Table: {table_metrics.get('avg_cols_per_table', 0):.1f}\n")
                    f.write(f"- Numeric Parse Rate: {table_metrics.get('numeric_cell_parse_rate', 0):.3f}\n")
                    f.write(f"- Completeness Score: {table_metrics.get('table_completeness_score', 0):.3f}\n\n")
                
                if text_metrics.get('text_block_count', 0) > 0:
                    f.write("**Text Metrics:**\n")
                    f.write(f"- Text Block Count: {text_metrics.get('text_block_count', 0)}\n")
                    f.write(f"- Total Characters: {text_metrics.get('total_characters', 0)}\n")
                    f.write(f"- Readable Text Rate: {text_metrics.get('readable_text_rate', 0):.3f}\n\n")
        
        logger.info(f"Markdown report exported to {report_path}")
        return report_path
    
    def _export_html_report(
        self,
        comparison: Dict[str, Any],
        document_id: str
    ) -> Path:
        """Export comparison report as HTML."""
        report_path = self.reports_dir / f"{document_id}_comparison.html"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PDFX-Bench Comparison Report - {document_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ margin: 10px 0; }}
        .score {{ font-weight: bold; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
    </style>
</head>
<body>
    <h1>PDFX-Bench Comparison Report</h1>
    <p><strong>Document:</strong> {document_id}</p>
    <p><strong>Generated:</strong> {datetime.now().isoformat()}</p>
    
    <h2>Summary</h2>
    <ul>
        <li><strong>Total Methods:</strong> {comparison.get('total_methods', 0)}</li>
        <li><strong>Best Overall:</strong> {comparison.get('best_overall', 'N/A')}</li>
        <li><strong>Best for Tables:</strong> {comparison.get('best_tables', 'N/A')}</li>
        <li><strong>Best for Text:</strong> {comparison.get('best_text', 'N/A')}</li>
    </ul>
    
    <h2>Method Rankings</h2>
    <ol>
"""
        
        rankings = comparison.get('method_rankings', [])
        for method in rankings:
            method_name = method.value if hasattr(method, 'value') else method
            html_content += f"        <li>{method_name}</li>\n"
        
        html_content += """    </ol>
    
    <h2>Detailed Scores</h2>
    <table>
        <tr>
            <th>Method</th>
            <th>Overall Score</th>
            <th>Tables</th>
            <th>Text Blocks</th>
            <th>Avg Confidence</th>
            <th>Processing Time</th>
        </tr>
"""
        
        detailed_scores = comparison.get('detailed_scores', {})
        for method, scores in detailed_scores.items():
            overall = scores.get('overall_score', 0)
            tables = scores.get('basic_metrics', {}).get('total_tables', 0)
            text_blocks = scores.get('basic_metrics', {}).get('total_text_blocks', 0)
            confidence = scores.get('basic_metrics', {}).get('avg_confidence', 'N/A')
            proc_time = scores.get('processing_time', 0)
            
            conf_str = f"{confidence:.3f}" if isinstance(confidence, (int, float)) else str(confidence)
            
            html_content += f"""        <tr>
            <td>{method}</td>
            <td class="score">{overall:.3f}</td>
            <td>{tables}</td>
            <td>{text_blocks}</td>
            <td>{conf_str}</td>
            <td>{proc_time:.2f}s</td>
        </tr>
"""
        
        html_content += """    </table>
</body>
</html>"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report exported to {report_path}")
        return report_path
