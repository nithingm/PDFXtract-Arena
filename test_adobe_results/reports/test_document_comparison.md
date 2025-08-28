# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-28 02:14:01

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 1
- **Best Overall:** adobe
- **Best for Tables:** adobe
- **Best for Text:** adobe

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. adobe**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🔴 adobe | 0.384 | 0 | 38 | N/A* | 8.509 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### adobe

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: None

**Text Metrics:**
- Text Block Count: 38
- Total Characters: 610
- Readable Text Rate: 0.421

