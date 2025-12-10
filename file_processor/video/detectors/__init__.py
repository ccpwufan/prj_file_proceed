"""
Detectors module for video object detection
"""

from .barcode_detector import BarcodeDetector
from .manager import MultiTypeDetector

# Future detectors will be added here as they are implemented
# from .phone_detector import PhoneDetector
# from .yellow_box_detector import YellowBoxDetector

__all__ = ['BarcodeDetector', 'MultiTypeDetector']