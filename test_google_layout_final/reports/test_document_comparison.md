# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-27 22:50:20

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 1
- **Best Overall:** google-layout
- **Best for Tables:** google-layout
- **Best for Text:** google-layout

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. google-layout**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🔴 google-layout | 0.300 | 0 | 0 | N/A* | 1.590 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### google-layout

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: None

