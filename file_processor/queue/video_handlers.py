"""
Video Processing Task Handlers

This module contains task handlers specifically for video-related operations
including video conversion, thumbnail generation, and video analysis.
"""

import os
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from file_processor.video.models import VideoFile, VideoAnalysis
from file_processor.video.services import VideoProcessor, generate_thumbnail
from .handlers import BaseTaskHandler
from .registry import register_task_handler

logger = logging.getLogger(__name__)


@register_task_handler(
    'video_conversion',
    description='Convert video files to web-compatible format',
    default_timeout=600,  # 10 minutes
    default_priority=5,
    max_concurrent=1,
    default_max_retries=3
)
class VideoConversionHandler(BaseTaskHandler):
    """
    Handler for video conversion tasks.
    
    This handler processes uploaded video files, converting them to
    web-compatible formats and generating thumbnails.
    """
    
    def execute(self, task_params):
        """
        Execute video conversion.
        
        Args:
            task_params (dict): Should contain 'video_file_id'
            
        Returns:
            dict: Conversion results
        """
        video_file_id = task_params.get('video_file_id')
        if not video_file_id:
            raise ValueError("Missing required parameter: video_file_id")
        
        # Get video file with transaction
        with transaction.atomic():
            video_file = VideoFile.objects.select_for_update().get(id=video_file_id)
            
            # Update status to converting
            video_file.status = 'converting'
            video_file.save(update_fields=['status'])
        
        self.log(f"Starting conversion for video file {video_file_id}: {video_file.original_filename}")
        
        try:
            # Create video processor with progress callback
            processor = VideoProcessor()
            
            # Process video with progress tracking
            success = processor.process_uploaded_video(
                video_file, 
                progress_callback=self._progress_callback
            )
            
            if success:
                # Re-fetch video_file to get the latest state (including converted video_file)
                with transaction.atomic():
                    video_file = VideoFile.objects.get(id=video_file_id)
                
                # Generate thumbnail
                thumbnail_result = self._generate_thumbnail(video_file)
                
                # Update final status
                with transaction.atomic():
                    video_file = VideoFile.objects.get(id=video_file_id)
                    video_file.status = 'processed'
                    if thumbnail_result:
                        video_file.thumbnail = thumbnail_result
                    video_file.save(update_fields=['status', 'thumbnail'])
                
                return {
                    'success': True,
                    'message': 'Video conversion completed successfully',
                    'video_file_id': video_file_id,
                    'thumbnail_generated': thumbnail_result is not None,
                    'final_status': 'processed'
                }
            else:
                # Mark as failed
                with transaction.atomic():
                    video_file = VideoFile.objects.get(id=video_file_id)
                    video_file.status = 'failed'
                    video_file.save(update_fields=['status'])
                
                raise Exception('Video processing failed')
                
        except Exception as e:
            # Mark video as failed
            with transaction.atomic():
                video_file = VideoFile.objects.get(id=video_file_id)
                video_file.status = 'failed'
                video_file.save(update_fields=['status'])
            
            raise
    
    def _progress_callback(self, progress):
        """
        Progress callback for video processing.
        
        Args:
            progress (float): Progress percentage (0-100)
        """
        # Only log progress at significant milestones to reduce spam
        if progress % 10 == 0 or progress == 100:
            self.update_progress(progress, f"Video conversion progress: {progress:.1f}%")
    
    def _generate_thumbnail(self, video_file):
        """
        Generate thumbnail for processed video.
        
        Args:
            video_file (VideoFile): Video file instance
            
        Returns:
            ContentFile or None: Thumbnail file content
        """
        try:
            # Determine which video file to use for thumbnail generation
            # Priority: converted_file > video_file > original_file
            video_source = None
            video_path = None
            
            if video_file.converted_file and video_file.conversion_status == 'completed':
                video_source = "converted"
                video_path = video_file.converted_file.path
                self.log(f"Using converted file for thumbnail: {video_path}")
            elif video_file.video_file:
                video_source = "original"
                video_path = video_file.video_file.path
                self.log(f"Using video file for thumbnail: {video_path}")
            elif video_file.original_file:
                video_source = "backup"
                video_path = video_file.original_file.path
                self.log(f"Using original file backup for thumbnail: {video_path}")
            
            if not video_path:
                self.log("No video file available for thumbnail generation")
                return None
            
            if not os.path.exists(video_path):
                self.log(f"Video file does not exist: {video_path}")
                return None
            
            thumbnail_path = generate_thumbnail(video_path)
            self.log(f"generate_thumbnail returned: {thumbnail_path}")
            
            # Convert relative path to absolute path for existence check
            full_thumbnail_path = os.path.join(settings.MEDIA_ROOT, thumbnail_path) if thumbnail_path else None
            self.log(f"Full thumbnail path: {full_thumbnail_path}")
            
            if thumbnail_path and os.path.exists(full_thumbnail_path):
                file_size = os.path.getsize(full_thumbnail_path)
                self.log(f"Thumbnail file exists, size: {file_size} bytes")
                
                with open(full_thumbnail_path, 'rb') as f:
                    thumbnail_content = ContentFile(f.read(), name=f"thumb_{video_file.id}.jpg")
                
                # Clean up temporary thumbnail file
                try:
                    os.remove(full_thumbnail_path)
                    self.log("Temporary thumbnail file cleaned up")
                except OSError:
                    pass
                
                self.log("Thumbnail generated successfully")
                return thumbnail_content
            else:
                self.log(f"Thumbnail generation returned no result. thumbnail_path: {thumbnail_path}, file_exists: {os.path.exists(full_thumbnail_path) if full_thumbnail_path else False}")
                return None
                
        except Exception as e:
            self.log(f"Thumbnail generation failed: {e}", level='error')
            return None
    
    def should_retry(self, exception):
        """
        Custom retry logic for video conversion.
        
        Args:
            exception (Exception): The exception that occurred
            
        Returns:
            bool: True if should retry
        """
        # Don't retry file not found errors
        if 'FileNotFoundError' in str(type(exception)) or 'does not exist' in str(exception):
            return False
        
        # Don't retry permission errors
        if 'Permission' in str(exception):
            return False
        
        # Use default retry logic for other cases
        return super().should_retry(exception)
    
    def on_task_success(self, result):
        """Called when video conversion succeeds."""
        self.log(f"Video conversion completed successfully: {result}")
    
    def on_task_failure(self, exception):
        """Called when video conversion fails permanently."""
        self.log(f"Video conversion failed permanently: {exception}", level='error')


