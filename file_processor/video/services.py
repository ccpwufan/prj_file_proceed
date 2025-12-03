import os
import cv2
import json
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import VideoFile, VideoAnalysis, VideoDetectionFrame


class VideoProcessingService:
    """Service for processing video files and performing analysis"""
    
    def __init__(self, video_file):
        self.video_file = video_file
        self.video_path = video_file.video_file.path
    
    def extract_video_metadata(self):
        """Extract metadata from video file"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Get file size
            file_size = os.path.getsize(self.video_path)
            
            # Update video file model
            self.video_file.duration = duration
            self.video_file.file_size = file_size
            self.video_file.resolution = f"{width}x{height}"
            self.video_file.save()
            
            cap.release()
            return True
            
        except Exception as e:
            print(f"Error extracting video metadata: {e}")
            return False
    
    def generate_thumbnail(self):
        """Generate thumbnail from video"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            
            # Get frame at 1 second or first frame
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(fps) if fps > 0 else 0
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            
            if ret:
                # Resize frame to thumbnail size
                thumbnail = cv2.resize(frame, (320, 240))
                
                # Save thumbnail
                thumbnail_filename = f"thumb_{self.video_file.id}.jpg"
                thumbnail_path = os.path.join(settings.MEDIA_ROOT, 'video_thumbnails', thumbnail_filename)
                
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                cv2.imwrite(thumbnail_path, thumbnail)
                
                # Update model
                self.video_file.thumbnail = f"video_thumbnails/{thumbnail_filename}"
                self.video_file.save()
            
            cap.release()
            return True
            
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return False


class VideoAnalysisService:
    """Service for performing video analysis"""
    
    def __init__(self, analysis):
        self.analysis = analysis
        self.video_file = analysis.video_file
        self.video_path = self.video_file.video_file.path
    
    def start_analysis(self):
        """Start video analysis process"""
        try:
            # Update analysis status
            self.analysis.status = 'processing'
            self.analysis.save()
            
            # Process video frames
            self._process_video_frames()
            
            # Update completion status
            self.analysis.status = 'completed'
            self.analysis.completed_at = timezone.now()
            self.analysis.save()
            
            return True
            
        except Exception as e:
            print(f"Error during analysis: {e}")
            self.analysis.status = 'failed'
            self.analysis.save()
            return False
    
    def _process_video_frames(self):
        """Process video frames for detection"""
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval_frames = int(fps * self.analysis.frame_interval)
        
        frame_number = 0
        total_detections = 0
        frames_processed = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame at specified interval
            if frame_number % frame_interval_frames == 0:
                # Perform detection (placeholder for actual detection logic)
                detection_result = self._perform_detection(frame)
                
                if detection_result['detections']:
                    total_detections += len(detection_result['detections'])
                    
                    # Save frame image
                    frame_filename = f"frame_{self.analysis.id}_{frame_number}.jpg"
                    frame_path = os.path.join(settings.MEDIA_ROOT, 'detection_frames', frame_filename)
                    
                    os.makedirs(os.path.dirname(frame_path), exist_ok=True)
                    cv2.imwrite(frame_path, frame)
                    
                    # Create detection frame record
                    VideoDetectionFrame.objects.create(
                        video_analysis=self.analysis,
                        frame_number=frame_number,
                        frame_image=f"detection_frames/{frame_filename}",
                        detection_data=detection_result,
                        timestamp=frame_number / fps if fps > 0 else 0
                    )
                
                frames_processed += 1
            
            frame_number += 1
        
        # Update analysis summary
        self.analysis.total_frames_processed = frames_processed
        self.analysis.total_detections = total_detections
        self.analysis.result_summary = f"Processed {frames_processed} frames, found {total_detections} detections"
        self.analysis.save()
        
        cap.release()
    
    def _perform_detection(self, frame):
        """Perform object detection on frame (placeholder implementation)"""
        # This is a placeholder for actual detection logic
        # In a real implementation, you would use YOLO, OpenCV, or other detection models
        
        # Simulate detection result
        detection_result = {
            'detections': [],
            'confidence_threshold': self.analysis.detection_threshold,
            'timestamp': timezone.now().isoformat()
        }
        
        # Placeholder: simulate random phone detection
        import random
        if random.random() > 0.7:  # 30% chance of detection
            detection_result['detections'] = [
                {
                    'class': 'phone',
                    'confidence': random.uniform(0.5, 0.9),
                    'bbox': [random.randint(50, 200), random.randint(50, 200), 100, 150]
                }
            ]
        
        return detection_result


class CameraDetectionService:
    """Service for real-time camera detection"""
    
    def __init__(self):
        self.cap = None
    
    def start_camera(self, camera_index=0):
        """Start camera capture"""
        self.cap = cv2.VideoCapture(camera_index)
        return self.cap.isOpened()
    
    def capture_frame(self):
        """Capture single frame from camera"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            return frame if ret else None
        return None
    
    def stop_camera(self):
        """Stop camera capture"""
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def detect_objects(self, frame):
        """Detect objects in camera frame (placeholder)"""
        # Placeholder implementation
        # In real implementation, use YOLO or other detection models
        return {
            'detections': [],
            'timestamp': timezone.now().isoformat()
        }