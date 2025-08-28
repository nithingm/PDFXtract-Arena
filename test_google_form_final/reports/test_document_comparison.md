# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-27 22:50:07

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 1
- **Best Overall:** google-form
- **Best for Tables:** google-form
- **Best for Text:** google-form

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. google-form**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🟢 google-form | 0.893 | 1 | 40 | 0.973 | 3.256 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### google-form

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: 0.973003867219706

**Table Metrics:**
- Table Count: 1
- Avg Rows per Table: 1.0
- Avg Cols per Table: 1.0
- Numeric Parse Rate: 1.000
- Completeness Score: 1.000

**Text Metrics:**
- Text Block Count: 40
- Total Characters: 725
- Readable Text Rate: 0.500

