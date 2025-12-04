#!/usr/bin/env python
"""
Test script to verify that new video uploads will have metadata extracted correctly.
This script simulates the video processing flow to ensure metadata extraction works.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.video.services import VideoProcessor
from file_processor.video.models import VideoFile
import logging

logger = logging.getLogger(__name__)

def test_metadata_extraction():
    """Test metadata extraction for existing video files"""
    processor = VideoProcessor()
    
    # Test with a few existing video files
    test_videos = VideoFile.objects.all()[:3]  # Test first 3 videos
    
    for video_file in test_videos:
        print(f"\nTesting metadata extraction for: {video_file.original_filename}")
        
        try:
            # Simulate processing (this should extract metadata if missing)
            success = processor.process_uploaded_video(video_file)
            
            # Refresh the object from database
            video_file.refresh_from_db()
            
            print(f"  Processing successful: {success}")
            print(f"  Duration: {video_file.duration} seconds")
            print(f"  Resolution: {video_file.resolution}")
            print(f"  File Size: {video_file.file_size} bytes")
            print(f"  Conversion Status: {video_file.conversion_status}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\nMetadata extraction test completed!")

if __name__ == "__main__":
    test_metadata_extraction()