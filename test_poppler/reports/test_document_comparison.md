# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-27 13:30:39

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 1
- **Best Overall:** poppler
- **Best for Tables:** poppler
- **Best for Text:** poppler

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. poppler**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🟡 poppler | 0.600 | 0 | 1 | 1.000 | 0.093 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### poppler

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: 1.0

**Text Metrics:**
- Text Block Count: 1
- Total Characters: 776
- Readable Text Rate: 1.000

