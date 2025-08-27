# 📊 PDFX-Bench Extraction Comparison Report

**📄 Document:** `test_document.pdf`
**🕒 Generated:** 2025-08-27 12:36:44

## 🎯 Executive Summary

This report compares multiple PDF extraction methods using deterministic, no-hallucination algorithms. Each method is scored on accuracy, completeness, and data quality.

- **📈 Methods Tested:** 1
- **🏆 Best Overall:** tesseract
- **📋 Best for Tables:** tesseract
- **📝 Best for Text:** tesseract

## 🏅 Method Rankings

Methods ranked by overall extraction quality:

🥇 **1. tesseract**

## 📈 Performance Metrics

| Method | Quality Score | Tables Found | Text Blocks | Confidence | Time (sec) |
|--------|---------------|--------------|-------------|------------|------------|
| 🔴 tesseract | 0.593 | 0 | 1 | 0.934 | 1.362 |

**Notes:**
- *Quality Score: 0-1 scale (higher is better)
- *N/A: Local extractors don't provide confidence scores (cloud APIs do)
- *Time: Processing time in seconds

## 🔍 Detailed Quality Analysis

### tesseract

**Basic Metrics:**
- Success: True
- Empty Cell Rate: 0.000
- Average Confidence: 0.9342857142857143

**Text Metrics:**
- Text Block Count: 1
- Total Characters: 765
- Readable Text Rate: 1.000

