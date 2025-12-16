"""
Detection API module for camera-based multi-type detection

This module serves as the main entry point for detection API functionality.
The actual implementations are in detection_api.py to avoid code duplication.
"""

# Import the actual API implementations
from .detection_api import (
    DetectionAPIView,
)

__all__ = [
    'DetectionAPIView',
]