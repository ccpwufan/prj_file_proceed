"""
Queue System Initialization

This module ensures that all task handlers are properly registered
when the Django application starts.
"""

# Import all task handlers to ensure they are registered
from .video_handlers import (
    VideoConversionHandler,
    VideoAnalysisHandler,
    BatchVideoConversionHandler
)

# Import the manager to make it available
from .manager import queue_manager

# Export for easy access
__all__ = [
    'VideoConversionHandler',
    'VideoAnalysisHandler', 
    'BatchVideoConversionHandler',
    'queue_manager'
]

print("Queue system initialized - task handlers registered")