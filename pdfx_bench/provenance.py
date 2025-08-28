"""
Provenance tracking utilities for PDFX-Bench.
Attach page/bbox/method/confidence to all extracted data.
"""

import logging
from typing import Dict, Any, Optional, List
from .schema import Provenance, BoundingBox, ExtractionMethod

logger = logging.getLogger(__name__)


def create_provenance(
    method: ExtractionMethod,
    page: int,
    bbox: Optional[BoundingBox] = None,
    confidence: Optional[float] = None,
    raw_data: Optional[Dict[str, Any]] = None
) -> Provenance:
    """
    Create a provenance record for extracted data.
    
    Args:
        method: Extraction method used
        page: Page number (1-based)
        bbox: Bounding box coordinates if available
        confidence: Confidence score if available
        raw_data: Original extractor-specific data
        
    Returns:
        Provenance record
    """
    return Provenance(
        method=method,
        page=page,
        bbox=bbox,
        confidence=confidence,
        raw_data=raw_data
    )


def create_bbox_from_coords(x0: float, y0: float, x1: float, y1: float) -> BoundingBox:
    """
    Create a bounding box from coordinates.
    
    Args:
        x0: Left coordinate
        y0: Top coordinate  
        x1: Right coordinate
        y1: Bottom coordinate
        
    Returns:
        BoundingBox instance
    """
    return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)


def create_bbox_from_dict(bbox_dict: Dict[str, float]) -> Optional[BoundingBox]:
    """
    Create a bounding box from a dictionary.
    
    Args:
        bbox_dict: Dictionary with bbox coordinates
        
    Returns:
        BoundingBox instance or None if invalid
    """
    try:
        # Handle different bbox formats
        if all(key in bbox_dict for key in ['x0', 'y0', 'x1', 'y1']):
            return BoundingBox(
                x0=bbox_dict['x0'],
                y0=bbox_dict['y0'],
                x1=bbox_dict['x1'],
                y1=bbox_dict['y1']
            )
        elif all(key in bbox_dict for key in ['left', 'top', 'right', 'bottom']):
            return BoundingBox(
                x0=bbox_dict['left'],
                y0=bbox_dict['top'],
                x1=bbox_dict['right'],
                y1=bbox_dict['bottom']
            )
        elif all(key in bbox_dict for key in ['x', 'y', 'width', 'height']):
            return BoundingBox(
                x0=bbox_dict['x'],
                y0=bbox_dict['y'],
                x1=bbox_dict['x'] + bbox_dict['width'],
                y1=bbox_dict['y'] + bbox_dict['height']
            )
        else:
            logger.warning(f"Unknown bbox format: {bbox_dict}")
            return None
    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Failed to create bbox from dict {bbox_dict}: {e}")
        return None


def normalize_confidence(confidence: Any, method: ExtractionMethod) -> Optional[float]:
    """
    Normalize confidence scores from different extractors to 0-1 range.
    
    Args:
        confidence: Raw confidence value
        method: Extraction method
        
    Returns:
        Normalized confidence score or None
    """
    if confidence is None:
        return None
    
    try:
        conf_float = float(confidence)
        
        # Different extractors use different confidence ranges
        if method == ExtractionMethod.AWS_TEXTRACT:
            # Textract uses 0-100 range
            if 0 <= conf_float <= 100:
                return conf_float / 100.0
        elif method in [ExtractionMethod.GOOGLE_DOCAI_OCR, ExtractionMethod.GOOGLE_DOCAI_FORM, ExtractionMethod.GOOGLE_DOCAI_LAYOUT]:
            # Document AI uses 0-1 range
            if 0 <= conf_float <= 1:
                return conf_float
        elif method in [ExtractionMethod.AZURE_READ, ExtractionMethod.AZURE_LAYOUT]:
            # Azure uses 0-1 range
            if 0 <= conf_float <= 1:
                return conf_float
        elif method == ExtractionMethod.ADOBE_EXTRACT:
            # Adobe uses 0-1 range
            if 0 <= conf_float <= 1:
                return conf_float
        
        # For other methods or unknown ranges, assume 0-1
        if 0 <= conf_float <= 1:
            return conf_float
        elif 0 <= conf_float <= 100:
            return conf_float / 100.0
        else:
            logger.warning(f"Confidence score {conf_float} out of expected range for {method}")
            return None
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to normalize confidence {confidence}: {e}")
        return None


