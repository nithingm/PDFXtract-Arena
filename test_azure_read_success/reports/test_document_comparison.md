# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-27 19:29:20

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 1
- **Best Overall:** azure-read
- **Best for Tables:** azure-read
- **Best for Text:** azure-read

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. azure-read**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🔴 azure-read | 0.498 | 0 | 43 | 1.000 | 1.723 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### azure-read

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: 1.0

**Text Metrics:**
- Text Block Count: 43
- Total Characters: 723
- Readable Text Rate: 0.488

