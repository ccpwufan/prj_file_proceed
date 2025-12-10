"""
Multi-detector manager for coordinating multiple detection algorithms
"""
import logging
import time
from typing import List, Dict, Any, Optional, Union
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .base import BaseDetector, DetectorError
from .barcode_detector import BarcodeDetector

# Import future detectors when implemented
# from .phone_detector import PhoneDetector
# from .yellow_box_detector import YellowBoxDetector

logger = logging.getLogger(__name__)


class MultiTypeDetector:
    """
    Multi-type detector manager that coordinates multiple detection algorithms
    
    This class manages multiple detectors and provides a unified interface for
    running different types of detection simultaneously or individually.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize multi-detector manager
        
        Args:
            config: Configuration dictionary with options:
                - enable_parallel: Enable parallel processing (default: True)
                - max_workers: Maximum number of parallel workers (default: 4)
                - detector_configs: Individual detector configurations
        """
        self.config = {
            'enable_parallel': True,
            'max_workers': 4,
            'detector_configs': {},
            **(config or {})
        }
        
        self.detectors = {}
        self.detector_lock = threading.Lock()
        self._initialize_detectors()
    
    def _initialize_detectors(self):
        """Initialize all available detectors"""
        detector_configs = self.config.get('detector_configs', {})
        
        # Initialize barcode detector
        try:
            barcode_config = detector_configs.get('barcode', {})
            self.detectors['barcode'] = BarcodeDetector(barcode_config)
            logger.info("Barcode detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize barcode detector: {e}")
        
        # Initialize other detectors when available
        # try:
        #     phone_config = detector_configs.get('phone', {})
        #     self.detectors['phone'] = PhoneDetector(phone_config)
        #     logger.info("Phone detector initialized")
        # except Exception as e:
        #     logger.error(f"Failed to initialize phone detector: {e}")
        
        # try:
        #     box_config = detector_configs.get('box', {})
        #     self.detectors['box'] = YellowBoxDetector(box_config)
        #     logger.info("Yellow box detector initialized")
        # except Exception as e:
        #     logger.error(f"Failed to initialize yellow box detector: {e}")
        
        logger.info(f"Multi-detector manager initialized with {len(self.detectors)} detectors")
    
    def detect_all(self, image: np.ndarray, enabled_types: List[str] = None) -> Dict[str, Any]:
        """
        Run all enabled detectors on the given image
        
        Args:
            image: Input image as numpy array (BGR format)
            enabled_types: List of detector types to run (None for all)
        
        Returns:
            Dictionary containing all detection results and summary
        """
        if enabled_types is None:
            enabled_types = list(self.detectors.keys())
        
        start_time = time.time()
        all_detections = []
        detection_summary = {}
        detector_results = {}
        
        if self.config.get('enable_parallel', True) and len(enabled_types) > 1:
            # Run detectors in parallel
            detector_results = self._run_detectors_parallel(image, enabled_types)
        else:
            # Run detectors sequentially
            detector_results = self._run_detectors_sequential(image, enabled_types)
        
        # Process results from each detector
        for detector_type, result in detector_results.items():
            if result['success']:
                detections = result['detections']
                
                # Add detector type to each detection
                for detection in detections:
                    detection['detector_type'] = detector_type
                
                all_detections.extend(detections)
                detection_summary[f'{detector_type}_count'] = len(detections)
                detection_summary[f'{detector_type}_time_ms'] = result['processing_time_ms']
            else:
                detection_summary[f'{detector_type}_error'] = result['error']
        
        # Apply non-maximum suppression to reduce overlapping detections
        all_detections = self._apply_non_maximum_suppression(all_detections)
        
        # Calculate summary statistics
        total_processing_time = (time.time() - start_time) * 1000
        detection_summary.update({
            'total_count': len(all_detections),
            'total_processing_time_ms': total_processing_time,
            'detection_types_used': enabled_types,
            'detection_types_available': list(self.detectors.keys())
        })
        
        return {
            'detections': all_detections,
            'summary': detection_summary,
            'detector_results': detector_results
        }
    
    def _run_detectors_parallel(self, image: np.ndarray, enabled_types: List[str]) -> Dict[str, Dict[str, Any]]:
        """Run detectors in parallel using ThreadPoolExecutor"""
        results = {}
        max_workers = min(self.config.get('max_workers', 4), len(enabled_types))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit detector tasks
            future_to_detector = {
                executor.submit(self._run_single_detector, detector_type, image): detector_type
                for detector_type in enabled_types
                if detector_type in self.detectors
            }
            
            # Collect results
            for future in as_completed(future_to_detector):
                detector_type = future_to_detector[future]
                try:
                    result = future.result(timeout=30)  # 30 second timeout per detector
                    results[detector_type] = result
                except Exception as e:
                    logger.error(f"Parallel detection error for {detector_type}: {e}")
                    results[detector_type] = {
                        'success': False,
                        'error': str(e),
                        'detections': [],
                        'processing_time_ms': 0
                    }
        
        return results
    
    def _run_detectors_sequential(self, image: np.ndarray, enabled_types: List[str]) -> Dict[str, Dict[str, Any]]:
        """Run detectors sequentially"""
        results = {}
        
        for detector_type in enabled_types:
            if detector_type in self.detectors:
                result = self._run_single_detector(detector_type, image)
                results[detector_type] = result
        
        return results
    
    def update_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Update detection thresholds for specific detectors"""
        for detector_type, threshold in thresholds.items():
            if detector_type in self.detectors:
                try:
                    detector = self.detectors[detector_type]
                    if hasattr(detector, 'set_threshold'):
                        detector.set_threshold(threshold)
                        logger.info(f"Updated {detector_type} threshold to {threshold}")
                    else:
                        logger.warning(f"Detector {detector_type} doesn't support threshold updates")
                except Exception as e:
                    logger.error(f"Failed to update threshold for {detector_type}: {e}")
    
    def _run_single_detector(self, detector_type: str, image: np.ndarray) -> Dict[str, Any]:
        """Run a single detector and return results"""
        start_time = time.time()
        
        try:
            detector = self.detectors[detector_type]
            detections = detector.detect(image)
            processing_time = (time.time() - start_time) * 1000
            
            logger.debug(f"{detector_type} detector: {len(detections)} detections in {processing_time:.1f}ms")
            
            return {
                'success': True,
                'detections': detections,
                'processing_time_ms': processing_time,
                'detector_info': detector.get_info()
            }
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Error in {detector_type} detector: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'detections': [],
                'processing_time_ms': processing_time
            }
    
    def detect_single_type(self, image: np.ndarray, detector_type: str) -> Dict[str, Any]:
        """
        Run a single detector type
        
        Args:
            image: Input image as numpy array
            detector_type: Type of detector to run
        
        Returns:
            Detection results for the specified detector
        """
        if detector_type not in self.detectors:
            raise DetectorError(f"Detector '{detector_type}' not available")
        
        return self._run_single_detector(detector_type, image)
    
    def _apply_non_maximum_suppression(self, detections: List[Dict[str, Any]], 
                                      iou_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Apply non-maximum suppression to reduce overlapping detections
        
        Args:
            detections: List of detection dictionaries
            iou_threshold: Intersection over Union threshold for suppression
        
        Returns:
            Filtered list of detections
        """
        if len(detections) <= 1:
            return detections
        
        # Group detections by type (don't suppress different types)
        detections_by_type = {}
        for detection in detections:
            det_type = detection.get('type', 'unknown')
            if det_type not in detections_by_type:
                detections_by_type[det_type] = []
            detections_by_type[det_type].append(detection)
        
        # Apply NMS within each type group
        filtered_detections = []
        for det_type, type_detections in detections_by_type.items():
            if len(type_detections) <= 1:
                filtered_detections.extend(type_detections)
                continue
            
            # Sort by confidence (highest first)
            type_detections.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Apply NMS
            keep_indices = []
            for i, detection in enumerate(type_detections):
                if i in keep_indices:
                    continue
                
                keep_indices.append(i)
                
                # Check remaining detections
                for j in range(i + 1, len(type_detections)):
                    if j in keep_indices:
                        continue
                    
                    iou = self._calculate_iou(detection['bbox'], type_detections[j]['bbox'])
                    if iou > iou_threshold:
                        keep_indices.append(j)
            
            # Keep detections with highest confidence for each overlapping group
            for idx in keep_indices:
                filtered_detections.append(type_detections[idx])
        
        return filtered_detections
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """
        Calculate Intersection over Union (IoU) for two bounding boxes
        
        Args:
            bbox1: [x1, y1, w1, h1]
            bbox2: [x2, y2, w2, h2]
        
        Returns:
            IoU value between 0.0 and 1.0
        """
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection rectangle
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right <= x_left or y_bottom <= y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        union_area = bbox1_area + bbox2_area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def get_available_detectors(self) -> List[str]:
        """Get list of available detector types"""
        return list(self.detectors.keys())
    
    def get_detector_info(self, detector_type: str = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get information about detectors
        
        Args:
            detector_type: Specific detector type (None for all)
        
        Returns:
            Detector information dictionary or list
        """
        if detector_type:
            if detector_type not in self.detectors:
                raise DetectorError(f"Detector '{detector_type}' not available")
            return self.detectors[detector_type].get_info()
        
        return [detector.get_info() for detector in self.detectors.values()]
    
    def add_detector(self, detector_type: str, detector: BaseDetector):
        """
        Add a new detector to the manager
        
        Args:
            detector_type: Type identifier for the detector
            detector: Detector instance
        """
        with self.detector_lock:
            self.detectors[detector_type] = detector
            logger.info(f"Added detector '{detector_type}' to manager")
    
    def remove_detector(self, detector_type: str) -> bool:
        """
        Remove a detector from the manager
        
        Args:
            detector_type: Type identifier for the detector to remove
        
        Returns:
            True if detector was removed, False if not found
        """
        with self.detector_lock:
            if detector_type in self.detectors:
                del self.detectors[detector_type]
                logger.info(f"Removed detector '{detector_type}' from manager")
                return True
            return False
    
    def test_detectors(self, test_image_path: str = None) -> Dict[str, Any]:
        """
        Test all available detectors
        
        Args:
            test_image_path: Path to test image (optional)
        
        Returns:
            Test results for all detectors
        """
        results = {}
        
        for detector_type, detector in self.detectors.items():
            try:
                if test_image_path:
                    # Test with image
                    import cv2
                    image = cv2.imread(test_image_path)
                    if image is not None:
                        test_result = self._run_single_detector(detector_type, image)
                        results[detector_type] = {
                            'status': 'success' if test_result['success'] else 'error',
                            'detections_count': len(test_result['detections']),
                            'processing_time_ms': test_result['processing_time_ms'],
                            'error': test_result.get('error')
                        }
                    else:
                        results[detector_type] = {
                            'status': 'error',
                            'error': f'Could not load test image: {test_image_path}'
                        }
                else:
                    # Test initialization only
                    test_result = detector.test_detector()
                    results[detector_type] = test_result
                    
            except Exception as e:
                results[detector_type] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return {
            'available_detectors': list(self.detectors.keys()),
            'test_results': results
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update manager configuration
        
        Args:
            new_config: New configuration dictionary
        """
        self.config.update(new_config)
        logger.info(f"Updated multi-detector configuration: {new_config}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics for the detector manager
        
        Returns:
            Statistics dictionary
        """
        return {
            'available_detectors': list(self.detectors.keys()),
            'config': self.config,
            'detector_count': len(self.detectors),
            'parallel_processing_enabled': self.config.get('enable_parallel', True),
            'max_workers': self.config.get('max_workers', 4)
        }