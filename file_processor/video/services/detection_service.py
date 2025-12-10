"""
Detection service for integrating and managing multiple detection algorithms
"""
import logging
import time
from typing import List, Dict, Any, Optional
import numpy as np
from django.conf import settings
from ..models import VideoAnalysis, VideoDetectionFrame

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
        import numpy as np
        from ..detectors import MultiTypeDetector
        
        try:
            # Initialize multi-detector
            detector_manager = MultiTypeDetector()
            
            # Apply threshold to configuration if provided
            if threshold:
                detector_manager.update_thresholds({detection_types[0]: threshold} if detection_types else {})
            
            # Run detection
            results = detector_manager.detect_all(frame, enabled_types=detection_types)
            
            # Extract results for the requested detection types
            formatted_results = {}
            if detection_types:
                for det_type in detection_types:
                    if det_type in detector_manager.detectors:
                        # Get detections from this detector
                        det_results = detector_manager.detectors[det_type].detect(frame)
                        formatted_results[det_type] = det_results
                    else:
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
                             detections: List[Dict], processing_time: float) -> VideoDetectionFrame:
        """
        Save detection frame to database
        
        Args:
            analysis: VideoAnalysis instance
            frame_number: Frame number
            frame_data: Raw frame data
            timestamp: Timestamp in seconds
            detections: List of detection results
            processing_time: Processing time in milliseconds
        
        Returns:
            VideoDetectionFrame instance
        """
        from django.core.files.base import ContentFile
        import os
        
        # Generate filename for frame image
        frame_filename = f"frame_{analysis.id}_{frame_number:06d}.jpg"
        
        # Create detection frame record
        detection_frame = VideoDetectionFrame.objects.create(
            video_analysis=analysis,
            frame_number=frame_number,
            timestamp=timestamp,
            processing_time=processing_time,
            detection_data={
                'detections': detections,
                'summary': {
                    'total_detections': len(detections),
                    'detection_types': list(set(d.get('type', 'unknown') for d in detections))
                }
            }
        )
        
        # Save frame image
        detection_frame.frame_image.save(frame_filename, ContentFile(frame_data))
        detection_frame.save()
        
        logger.info(f"Saved detection frame {frame_number} with {len(detections)} detections")
        
        return detection_frame
    
    def get_available_detectors(self) -> List[str]:
        """Get list of available detector types"""
        return list(self.detectors.keys())
    
    def get_detector_info(self, detector_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific detector"""
        if detector_type not in self.detectors:
            return None
        
        detector = self.detectors[detector_type]
        return {
            'type': detector_type,
            'name': getattr(detector, 'name', detector_type.capitalize()),
            'description': getattr(detector, 'description', f"{detector_type} detector"),
            'version': getattr(detector, 'version', '1.0.0'),
            'supported_formats': getattr(detector, 'supported_formats', []),
            'capabilities': getattr(detector, 'capabilities', {})
        }
    
    def batch_process_frames(self, frames_data: List[Dict], analysis: VideoAnalysis,
                           enabled_detectors: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process multiple frames in batch
        
        Args:
            frames_data: List of frame data dictionaries
            analysis: VideoAnalysis instance
            enabled_detectors: List of detector types to use
        
        Returns:
            List of processing results for each frame
        """
        results = []
        
        logger.info(f"Starting batch processing of {len(frames_data)} frames")
        
        for i, frame_data in enumerate(frames_data):
            try:
                result = self.process_frame(
                    frame_data=frame_data['data'],
                    analysis=analysis,
                    frame_number=frame_data['frame_number'],
                    timestamp=frame_data['timestamp'],
                    enabled_detectors=enabled_detectors
                )
                results.append(result)
                
                # Log progress every 10 frames
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(frames_data)} frames")
                    
            except Exception as e:
                logger.error(f"Error processing frame {frame_data.get('frame_number', i)}: {e}")
                results.append({
                    'error': str(e),
                    'frame_number': frame_data.get('frame_number', i)
                })
        
        logger.info(f"Completed batch processing: {len([r for r in results if 'error' not in r])} successful, "
                   f"{len([r for r in results if 'error' in r])} failed")
        
        return results