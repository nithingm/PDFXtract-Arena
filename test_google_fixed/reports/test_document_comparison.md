# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-27 22:35:38

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 1
- **Best Overall:** google-ocr
- **Best for Tables:** google-ocr
- **Best for Text:** google-ocr

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. google-ocr**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🔴 google-ocr | 0.496 | 0 | 43 | 0.982 | 2.165 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### google-ocr

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: 0.981640660485556

**Text Metrics:**
- Text Block Count: 43
- Total Characters: 721
- Readable Text Rate: 0.488

