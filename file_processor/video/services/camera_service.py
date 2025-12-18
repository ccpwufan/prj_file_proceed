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
            'session_start': timezone.localtime().isoformat()
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
            timestamp = timezone.now().timestamp()
            
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
                'analysis_id': analysis_id,
                'saved_at': timezone.localtime().isoformat()
            }
            
        except VideoAnalysis.DoesNotExist:
            return {'error': f'Analysis {analysis_id} not found'}
        except Exception as e:
            logger.error(f"Error saving detection snapshot for analysis {analysis_id}: {e}")
            return {'error': str(e)}
    
    # Session management methods
    
    def start_session(self, user, title: str = None, detection_types: List[str] = None) -> VideoAnalysis:
        """
        Start a new camera detection session (alias for create_camera_analysis)
        
        Args:
            user: User instance
            title: Optional title for the session
            detection_types: List of detection types to enable
        
        Returns:
            VideoAnalysis instance
        """
        return self.create_camera_analysis(user, title, detection_types, status='processing')
    
    def get_session_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a camera session (alias for get_camera_analysis_info)
        
        Args:
            session_id: VideoAnalysis ID
        
        Returns:
            Dict with session information or None if not found
        """
        return self.get_camera_analysis_info(session_id)
    
    def close_session(self, session_id: int) -> Dict[str, Any]:
        """
        Close a camera detection session (alias for end_camera_session)
        
        Args:
            session_id: VideoAnalysis ID
        
        Returns:
            Dict with session summary
        """
        return self.end_camera_session(session_id)
    
    def update_session_status(self, session_id: int, status: str) -> Dict[str, Any]:
        """
        Update the status of a camera session
        
        Args:
            session_id: VideoAnalysis ID
            status: New status ('processing', 'completed', 'error', etc.)
        
        Returns:
            Dict with update result
        """
        try:
            analysis = VideoAnalysis.objects.get(id=session_id)
            old_status = analysis.status
            analysis.status = status
            analysis.save()
            
            logger.info(f"Updated session {session_id} status from '{old_status}' to '{status}'")
            
            return {
                'session_id': session_id,
                'old_status': old_status,
                'new_status': status,
                'updated_at': analysis.updated_at.isoformat(),
                'success': True
            }
            
        except VideoAnalysis.DoesNotExist:
            return {'error': f'Session {session_id} not found', 'success': False}
        except Exception as e:
            logger.error(f"Error updating session status for {session_id}: {e}")
            return {'error': str(e), 'success': False}
    
    def get_active_sessions(self, user=None) -> List[Dict[str, Any]]:
        """
        Get all active (processing) camera sessions
        
        Args:
            user: Optional user filter
        
        Returns:
            List of active session information
        """
        try:
            analyses = VideoAnalysis.objects.filter(
                video_file__isnull=True,  # Camera analysis only
                status='processing'
            )
            
            if user:
                analyses = analyses.filter(user=user)
            
            analyses = analyses.order_by('-created_at')
            
            sessions = []
            for analysis in analyses:
                sessions.append({
                    'session_id': analysis.id,
                    'user': analysis.user.username if analysis.user else 'Unknown',
                    'title': analysis.result_summary.get('title', '') if isinstance(analysis.result_summary, dict) else '',
                    'detection_types': analysis.result_summary.get('detection_types', ['barcode']) if isinstance(analysis.result_summary, dict) else ['barcode'],
                    'created_at': analysis.created_at.isoformat(),
                    'total_frames': analysis.total_frames_processed,
                    'total_detections': analysis.total_detections,
                    'is_camera_session': True
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    def get_session_statistics(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a specific session
        
        Args:
            session_id: VideoAnalysis ID
        
        Returns:
            Dict with session statistics or None if not found
        """
        try:
            analysis = VideoAnalysis.objects.get(id=session_id)
            
            # Get all detection frames
            frames = analysis.detection_frames.all()
            
            # Calculate statistics
            detection_counts = {}
            detection_by_type = {}
            total_processing_time = 0
            frame_count = len(frames)
            
            for frame in frames:
                detections = frame.detection_data.get('detections', [])
                frame_processing_time = frame.processing_time or 0
                total_processing_time += frame_processing_time
                
                for detection in detections:
                    det_type = detection.get('type', 'unknown')
                    det_class = detection.get('class', 'unknown')
                    
                    detection_counts[det_type] = detection_counts.get(det_type, 0) + 1
                    
                    if det_type not in detection_by_type:
                        detection_by_type[det_type] = {}
                    detection_by_type[det_type][det_class] = detection_by_type[det_type].get(det_class, 0) + 1
            
            # Calculate session duration
            session_duration = None
            if isinstance(analysis.result_summary, dict):
                session_start = analysis.result_summary.get('session_start')
                if analysis.status == 'completed':
                    session_end = analysis.result_summary.get('session_end')
                    if session_start and session_end:
                        try:
                            from datetime import datetime
                            start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
                            end = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
                            session_duration = (end - start).total_seconds()
                        except (ValueError, AttributeError):
                            pass
            
            return {
                'session_id': session_id,
                'session_duration_seconds': session_duration,
                'total_frames': frame_count,
                'total_detections': analysis.total_detections,
                'detection_counts': detection_counts,
                'detection_by_type_and_class': detection_by_type,
                'average_processing_time_ms': total_processing_time / frame_count if frame_count > 0 else 0,
                'detection_rate_per_frame': analysis.total_detections / frame_count if frame_count > 0 else 0,
                'status': analysis.status,
                'created_at': analysis.created_at.isoformat(),
                'updated_at': analysis.updated_at.isoformat(),
                'detection_threshold': analysis.detection_threshold,
                'performance_metrics': {
                    'total_processing_time_ms': total_processing_time,
                    'frames_per_second': frame_count / session_duration if session_duration and session_duration > 0 else 0
                }
            }
            
        except VideoAnalysis.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting session statistics for {session_id}: {e}")
            return None