"""
Timing utilities for PDFX-Bench.
"""

import time
import functools
from typing import Callable, Any, Dict
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Timer:
    """Simple timer class for measuring execution time."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.perf_counter()
        self.end_time = None
    
    def stop(self) -> float:
        """Stop the timer and return elapsed time."""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        
        self.end_time = time.perf_counter()
        return self.elapsed
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        
        end_time = self.end_time or time.perf_counter()
        return end_time - self.start_time
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


@contextmanager
def time_operation(operation_name: str, log_result: bool = True):
    """
    Context manager for timing operations.
    
    Args:
        operation_name: Name of the operation being timed
        log_result: Whether to log the timing result
        
    Yields:
        Timer instance
    """
    timer = Timer()
    timer.start()
    
    try:
        yield timer
    finally:
        elapsed = timer.stop()
        if log_result:
            logger.debug(f"{operation_name} completed in {elapsed:.3f} seconds")


def timed(func: Callable) -> Callable:
    """
    Decorator to time function execution.
    
    Args:
        func: Function to time
        
    Returns:
        Wrapped function that logs execution time
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} executed in {elapsed:.3f} seconds")
    
    return wrapper


class PerformanceTracker:
    """Track performance metrics across multiple operations."""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    def record(self, operation: str, duration: float) -> None:
        """Record a timing measurement."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation not in self.metrics:
            return {}
        
        durations = self.metrics[operation]
        return {
            'count': len(durations),
            'total': sum(durations),
            'average': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations."""
        return {op: self.get_stats(op) for op in self.metrics.keys()}
    
    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()


# Global performance tracker instance
performance_tracker = PerformanceTracker()


@contextmanager
def track_performance(operation_name: str):
    """
    Context manager that tracks performance metrics.
    
    Args:
        operation_name: Name of the operation to track
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        performance_tracker.record(operation_name, elapsed)
