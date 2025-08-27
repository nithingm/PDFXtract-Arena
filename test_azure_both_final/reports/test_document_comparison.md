# PDFX-Bench Extraction Comparison Report

     **Document:** `test_document.pdf`
     **Generated:** 2025-08-27 19:31:31

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **Methods Tested:** 2
- **Best Overall:** azure-layout
- **Best for Tables:** azure-layout
- **Best for Text:** azure-layout

##  Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. azure-layout**
🥈 **2. azure-read**

##  Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🟢 azure-layout | 0.826 | 1 | 43 | 1.000 | 4.805 |
| 🔴 azure-read | 0.498 | 0 | 43 | 1.000 | 2.763 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### azure-layout

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.214
- Average Confidence: 1.0

**Table Metrics:**
- Table Count: 1
- Avg Rows per Table: 7.0
- Avg Cols per Table: 4.0
- Numeric Parse Rate: 1.000
- Completeness Score: 0.786

**Text Metrics:**
- Text Block Count: 43
- Total Characters: 723
- Readable Text Rate: 0.488

### azure-read

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: 1.0

**Text Metrics:**
- Text Block Count: 43
- Total Characters: 723
- Readable Text Rate: 0.488

