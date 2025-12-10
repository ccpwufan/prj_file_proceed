import os
import subprocess
import json
import logging
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from ..models import VideoFile

logger = logging.getLogger(__name__)


def generate_thumbnail(video_path, output_path=None, time_offset=1):
    """Generate thumbnail from video file"""
    try:
        if not output_path:
            # Generate output path based on video path
            video_dir = os.path.dirname(video_path)
            video_name = Path(video_path).stem
            thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'video_thumbnails')
            os.makedirs(thumbnail_dir, exist_ok=True)
            output_path = os.path.join(thumbnail_dir, f"{video_name}_thumbnail.jpg")
        
        # FFmpeg command to generate thumbnail
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', str(time_offset),
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Return path relative to media root
            return output_path.replace(settings.MEDIA_ROOT + '/', '')
        else:
            logger.error(f"Thumbnail generation failed: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None


class VideoConverter:
    """Video conversion service for converting videos to web-compatible formats"""
    
    def __init__(self):
        self.supported_formats = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm']
        self.web_compatible_codecs = {
            'video': ['h264', 'avc', 'mpeg4'],
            'audio': ['aac', 'mp3']
        }
    
    def get_video_info(self, file_path):
        """Get video information using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"Error getting video info: {e}")
        
        return None
    
    def is_web_compatible(self, video_info):
        """Check if video is already web compatible"""
        if not video_info:
            return False
        
        format_name = video_info.get('format', {}).get('format_name', '').lower()
        
        # Check container format
        if 'mp4' not in format_name:
            return False
        
        # Check streams
        streams = video_info.get('streams', [])
        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        
        # Check video codec
        for stream in video_streams:
            codec = stream.get('codec_name', '').lower()
            if codec not in self.web_compatible_codecs['video']:
                return False
        
        # Check audio codec if present
        for stream in audio_streams:
            codec = stream.get('codec_name', '').lower()
            if codec not in self.web_compatible_codecs['audio']:
                return False
        
        return True
    
    def convert_video(self, input_path, output_path, progress_callback=None):
        """Convert video to web-compatible format"""
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', 'libx264',        # H.264 video codec
                '-preset', 'medium',       # Balance between speed and quality
                '-crf', '23',             # Quality (18-28, lower is better)
                '-c:a', 'aac',            # AAC audio codec
                '-b:a', '128k',           # Audio bitrate
                '-movflags', '+faststart', # Optimize for web streaming
                '-y',                     # Overwrite output file
                output_path
            ]
            
            # Run conversion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Monitor progress
            duration = None
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Parse progress from FFmpeg output
                    if 'Duration:' in output and duration is None:
                        try:
                            time_str = output.split('Duration:')[1].split(',')[0].strip()
                            h, m, s = map(float, time_str.split(':'))
                            duration = h * 3600 + m * 60 + s
                        except:
                            pass
                    
                    if 'time=' in output and duration:
                        try:
                            time_str = output.split('time=')[1].split()[0]
                            h, m, s = map(float, time_str.split(':'))
                            current_time = h * 3600 + m * 60 + s
                            progress = min(100, int((current_time / duration) * 100))
                            
                            if progress_callback:
                                progress_callback(progress)
                        except:
                            pass
            
            # Check if conversion was successful
            if process.returncode == 0 and os.path.exists(output_path):
                return True, "Conversion completed successfully"
            else:
                return False, f"Conversion failed with return code: {process.returncode}"
                
        except Exception as e:
            logger.error(f"Error during video conversion: {e}")
            return False, f"Conversion error: {str(e)}"
    
    def extract_video_metadata(self, video_info):
        """Extract video metadata from ffprobe output"""
        metadata = {
            'duration': None,
            'resolution': None,
            'file_size': None
        }
        
        if not video_info:
            return metadata
        
        try:
            # Extract duration
            format_info = video_info.get('format', {})
            duration_str = format_info.get('duration')
            if duration_str:
                metadata['duration'] = float(duration_str)
            
            # Extract file size
            size_str = format_info.get('size')
            if size_str:
                metadata['file_size'] = int(size_str)
            
            # Extract resolution from video streams
            streams = video_info.get('streams', [])
            video_streams = [s for s in streams if s.get('codec_type') == 'video']
            
            if video_streams:
                video_stream = video_streams[0]  # Use first video stream
                width = video_stream.get('width')
                height = video_stream.get('height')
                if width and height:
                    metadata['resolution'] = f"{width}x{height}"
                    
        except (ValueError, TypeError) as e:
            logger.warning(f"Error extracting video metadata: {e}")
        
        return metadata
    
    def convert_video_file(self, video_file, progress_callback=None):
        """Convert a VideoFile instance"""
        try:
            input_path = video_file.video_file.path
            
            # Get video info
            video_info = self.get_video_info(input_path)
            if not video_info:
                video_file.conversion_status = 'failed'
                video_file.conversion_error = "Unable to read video file"
                video_file.save()
                return False
            
            # Extract and save metadata regardless of conversion outcome
            metadata = self.extract_video_metadata(video_info)
            video_file.duration = metadata['duration']
            video_file.resolution = metadata['resolution']
            video_file.file_size = metadata['file_size']
            
            # Store original format info
            format_info = video_info.get('format', {})
            video_file.original_format = f"{format_info.get('format_name', 'unknown')} - {format_info.get('size', 0)} bytes"
            
            # Check if already compatible
            if self.is_web_compatible(video_info):
                video_file.conversion_status = 'skipped'
                video_file.is_web_compatible = True
                video_file.conversion_log = "Video is already web-compatible"
                video_file.save()
                return True
            
            # Start conversion
            video_file.conversion_status = 'converting'
            video_file.conversion_progress = 0
            video_file.save()
            
            # Generate output filename with video ID prefix
            original_name = Path(input_path).stem
            output_filename = f"{video_file.id}_{original_name}_converted.mp4"
            output_path = os.path.join(
                settings.MEDIA_ROOT, 
                'videos', 
                'converted', 
                output_filename
            )
            
            # Progress callback - use provided callback or default one
            if progress_callback:
                # Use the provided progress callback
                video_progress_callback = progress_callback
            else:
                # Use default progress callback that updates video_file
                def video_progress_callback(progress):
                    video_file.conversion_progress = progress
                    video_file.save()
            
            # Convert video
            success, message = self.convert_video(input_path, output_path, video_progress_callback)
            
            if success:
                # Store original file path before deletion
                original_file_path = video_file.video_file.path if video_file.video_file else None
                
                # Update video file with converted file
                with open(output_path, 'rb') as f:
                    video_file.converted_file.save(output_filename, ContentFile(f.read()))
                
                # Keep original file reference unchanged - don't update video_file.video_file
                # This maintains separation between original and converted files for retry scenarios
                video_file.conversion_status = 'completed'
                video_file.is_web_compatible = True
                video_file.converted_format = "MP4 - H.264+AAC"
                video_file.conversion_progress = 100
                video_file.conversion_log = message
                
                # Clean up temporary converted file
                os.remove(output_path)
                
                # Delete original file to save space
                if original_file_path and os.path.exists(original_file_path):
                    try:
                        os.remove(original_file_path)
                        logger.info(f"Deleted original file: {original_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete original file {original_file_path}: {e}")
                
            else:
                video_file.conversion_status = 'failed'
                video_file.conversion_error = message
                video_file.conversion_progress = 0
                # Even if conversion fails, metadata should already be saved above
            
            video_file.save()
            return success
            
        except Exception as e:
            logger.error(f"Error converting video file {video_file.id}: {e}")
            video_file.conversion_status = 'failed'
            video_file.conversion_error = str(e)
            video_file.save()
            return False


class VideoProcessor:
    """Main video processing service"""
    
    def __init__(self):
        self.converter = VideoConverter()
        self.detection_service = None
        self._initialize_detection_service()
    
    def _initialize_detection_service(self):
        """Initialize detection service"""
        try:
            from .detection_service import DetectionService
            self.detection_service = DetectionService()
            logger.info("Detection service initialized in VideoProcessor")
        except ImportError as e:
            logger.warning(f"Detection service not available: {e}")
    
    def process_video_for_detection(self, video_file, analysis, detection_types=None, progress_callback=None):
        """
        Process video file for object detection
        
        Args:
            video_file: VideoFile instance
            analysis: VideoAnalysis instance
            detection_types: List of detection types to run
            progress_callback: Optional progress callback
        
        Returns:
            bool: Success status
        """
        if not self.detection_service:
            logger.error("Detection service not available")
            analysis.status = 'failed'
            analysis.save()
            return False
        
        try:
            # Determine which video file to use
            video_path = None
            if video_file.converted_file and video_file.conversion_status == 'completed':
                video_path = video_file.converted_file.path
            elif video_file.original_file:
                video_path = video_file.original_file.path
            elif video_file.video_file:
                video_path = video_file.video_file.path
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                analysis.status = 'failed'
                analysis.save()
                return False
            
            # Extract frames and run detection
            success = self._extract_and_detect_frames(
                video_path, analysis, detection_types, progress_callback
            )
            
            if success:
                analysis.status = 'completed'
                analysis.completed_at = timezone.now()
                logger.info(f"Video detection completed for {video_file.original_filename}")
            else:
                analysis.status = 'failed'
            
            analysis.save()
            return success
            
        except Exception as e:
            logger.error(f"Error processing video for detection: {e}")
            analysis.status = 'failed'
            analysis.save()
            return False
    
    def _extract_and_detect_frames(self, video_path, analysis, detection_types=None, progress_callback=None):
        """
        Extract frames from video and run detection
        
        Args:
            video_path: Path to video file
            analysis: VideoAnalysis instance
            detection_types: List of detection types
            progress_callback: Progress callback function
        
        Returns:
            bool: Success status
        """
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return False
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Calculate frame interval based on analysis settings
            frame_interval = analysis.frame_interval or 1.0
            frames_to_process = int(duration / frame_interval)
            
            logger.info(f"Processing {frames_to_process} frames from {video_path}")
            
            frame_count = 0
            processed_frames = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Calculate timestamp
                timestamp = frame_count / fps if fps > 0 else frame_count
                
                # Process frame at specified interval
                if frame_count % int(frame_interval * fps) == 0:
                    # Convert frame to bytes
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()
                    
                    # Run detection
                    result = self.detection_service.process_frame(
                        frame_data=frame_bytes,
                        analysis=analysis,
                        frame_number=processed_frames + 1,
                        timestamp=timestamp,
                        enabled_detectors=detection_types
                    )
                    
                    processed_frames += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = int((processed_frames / frames_to_process) * 100)
                        progress_callback(progress)
                    
                    # Log progress every 10 frames
                    if processed_frames % 10 == 0:
                        logger.info(f"Processed {processed_frames}/{frames_to_process} frames")
                
                frame_count += 1
            
            cap.release()
            
            # Update analysis statistics
            analysis.total_frames_processed = processed_frames
            analysis.total_detections = analysis.detection_frames.count()
            analysis.save()
            
            logger.info(f"Frame extraction and detection completed: {processed_frames} frames processed")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting and detecting frames: {e}")
            return False
    
    def process_uploaded_video(self, video_file, progress_callback=None):
        """Process uploaded video including conversion and thumbnail generation"""
        try:
            # Store original file with ID prefix
            if video_file.video_file and not video_file.original_file:
                original_filename = f"{video_file.id}_original_{video_file.original_filename}"
                with video_file.video_file.open('rb') as src:
                    video_file.original_file.save(original_filename, ContentFile(src.read()))
            
            # Convert video if needed (this will also extract metadata)
            conversion_success = self.converter.convert_video_file(video_file, progress_callback=progress_callback)
            
            # If metadata wasn't extracted during conversion (e.g., conversion was skipped), try to extract it now
            if video_file.duration is None or video_file.resolution is None or video_file.file_size is None:
                file_to_analyze = None
                if video_file.converted_file and video_file.conversion_status == 'completed':
                    file_to_analyze = video_file.converted_file.path
                elif video_file.original_file:
                    file_to_analyze = video_file.original_file.path
                elif video_file.video_file:
                    file_to_analyze = video_file.video_file.path
                
                if file_to_analyze and os.path.exists(file_to_analyze):
                    video_info = self.converter.get_video_info(file_to_analyze)
                    metadata = self.converter.extract_video_metadata(video_info)
                    video_file.duration = metadata['duration']
                    video_file.resolution = metadata['resolution']
                    video_file.file_size = metadata['file_size']
            
            # Update status based on conversion result
            if conversion_success:
                video_file.status = 'processing'  # Ready for thumbnail generation
            else:
                # If conversion failed but original file exists, still process
                if video_file.original_file:
                    video_file.status = 'processing'  # Try to process original
                else:
                    video_file.status = 'failed'
            
            video_file.save()
            
            # Trigger thumbnail generation (this would be handled by existing thumbnail logic)
            return True
            
        except Exception as e:
            logger.error(f"Error processing uploaded video {video_file.id}: {e}")
            video_file.status = 'failed'
            video_file.save()
            return False
    
    def process_video_with_detection(self, video_file, user, analysis_type='barcode', title=None, detection_types=None):
        """
        Process video with detection (create analysis and run detection)
        
        Args:
            video_file: VideoFile instance
            user: User instance
            analysis_type: Type of analysis
            title: Optional title for analysis
            detection_types: List of detection types to run
        
        Returns:
            VideoAnalysis instance or None if failed
        """
        try:
            from ..models import VideoAnalysis
            
            # Create analysis record
            analysis = VideoAnalysis.objects.create(
                video_file=video_file,
                user=user,
                analysis_type=analysis_type,
                title=title or f"{analysis_type.title()} Analysis - {video_file.original_filename}",
                status='pending',
                detection_threshold=0.5,
                frame_interval=1.0  # 1 frame per second by default
            )
            
            logger.info(f"Created video analysis {analysis.id} for {video_file.original_filename}")
            
            # Process video for detection
            success = self.process_video_for_detection(
                video_file, analysis, detection_types
            )
            
            if success:
                return analysis
            else:
                # Clean up failed analysis
                analysis.delete()
                return None
                
        except Exception as e:
            logger.error(f"Error processing video with detection: {e}")
            return None