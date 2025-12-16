"""
Camera detection service for real-time camera-based detection operations
"""
import logging
import time
import base64
from typing import Dict, Any, List, Optional
from django.core.files.base import ContentFile
from django.utils import timezone
from ..models import VideoAnalysis, VideoDetectionFrame

logger = logging.getLogger(__name__)


class CameraService:
    """
    Service class for managing camera-based detection operations
    """
    
    def __init__(self):
        self.detection_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize dependent services"""
        try:
            from .detection_service import DetectionService
            self.detection_service = DetectionService()
            logger.info("Detection service initialized for camera operations")
        except ImportError as e:
            logger.error(f"Failed to initialize detection service: {e}")
    
    def create_camera_analysis(self, user, title: str = None, 
                              detection_types: List[str] = None, status: str = 'processing') -> VideoAnalysis:
        """
        Create a new camera-based analysis session
        
        Args:
            user: User instance
            title: Optional title for the analysis
            detection_types: List of detection types to enable
            status: Initial status for the analysis ('processing' or 'completed')
        
        Returns:
            VideoAnalysis instance
        """
        if detection_types is None:
            detection_types = ['barcode']  # Default to barcode detection
        
        analysis = VideoAnalysis.objects.create(
            video_file=None,  # Camera analysis doesn't have a video file
            user=user,
            analysis_type='object_detection',  # Use existing analysis type
            status=status,  # Use provided status parameter
            detection_threshold=0.5,
            frame_interval=1.0,  # 1 frame per second for camera
            total_frames_processed=0,
            total_detections=0
        )
        
        # Prepare result_summary data with all information
        result_summary_data = {
            'detection_types': detection_types,
            'camera_session': True,
            'session_start': timezone.now().isoformat()
        }
        
        # Add title if provided
        if title:
            result_summary_data['title'] = title
        
        # Set result_summary and detection_type
        analysis.result_summary = result_summary_data
        analysis.detection_type = detection_types[0] if detection_types else 'barcode'
        analysis.save()
        
        logger.info(f"Created camera analysis {analysis.id} for user {user.username}")
        return analysis
    
    def process_camera_frame(self, analysis_id: int, frame_data: str, 
                           detection_types: List[str] = None) -> Dict[str, Any]:
        """
        Process a camera frame (base64 encoded)
        
        Args:
            analysis_id: VideoAnalysis ID
            frame_data: Base64 encoded frame data
            detection_types: List of detection types to use
        
        Returns:
            Dict containing detection results
        """
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            
            # Decode base64 frame data
            if frame_data.startswith('data:image/'):
                # Remove data URL prefix
                frame_data = frame_data.split(',')[1]
            
            frame_bytes = base64.b64decode(frame_data)
            
            # Generate frame number and timestamp
            frame_number = analysis.total_frames_processed + 1
            timestamp = time.time()
            
            if not self.detection_service:
                return {
                    'error': 'Detection service not available',
                    'frame_number': frame_number
                }
            
            # Process frame with detection service
            result = self.detection_service.process_frame(
                frame_data=frame_bytes,
                analysis=analysis,
                frame_number=frame_number,
                timestamp=timestamp,
                enabled_detectors=detection_types
            )
            
            # Update analysis statistics
            analysis.total_frames_processed = frame_number
            analysis.total_detections += result['summary']['total_count']
            analysis.save()
            
            # Add camera-specific metadata to result
            result['camera'] = {
                'session_id': analysis_id,
                'timestamp': timestamp,
                'frame_rate': 1.0 / analysis.frame_interval if analysis.frame_interval > 0 else 1.0
            }
            
            return result
            
        except VideoAnalysis.DoesNotExist:
            return {'error': f'Analysis {analysis_id} not found'}
        except Exception as e:
            logger.error(f"Error processing camera frame for analysis {analysis_id}: {e}")
            return {'error': str(e)}
    
    def get_camera_analysis_info(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a camera session
        
        Args:
            analysis_id: VideoAnalysis ID
        
        Returns:
            Dict with session information or None if not found
        """
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            
            # Get recent detection frames
            recent_frames = analysis.detection_frames.order_by('-frame_number')[:10]
            
            return {
                'session_id': analysis_id,
                'title': analysis.result_summary.get('Title', '') if isinstance(analysis.result_summary, dict) else str(analysis.result_summary or ''),
                'status': analysis.status,
                'created_at': analysis.created_at.isoformat(),
                'total_frames': analysis.total_frames_processed,
                'total_detections': analysis.total_detections,
                'detection_types': analysis.result_summary.get('detection_types', []) if isinstance(analysis.result_summary, dict) else ['barcode'],
                'recent_frames': [
                    {
                        'frame_number': frame.frame_number,
                        'timestamp': frame.timestamp,
                        'detection_count': len(frame.detection_data.get('detections', [])),
                        'processing_time': frame.processing_time,
                        'frame_image_url': frame.frame_image.url if frame.frame_image else None
                    }
                    for frame in recent_frames
                ]
            }
            
        except VideoAnalysis.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting camera session info for {analysis_id}: {e}")
            return None
    
    def end_camera_session(self, analysis_id: int) -> Dict[str, Any]:
        """
        End a camera detection session
        
        Args:
            analysis_id: VideoAnalysis ID
        
        Returns:
            Dict with session summary
        """
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            
            # Get final session statistics
            detection_frames = analysis.detection_frames.all()
            
            # Count detections by type
            detection_counts = {}
            total_processing_time = 0
            
            for frame in detection_frames:
                detections = frame.detection_data.get('detections', [])
                for detection in detections:
                    det_type = detection.get('type', 'unknown')
                    detection_counts[det_type] = detection_counts.get(det_type, 0) + 1
                
                total_processing_time += frame.processing_time or 0
            
            # Update analysis status
            analysis.status = 'completed'
            analysis.result_summary = {
                **analysis.result_summary,
                'session_end': timezone.now().isoformat(),
                'final_statistics': {
                    'total_frames': analysis.total_frames_processed,
                    'total_detections': analysis.total_detections,
                    'detection_counts': detection_counts,
                    'average_processing_time_ms': total_processing_time / len(detection_frames) if detection_frames else 0,
                    'detection_rate': analysis.total_detections / analysis.total_frames_processed if analysis.total_frames_processed > 0 else 0
                }
            }
            analysis.save()
            
            return {
                'session_id': analysis_id,
                'final_statistics': analysis.result_summary['final_statistics'],
                'status': 'completed'
            }
            
        except VideoAnalysis.DoesNotExist:
            return {'error': f'Analysis {analysis_id} not found'}
        except Exception as e:
            logger.error(f"Error ending camera session {analysis_id}: {e}")
            return {'error': str(e)}
    
    
    def save_detection_snapshot(self, analysis_id: int, image_data: bytes, 
                               detection_data: Dict) -> Dict[str, Any]:
        """
        Save a camera snapshot with detection results
        
        Args:
            analysis_id: VideoAnalysis ID
            image_data: Raw image data (bytes)
            detection_data: Detection data dictionary (without image)
        
        Returns:
            Dict with snapshot information
        """
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            
            # Create a detection frame for the snapshot
            frame_number = analysis.total_frames_processed + 1
            timestamp = time.time()
            
            # The detection_data is already prepared from frontend
            # Just ensure required fields exist
            if 'detection_type' not in detection_data:
                detection_data['detection_type'] = 'unknown'
            if 'threshold' not in detection_data:
                detection_data['threshold'] = 0.0
            if 'time' not in detection_data:
                detection_data['time'] = 0
            
            # Prepare the snapshot image
            filename = f"snapshot_{analysis_id}_{int(timestamp)}.jpg"
            image_file = ContentFile(image_data, filename)
            
            # Create a detection frame record for the snapshot with image
            detection_frame = VideoDetectionFrame.objects.create(
                video_analysis=analysis,
                frame_number=frame_number,
                timestamp=timestamp,
                detection_type=detection_data.get('detection_type', 'snapshot'),
                detection_data=detection_data,
                processing_time=0.0,
                frame_image=image_file
            )
            
            # Update analysis statistics
            analysis.total_frames_processed = frame_number
            detections_count = len(detection_data.get('detections', []))
            analysis.total_detections += detections_count
            analysis.save()
            
            detections_count = len(detection_data.get('detections', []))
            logger.info(f"Saved snapshot {detection_frame.id} for analysis {analysis_id} with {detections_count} detections")
            
            return {
                'snapshot_id': detection_frame.id,
                'frame_number': frame_number,
                'timestamp': timestamp,
                'image_url': str(detection_frame.frame_image.url) if detection_frame.frame_image else None,
                'detection_count': detections_count,
                'analysis_id': analysis_id
            }
            
        except VideoAnalysis.DoesNotExist:
            return {'error': f'Analysis {analysis_id} not found'}
        except Exception as e:
            logger.error(f"Error saving detection snapshot for analysis {analysis_id}: {e}")
            return {'error': str(e)}
    
    def re_detect(self, frame_id: int) -> Optional[Dict[str, Any]]:
        """
        Re-detect a specific detection frame using updated detection parameters
        
        Args:
            frame_id: VideoDetectionFrame ID to re-detect
            
        Returns:
            Dict with updated detection results or None if failed
        """
        try:
            from ..models import VideoDetectionFrame
            
            # Get the detection frame
            frame = VideoDetectionFrame.objects.get(id=frame_id)
            analysis = frame.video_analysis
            
            # 标记这是重检测操作
            analysis._is_re_detect = True
            
            if not self.detection_service:
                logger.error("Detection service not available for re-detection")
                return None
            
            # Check if frame has an image
            if not frame.frame_image:
                logger.error(f"Frame {frame_id} has no image for re-detection")
                return None
            
            # Read the image data
            with open(frame.frame_image.path, 'rb') as f:
                image_data = f.read()
            
            # Perform re-detection with current parameters
            result = self.detection_service.process_frame(
                frame_data=image_data,
                analysis=analysis,
                frame_number=frame.frame_number,
                timestamp=frame.timestamp,
                enabled_detectors=[analysis.detection_type or 'barcode']
            )
            
            if 'error' in result:
                logger.error(f"Detection service error for frame {frame_id}: {result['error']}")
                return None
            
            # 由于_save_detection_frame已经处理了数据格式化和保存，这里只需要返回结果
            new_detections = result.get('detections', [])
            logger.info(f"Re-detection completed for frame {frame_id}, found {len(new_detections)} detections")
            
            return {
                'frame_id': frame_id,
                'detection_count': len(new_detections),
                'detections': new_detections,
                'processing_time': frame.processing_time
            }
            
        except VideoDetectionFrame.DoesNotExist:
            logger.error(f"Frame {frame_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error in re_detect for frame {frame_id}: {e}")
            return None