@register_task_handler(
    'video_analysis',
    description='Analyze video content and extract metadata',
    default_timeout=300,  # 5 minutes
    default_priority=3,
    max_concurrent=1,
    default_max_retries=2
)
class VideoAnalysisHandler(BaseTaskHandler):
    """
    Handler for video analysis tasks.
    
    This handler performs detailed analysis of video content
    including object detection, scene analysis, etc.
    """
    
    def execute(self, task_params):
        """
        Execute video analysis.
        
        Args:
            task_params (dict): Should contain 'video_file_id' and 'analysis_id'
            
        Returns:
            dict: Analysis results
        """
        video_file_id = task_params.get('video_file_id')
        analysis_id = task_params.get('analysis_id')
        
        if not video_file_id or not analysis_id:
            raise ValueError("Missing required parameters: video_file_id and analysis_id")
        
        # Get objects
        try:
            video_file = VideoFile.objects.get(id=video_file_id)
            analysis = VideoAnalysis.objects.get(id=analysis_id)
        except (VideoFile.DoesNotExist, VideoAnalysis.DoesNotExist) as e:
            raise ValueError(f"Video file or analysis not found: {e}")
        
        self.log(f"Starting analysis for video {video_file_id}, analysis {analysis_id}")
        
        try:
            # Simulate video analysis process
            # In real implementation, this would call computer vision libraries
            analysis_results = self._perform_analysis(video_file)
            
            # Save results
            with transaction.atomic():
                analysis.status = 'completed'
                analysis.results = analysis_results
                analysis.save(update_fields=['status', 'results'])
            
            return {
                'success': True,
                'message': 'Video analysis completed',
                'analysis_id': analysis_id,
                'results_summary': analysis_results.get('summary', {})
            }
            
        except Exception as e:
            # Mark analysis as failed
            with transaction.atomic():
                analysis.status = 'failed'
                analysis.error_message = str(e)
                analysis.save(update_fields=['status', 'error_message'])
            
            raise
    
    def _perform_analysis(self, video_file):
        """
        Perform the actual video analysis.
        
        Args:
            video_file (VideoFile): Video file to analyze
            
        Returns:
            dict: Analysis results
        """
        # This is a placeholder implementation
        # In real implementation, you would use OpenCV, MediaPipe, etc.
        
        self.update_progress(10, "Initializing video analysis")
        
        # Simulate processing steps
        steps = [
            (20, "Extracting video frames"),
            (40, "Detecting objects"),
            (60, "Analyzing scenes"),
            (80, "Generating metadata"),
            (100, "Finalizing analysis")
        ]
        
        for progress, message in steps:
            import time
            time.sleep(0.5)  # Simulate processing time
            self.update_progress(progress, message)
        
        return {
            'summary': {
                'total_frames': 1000,
                'objects_detected': ['person', 'car', 'building'],
                'scenes': ['outdoor', 'urban'],
                'duration_seconds': video_file.duration
            },
            'detailed_results': {
                'object_counts': {'person': 15, 'car': 8, 'building': 3},
                'scene_transitions': 5,
                'motion_analysis': {'average_motion': 0.7}
            }
        }


