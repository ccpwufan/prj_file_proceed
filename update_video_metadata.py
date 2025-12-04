#!/usr/bin/env python
"""
Script to update metadata for existing video files that don't have duration, resolution, or file_size.
Run this script to populate missing metadata for existing VideoFile records.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.video.models import VideoFile
from file_processor.video.services import VideoConverter
from django.db import models
import logging

logger = logging.getLogger(__name__)

def update_missing_metadata():
    """Update metadata for video files that are missing duration, resolution, or file_size"""
    converter = VideoConverter()
    
    # Find videos with missing metadata
    videos_to_update = VideoFile.objects.filter(
        models.Q(duration__isnull=True) | 
        models.Q(resolution__isnull=True) | 
        models.Q(resolution='') |
        models.Q(file_size__isnull=True)
    )
    
    total_count = videos_to_update.count()
    logger.info(f"Found {total_count} video files with missing metadata")
    
    updated_count = 0
    failed_count = 0
    
    for video_file in videos_to_update:
        try:
            # Determine which file to analyze
            file_to_analyze = None
            
            # Priority: converted file > original file > video_file
            if video_file.converted_file and video_file.conversion_status == 'completed':
                file_to_analyze = video_file.converted_file.path
                logger.info(f"Analyzing converted file for {video_file.original_filename}")
            elif video_file.original_file and os.path.exists(video_file.original_file.path):
                file_to_analyze = video_file.original_file.path
                logger.info(f"Analyzing original file for {video_file.original_filename}")
            elif video_file.video_file and os.path.exists(video_file.video_file.path):
                file_to_analyze = video_file.video_file.path
                logger.info(f"Analyzing video file for {video_file.original_filename}")
            
            if not file_to_analyze or not os.path.exists(file_to_analyze):
                logger.warning(f"No valid file found for video {video_file.id}: {video_file.original_filename}")
                failed_count += 1
                continue
            
            # Get video info and extract metadata
            video_info = converter.get_video_info(file_to_analyze)
            metadata = converter.extract_video_metadata(video_info)
            
            # Update video file with metadata
            video_file.duration = metadata['duration']
            video_file.resolution = metadata['resolution']
            video_file.file_size = metadata['file_size']
            
            video_file.save(update_fields=['duration', 'resolution', 'file_size'])
            
            logger.info(f"Updated metadata for {video_file.original_filename}: "
                       f"Duration={metadata['duration']}s, "
                       f"Resolution={metadata['resolution']}, "
                       f"Size={metadata['file_size']} bytes")
            
            updated_count += 1
            
        except Exception as e:
            logger.error(f"Failed to update metadata for video {video_file.id}: {e}")
            failed_count += 1
    
    logger.info(f"Metadata update completed: {updated_count} updated, {failed_count} failed")
    return updated_count, failed_count

if __name__ == "__main__":
    print("Starting metadata update for existing video files...")
    updated, failed = update_missing_metadata()
    print(f"Update completed: {updated} files updated, {failed} files failed")