"""
Legacy services module - redirects to new modular services
This file is maintained for backward compatibility
"""

# Import core video services
from .services.video_services import (
    generate_thumbnail,
    VideoConverter,
    VideoProcessor
)

# Import new modular services
from .services.detection_service import DetectionService
from .services.camera_service import CameraService

# Maintain backward compatibility
__all__ = [
    'generate_thumbnail',
    'VideoConverter', 
    'VideoProcessor',
    'DetectionService',
    'CameraService'
]