def filter_by_confidence(
    items: List[Any],
    min_confidence: float,
    confidence_attr: str = 'confidence'
) -> List[Any]:
    """
    Filter items by minimum confidence threshold.
    
    Args:
        items: List of items with confidence scores
        min_confidence: Minimum confidence threshold (0-1)
        confidence_attr: Attribute name for confidence score
        
    Returns:
        Filtered list of items
    """
    filtered_items = []
    
    for item in items:
        try:
            # Get confidence from item
            if hasattr(item, 'provenance') and hasattr(item.provenance, 'confidence'):
                confidence = item.provenance.confidence
            elif hasattr(item, confidence_attr):
                confidence = getattr(item, confidence_attr)
            else:
                # No confidence available, include item
                filtered_items.append(item)
                continue
            
            # Filter by confidence
            if confidence is None or confidence >= min_confidence:
                filtered_items.append(item)
            else:
                logger.debug(f"Filtered item with confidence {confidence} < {min_confidence}")
                
        except Exception as e:
            logger.warning(f"Error checking confidence for item: {e}")
            # Include item if we can't check confidence
            filtered_items.append(item)
    
    return filtered_items


def add_provenance_to_raw_data(
    raw_data: Dict[str, Any],
    method: ExtractionMethod,
    page: int
) -> Dict[str, Any]:
    """
    Add provenance information to raw extractor data.
    
    Args:
        raw_data: Raw data from extractor
        method: Extraction method
        page: Page number
        
    Returns:
        Data with provenance added
    """
    enhanced_data = raw_data.copy()
    enhanced_data['_provenance'] = {
        'method': method.value,
        'page': page,
        'extraction_timestamp': None  # Will be set by caller
    }
    
    return enhanced_data


def extract_bbox_from_raw_data(
    raw_data: Dict[str, Any],
    method: ExtractionMethod
) -> Optional[BoundingBox]:
    """
    Extract bounding box from method-specific raw data.
    
    Args:
        raw_data: Raw data from extractor
        method: Extraction method
        
    Returns:
        BoundingBox if found, None otherwise
    """
    try:
        if method == ExtractionMethod.PDFPLUMBER:
            # pdfplumber uses 'bbox' key
            if 'bbox' in raw_data:
                bbox = raw_data['bbox']
                if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                    return BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3])
        
        elif method == ExtractionMethod.AWS_TEXTRACT:
            # Textract uses 'Geometry' -> 'BoundingBox'
            if 'Geometry' in raw_data and 'BoundingBox' in raw_data['Geometry']:
                bbox = raw_data['Geometry']['BoundingBox']
                return create_bbox_from_dict(bbox)
        
        elif method in [ExtractionMethod.GOOGLE_DOCAI_OCR, ExtractionMethod.GOOGLE_DOCAI_FORM, ExtractionMethod.GOOGLE_DOCAI_LAYOUT]:
            # Document AI uses 'boundingPoly' or 'boundingBox'
            if 'boundingPoly' in raw_data:
                # Convert polygon to bbox
                vertices = raw_data['boundingPoly'].get('vertices', [])
                if vertices:
                    x_coords = [v.get('x', 0) for v in vertices]
                    y_coords = [v.get('y', 0) for v in vertices]
                    return BoundingBox(
                        x0=min(x_coords), y0=min(y_coords),
                        x1=max(x_coords), y1=max(y_coords)
                    )
        
        elif method == ExtractionMethod.AZURE_DOCINTEL:
            # Azure uses 'boundingRegions'
            if 'boundingRegions' in raw_data and raw_data['boundingRegions']:
                region = raw_data['boundingRegions'][0]  # Take first region
                if 'polygon' in region:
                    polygon = region['polygon']
                    x_coords = [p['x'] for p in polygon]
                    y_coords = [p['y'] for p in polygon]
                    return BoundingBox(
                        x0=min(x_coords), y0=min(y_coords),
                        x1=max(x_coords), y1=max(y_coords)
                    )
        
        # Generic bbox extraction
        for bbox_key in ['bbox', 'bounding_box', 'boundingBox', 'geometry']:
            if bbox_key in raw_data:
                return create_bbox_from_dict(raw_data[bbox_key])
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to extract bbox from raw data: {e}")
        return None
