"""
I/O utilities for PDFX-Bench.
"""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if it doesn't."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_pdf_files(input_path: Union[str, Path]) -> List[Path]:
    """
    Find all PDF files in a path.
    
    Args:
        input_path: File or directory path
        
    Returns:
        List of PDF file paths
    """
    input_path = Path(input_path)
    
    if input_path.is_file():
        if input_path.suffix.lower() == '.pdf':
            return [input_path]
        else:
            raise ValueError(f"File {input_path} is not a PDF")
    
    elif input_path.is_dir():
        pdf_files = []
        for pdf_file in input_path.rglob("*.pdf"):
            pdf_files.append(pdf_file)
        
        if not pdf_files:
            logger.warning(f"No PDF files found in directory {input_path}")
        
        return sorted(pdf_files)
    
    else:
        raise FileNotFoundError(f"Path {input_path} does not exist")


def save_json(data: Any, file_path: Union[str, Path], indent: int = 2) -> None:
    """Save data as JSON file."""
    file_path = Path(file_path)
    ensure_dir(file_path.parent)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    
    logger.debug(f"Saved JSON to {file_path}")


def save_jsonl(data: List[Dict[str, Any]], file_path: Union[str, Path]) -> None:
    """Save data as JSONL (JSON Lines) file."""
    file_path = Path(file_path)
    ensure_dir(file_path.parent)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False, default=str)
            f.write('\n')
    
    logger.debug(f"Saved JSONL to {file_path}")


def save_csv(data: List[Dict[str, Any]], file_path: Union[str, Path]) -> None:
    """Save data as CSV file."""
    if not data:
        logger.warning("No data to save to CSV")
        return
    
    file_path = Path(file_path)
    ensure_dir(file_path.parent)
    
    fieldnames = data[0].keys()
    
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    logger.debug(f"Saved CSV to {file_path}")


def load_json(file_path: Union[str, Path]) -> Any:
    """Load data from JSON file."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file {file_path} not found")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_jsonl(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load data from JSONL file."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"JSONL file {file_path} not found")
    
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    
    return data


def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size in bytes."""
    return Path(file_path).stat().st_size


def get_file_hash(file_path: Union[str, Path]) -> str:
    """Get SHA-256 hash of file."""
    import hashlib
    
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()


def safe_filename(filename: str) -> str:
    """Make filename safe for filesystem."""
    import re
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename or "unnamed"
