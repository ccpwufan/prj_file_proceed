"""
Detection service for integrating and managing multiple detection algorithms
"""
import logging
import time
from typing import List, Dict, Any, Optional
import numpy as np
from django.conf import settings
from ..models import VideoAnalysis, VideoDetectionFrame
from django.utils import timezone
import cv2
from django.core.files.base import ContentFile
import os
from django.contrib.auth.models import User
from datetime import datetime

logger = logging.getLogger(__name__)


class DetectionService:
    """
    Service class for managing detection operations and integrating multiple detectors
    """
    
    def __init__(self):
        self.detectors = {}
        self._initialize_detectors()
    
    def _initialize_detectors(self):
        """Initialize all available detectors"""
        # This will be expanded as we add more detectors
        try:
            # Import and initialize barcode detector
            from ..detectors import BarcodeDetector
            self.detectors['barcode'] = BarcodeDetector()
            logger.info("Barcode detector initialized")
        except ImportError:
            logger.warning("Barcode detector not available")
        
        # Future detectors will be added here
        # try:
        #     from ..detectors import PhoneDetector
        #     self.detectors['phone'] = PhoneDetector()
        #     logger.info("Phone detector initialized")
        # except ImportError:
        #     logger.warning("Phone detector not available")
    
    def detect_objects(self, frame: np.ndarray, detection_types: List[str] = None, 
                      threshold: float = 0.5) -> Dict[str, Any]:
        """
        Detect objects in image frame using specified detectors
        
        Args:
            frame: Input image as numpy array (BGR format)
            detection_types: List of detector types to use
            threshold: Detection threshold (confidence threshold)
        
        Returns:
            Dict containing detection results
        """
        from ..detectors import MultiTypeDetector
        
        try:
            logger.debug(f"[BARCODE_DETECT] Starting detect_objects - detection_types: {detection_types}, threshold: {threshold}")
            
            # Initialize multi-detector
            detector_manager = MultiTypeDetector()
            
            logger.debug(f"[BARCODE_DETECT] Initialized MultiTypeDetector with {len(detector_manager.detectors)} detectors: {list(detector_manager.detectors.keys())}")
            
            # Apply threshold to configuration if provided
            if threshold and detection_types:
                threshold_config = {detection_types[0]: threshold}
                detector_manager.update_thresholds(threshold_config)
                logger.debug(f"[BARCODE_DETECT] Updated detector thresholds: {threshold_config}")
            
            # Run detection
            logger.debug(f"[BARCODE_DETECT] Running detection with enabled_types: {detection_types}")
            results = detector_manager.detect_all(frame, enabled_types=detection_types)
            
            # Extract results for the requested detection types
            formatted_results = {}
            if detection_types:
                for det_type in detection_types:
                    if det_type in detector_manager.detectors:
                        logger.debug(f"[BARCODE_DETECT] Calling detector '{det_type}' on frame with shape: {frame.shape}")
                        # Get detections from this detector
                        det_results = detector_manager.detectors[det_type].detect(frame)
                        logger.debug(f"[BARCODE_DETECT] Detector '{det_type}' returned {len(det_results)} results")
                        formatted_results[det_type] = det_results
                    else:
                        logger.debug(f"[BARCODE_DETECT] Detector '{det_type}' not available, returning empty list")
                        formatted_results[det_type] = []
            
            return {
                'detections': formatted_results,
                'processing_time': results.get('total_processing_time_ms', 0) / 1000.0,  # Convert to seconds
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return {
                'detections': {},
                'processing_time': 0,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def process_frame(self, frame_data: bytes, analysis: VideoAnalysis, 
                     frame_number: int, timestamp: float, 
                     enabled_detectors: List[str] = None) -> Dict[str, Any]:
        """
        Process a single frame with specified detectors
        
        Args:
            frame_data: Raw frame data (bytes)
            analysis: VideoAnalysis instance
            frame_number: Frame number in the video
            timestamp: Timestamp in seconds
            enabled_detectors: List of detector types to use
        
        Returns:
            Dict containing detection results and metadata
        """
        start_time = time.time()
        
        if enabled_detectors is None:
            enabled_detectors = list(self.detectors.keys())
        
        all_detections = []
        detection_summary = {}
        
        # Process frame with each enabled detector
        for detector_type in enabled_detectors:
            if detector_type not in self.detectors:
                logger.warning(f"Detector {detector_type} not available")
                continue
            
            try:
                detector = self.detectors[detector_type]
                detections = detector.detect_from_bytes(frame_data)
                
                # Add detector type to each detection
                for detection in detections:
                    detection['detection_type'] = detector_type
                
                all_detections.extend(detections)
                detection_summary[f'{detector_type}_count'] = len(detections)
                
                logger.debug(f"Frame {frame_number}: {detector_type} detected {len(detections)} objects")
                
            except Exception as e:
                logger.error(f"Error in {detector_type} detector for frame {frame_number}: {e}")
                detection_summary[f'{detector_type}_error'] = str(e)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        detection_summary['total_count'] = len(all_detections)
        detection_summary['processing_time_ms'] = processing_time
        
        # Save detection results to database
        detection_frame = self._save_detection_frame(
            analysis, frame_number, frame_data, timestamp, 
            all_detections, processing_time
        )
        
        return {
            'frame_id': detection_frame.id,
            'detections': all_detections,
            'summary': detection_summary,
            'processing_time_ms': processing_time
        }
    
    def _save_detection_frame(self, analysis: VideoAnalysis, frame_number: int, 
                             frame_data: bytes, timestamp: float, 
                             detections: List[Dict], processing_time: float,
                             detection_type: str = None, threshold: float = None) -> VideoDetectionFrame:
        """
        Save or update detection frame to database
        
        Args:
            analysis: VideoAnalysis instance
            frame_number: Frame number
            frame_data: Raw frame data
            timestamp: Timestamp in seconds
            detections: List of detection results
            processing_time: Processing time in milliseconds
            detection_type: Detection type override (for re-detection)
            threshold: Detection threshold override (for re-detection)
        
        Returns:
            VideoDetectionFrame instance
        """

        
        # Try to get existing frame record first
        try:
            detection_frame = VideoDetectionFrame.objects.get(
                video_analysis=analysis,
                frame_number=frame_number
            )
            # Update existing record
            detection_frame.timestamp = timestamp
            detection_frame.processing_time = processing_time
            # Use provided override parameters or fall back to analysis values
            actual_detection_type = detection_type or analysis.detection_type or 'barcode'
            actual_threshold = threshold if threshold is not None else analysis.detection_threshold or 0.5
            
            # Use the same structure as CameraService.re_detect
            detection_frame.detection_data = {
                'detections': detections,
                'detection_type': actual_detection_type,
                'threshold': actual_threshold,
                'time': timestamp,
                're_detected': True if getattr(analysis, '_is_re_detect', False) else False,
                're_detection_timestamp': timezone.now().isoformat() if getattr(analysis, '_is_re_detect', False) else None
            }
            detection_frame.save()
            logger.info(f"Updated existing detection frame {frame_number}")
        except VideoDetectionFrame.DoesNotExist:
            # Create new record if it doesn't exist
            frame_filename = f"frame_{analysis.id}_{frame_number:06d}.jpg"
            detection_frame = VideoDetectionFrame.objects.create(
                video_analysis=analysis,
                frame_number=frame_number,
                timestamp=timestamp,
                processing_time=processing_time,
                detection_data={
                    'detections': detections,
                    'detection_type': detection_type or analysis.detection_type or 'barcode',
                    'threshold': threshold if threshold is not None else analysis.detection_threshold or 0.5,
                    'time': timestamp
                }
            )
            # Save frame image only for new records
            detection_frame.frame_image.save(frame_filename, ContentFile(frame_data))
            detection_frame.save()
            logger.info(f"Created new detection frame {frame_number}")
        
        return detection_frame
    
    def get_available_detectors(self) -> List[str]:
        """Get list of available detector types"""
        return list(self.detectors.keys())
    
    def get_detection_history(self, user=None, limit: int = 10, detection_type: str = None, 
                             start_date=None, end_date=None) -> List[Dict[str, Any]]:
        """
        Get detection history with filtering options
        
        Args:
            user: User instance to filter by (None for all users)
            limit: Maximum number of records to return
            detection_type: Filter by detection type (barcode, phone, etc.)
            start_date: Filter by start date (datetime or string)
            end_date: Filter by end date (datetime or string)
        
        Returns:
            List of dictionaries containing detection history
        """
        try:

            
            # Start with all camera analyses
            analyses = VideoAnalysis.objects.filter(
                video_file__isnull=True  # Camera analysis only
            )
            
            # Apply filters
            if user:
                analyses = analyses.filter(user=user)
            
            if detection_type:
                analyses = analyses.filter(detection_type=detection_type)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                analyses = analyses.filter(created_at__gte=start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                analyses = analyses.filter(created_at__lte=end_date)
            
            # Order by creation date and limit results
            analyses = analyses.order_by('-created_at')[:limit]
            
            history = []
            for analysis in analyses:
                # Get recent frames for this analysis
                recent_frames = analysis.detection_frames.order_by('-frame_number')[:5]
                
                # Calculate session duration if completed
                session_duration = None
                if analysis.status == 'completed' and isinstance(analysis.result_summary, dict):
                    session_start = analysis.result_summary.get('session_start')
                    session_end = analysis.result_summary.get('session_end')
                    if session_start and session_end:
                        try:
                            start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
                            end = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
                            session_duration = (end - start).total_seconds()
                        except (ValueError, AttributeError):
                            pass
                
                # Detection type(s)
                detection_types = ['barcode']
                if isinstance(analysis.result_summary, dict):
                    detection_types = analysis.result_summary.get('detection_types', ['barcode'])
                
                history.append({
                    'analysis_id': analysis.id,
                    'user': analysis.user.username if analysis.user else 'Unknown',
                    'title': analysis.result_summary.get('title', '') if isinstance(analysis.result_summary, dict) else '',
                    'status': analysis.status,
                    'detection_type': analysis.detection_type or 'barcode',
                    'detection_types': detection_types,
                    'total_frames': analysis.total_frames_processed,
                    'total_detections': analysis.total_detections,
                    'detection_threshold': analysis.detection_threshold,
                    'created_at': analysis.created_at.isoformat(),
                    'updated_at': analysis.updated_at.isoformat(),
                    'session_duration_seconds': session_duration,
                    'recent_frames_count': len(recent_frames),
                    'average_detections_per_frame': (
                        analysis.total_detections / analysis.total_frames_processed 
                        if analysis.total_frames_processed > 0 else 0
                    ),
                    'has_frames': len(recent_frames) > 0,
                    'recent_frame_sample': {
                        'frame_number': recent_frames[0].frame_number,
                        'detection_count': len(recent_frames[0].detection_data.get('detections', [])),
                        'frame_image_url': recent_frames[0].frame_image.url if recent_frames[0].frame_image else None
                    } if recent_frames else None
                })
            
            logger.info(f"Retrieved {len(history)} detection history records")
            return history
            
        except Exception as e:
            logger.error(f"Error getting detection history: {e}")
            return []
    
    def re_detect(self, frame_id: int, detection_type: str = None, threshold: float = None) -> Optional[Dict[str, Any]]:
        """
        Re-detect a specific detection frame using updated detection parameters
        
        Args:
            frame_id: VideoDetectionFrame ID to re-detect
            detection_type: Optional detection type override
            threshold: Optional detection threshold override
            
        Returns:
            Dict with updated detection results or None if failed
        """
        try:
            logger.debug(f"[BARCODE_DETECT] Starting re-detection for frame_id: {frame_id}")
            
            # Get the detection frame
            frame = VideoDetectionFrame.objects.get(id=frame_id)
            analysis = frame.video_analysis
            
            logger.debug(f"[BARCODE_DETECT] Retrieved frame - frame_number: {frame.frame_number}, analysis_id: {analysis.id}")
            
            # Mark this as a re-detection operation
            analysis._is_re_detect = True
            
            # Check if frame has an image
            if not frame.frame_image:
                logger.debug(f"[BARCODE_DETECT] Frame {frame_id} has no image for re-detection")
                return None
            
            # Use provided parameters or fall back to original ones
            actual_detection_type = detection_type or analysis.detection_type or 'barcode'
            actual_threshold = threshold if threshold is not None else analysis.detection_threshold or 0.5
            
            logger.debug(f"[BARCODE_DETECT] Using detection parameters - type: {actual_detection_type}, threshold: {actual_threshold}")
            
            # Read and convert image to numpy array for detect_objects
            image_path = frame.frame_image.path
            logger.debug(f"[BARCODE_DETECT] Reading image from path: {image_path}")
            
            image_array = cv2.imread(image_path)
            if image_array is None:
                logger.debug(f"[BARCODE_DETECT] Failed to read image {image_path} for re-detection")
                return None
            
            logger.debug(f"[BARCODE_DETECT] Successfully loaded image - shape: {image_array.shape}, dtype: {image_array.dtype}")
            
            # Perform re-detection using detect_objects with proper threshold
            # Note: detect_objects internally handles threshold application via update_thresholds
            logger.debug(f"[BARCODE_DETECT] Calling detect_objects - detection_types: [{actual_detection_type}], threshold: {actual_threshold}")
            
            result = self.detect_objects(
                frame=image_array,
                detection_types=[actual_detection_type],
                threshold=actual_threshold
            )
            
            if 'error' in result:
                logger.error(f"Detection service error for frame {frame_id}: {result['error']}")
                return None
            
            # Extract detections from the result
            new_detections = result.get('detections', {}).get(actual_detection_type, [])
            
            # Add detection type to each detection for consistency
            for detection in new_detections:
                detection['detection_type'] = actual_detection_type
            
            # Update the detection frame with new results and correct parameters
            detection_frame = self._save_detection_frame(
                analysis=analysis,
                frame_number=frame.frame_number,
                frame_data=cv2.imencode('.jpg', image_array)[1].tobytes(),
                timestamp=frame.timestamp,
                detections=new_detections,
                processing_time=result.get('processing_time', 0) * 1000,  # Convert to milliseconds
                detection_type=actual_detection_type,
                threshold=actual_threshold
            )
            
            logger.debug(f"[BARCODE_DETECT] Re-detection completed for frame {frame_id} using {actual_detection_type} (threshold={actual_threshold}), found {len(new_detections)} detections")
            
            return_result = {
                'frame_id': frame_id,
                'detection_count': len(new_detections),
                'detections': new_detections,
                'processing_time': detection_frame.processing_time,
                'detection_type': actual_detection_type,
                'threshold': actual_threshold,
                're_detection_timestamp': timezone.localtime().isoformat()
            }
            
            logger.debug(f"[BARCODE_DETECT] Returning re-detection result - detection_count: {return_result['detection_count']}, processing_time: {return_result['processing_time']:.2f}ms")
            return return_result
            
        except VideoDetectionFrame.DoesNotExist:
            logger.error(f"Frame {frame_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error in re_detect for frame {frame_id}: {e}")
            return None
    

    
