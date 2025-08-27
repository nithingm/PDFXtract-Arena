"""
Logging utilities for PDFX-Bench.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = True,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Whether to use JSON formatting
        console_output: Whether to output to console
        
    Returns:
        Configured logger
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def log_extraction_start(
    logger: logging.Logger,
    method: str,
    file_path: str,
    **kwargs
) -> None:
    """Log extraction start."""
    logger.info(
        "Starting extraction",
        extra={
            'event': 'extraction_start',
            'method': method,
            'file_path': file_path,
            **kwargs
        }
    )


def log_extraction_end(
    logger: logging.Logger,
    method: str,
    file_path: str,
    success: bool,
    processing_time: float,
    **kwargs
) -> None:
    """Log extraction completion."""
    logger.info(
        "Extraction completed",
        extra={
            'event': 'extraction_end',
            'method': method,
            'file_path': file_path,
            'success': success,
            'processing_time': processing_time,
            **kwargs
        }
    )


def log_extraction_error(
    logger: logging.Logger,
    method: str,
    file_path: str,
    error: Exception,
    **kwargs
) -> None:
    """Log extraction error."""
    logger.error(
        f"Extraction failed: {str(error)}",
        extra={
            'event': 'extraction_error',
            'method': method,
            'file_path': file_path,
            'error_type': type(error).__name__,
            'error_message': str(error),
            **kwargs
        },
        exc_info=True
    )


def log_quality_metrics(
    logger: logging.Logger,
    method: str,
    file_path: str,
    metrics: Dict[str, Any]
) -> None:
    """Log quality metrics."""
    logger.info(
        "Quality metrics calculated",
        extra={
            'event': 'quality_metrics',
            'method': method,
            'file_path': file_path,
            **metrics
        }
    )


def log_quarantine(
    logger: logging.Logger,
    method: str,
    reason: str,
    data: Dict[str, Any]
) -> None:
    """Log data quarantine."""
    logger.warning(
        f"Data quarantined: {reason}",
        extra={
            'event': 'quarantine',
            'method': method,
            'reason': reason,
            'quarantined_data': data
        }
    )
