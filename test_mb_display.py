#!/usr/bin/env python
"""
Test script to verify that total size is correctly displayed in MB
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.video.models import VideoFile
from django.contrib.auth.models import User

def test_mb_calculation():
    """Test MB calculation for total size display"""
    print("Testing MB calculation for video statistics...")
    
    # Get all videos
    videos = VideoFile.objects.all()
    
    if not videos:
        print("No videos found in database")
        return
    
    # Calculate total size in bytes
    total_size_bytes = sum(video.file_size or 0 for video in videos)
    
    # Convert to MB and round to 2 decimal places
    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
    
    print(f"Total videos: {videos.count()}")
    print(f"Total size in bytes: {total_size_bytes:,}")
    print(f"Total size in MB: {total_size_mb}")
    
    # Show individual video sizes
    print("\nIndividual video sizes:")
    for video in videos[:5]:  # Show first 5 videos
        size_mb = round((video.file_size or 0) / (1024 * 1024), 2)
        print(f"  {video.original_filename}: {size_mb} MB")
    
    if videos.count() > 5:
        print(f"  ... and {videos.count() - 5} more videos")
    
    print(f"\n✅ Total size will be displayed as: {total_size_mb} MB")

if __name__ == "__main__":
    test_mb_calculation()