@register_task_handler(
    'batch_video_conversion',
    description='Convert multiple video files in batch',
    default_timeout=1800,  # 30 minutes
    default_priority=2,
    max_concurrent=1,
    default_max_retries=2
)
class BatchVideoConversionHandler(BaseTaskHandler):
    """
    Handler for batch video conversion tasks.
    
    This handler processes multiple video files in sequence
    with progress tracking for the entire batch.
    """
    
    def execute(self, task_params):
        """
        Execute batch video conversion.
        
        Args:
            task_params (dict): Should contain 'video_file_ids' list
            
        Returns:
            dict: Batch conversion results
        """
        video_file_ids = task_params.get('video_file_ids', [])
        
        if not video_file_ids:
            raise ValueError("Missing required parameter: video_file_ids")
        
        if not isinstance(video_file_ids, list):
            raise ValueError("video_file_ids must be a list")
        
        self.log(f"Starting batch conversion for {len(video_file_ids)} videos")
        
        results = []
        failed_conversions = []
        
        for i, video_file_id in enumerate(video_file_ids):
            try:
                self.update_progress(
                    (i / len(video_file_ids)) * 100,
                    f"Processing video {i+1}/{len(video_file_ids)} (ID: {video_file_id})"
                )
                
                # Create subtask for individual conversion
                from .manager import queue_manager
                subtask = queue_manager.add_task(
                    task_name=f"Convert video {video_file_id}",
                    task_type='video_conversion',
                    task_params={'video_file_id': video_file_id},
                    priority=self.task.priority
                )
                
                results.append({
                    'video_file_id': video_file_id,
                    'task_id': subtask.id,
                    'status': 'queued'
                })
                
            except Exception as e:
                self.log(f"Failed to queue conversion for video {video_file_id}: {e}", level='error')
                failed_conversions.append({
                    'video_file_id': video_file_id,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'message': f'Batch conversion initiated for {len(results)} videos',
            'queued_conversions': results,
            'failed_conversions': failed_conversions,
            'total_videos': len(video_file_ids),
            'successful_queues': len(results),
            'failed_queues': len(failed_conversions)
        }