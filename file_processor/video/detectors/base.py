"""
Base detector abstract class for video object detection
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Optional
import numpy as np

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """
    Abstract base class for all video object detectors
    
    This class defines the common interface that all detectors must implement,
    ensuring consistent behavior and standardized output formats across different
    detection algorithms.
    """
    
    # Class attributes that should be overridden by subclasses
    name = None
    version = "1.0.0"
    description = "Base detector class"
    supported_formats = ['jpg', 'jpeg', 'png', 'bmp']
    capabilities = {}
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the detector with optional configuration
        
        Args:
            config: Dictionary containing detector-specific configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialize_detector()
    
    @abstractmethod
    def _initialize_detector(self):
        """
        Initialize the underlying detection model/library
        Must be implemented by each detector subclass
        """
        pass
    
    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Perform object detection on an image
        
        Args:
            image: Input image as numpy array (BGR format for OpenCV compatibility)
        
        Returns:
            List of detection results, each containing:
            - type: str - detection type (e.g., 'barcode', 'phone', 'box')
            - class: str - specific class name
            - confidence: float - confidence score (0.0 to 1.0)
            - bbox: list - [x, y, width, height] bounding box
            - data: dict - additional detection-specific data
        """
        pass
    
    def detect_from_bytes(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Perform object detection on image bytes
        
        Args:
            image_bytes: Raw image data as bytes
        
        Returns:
            List of detection results
        """
        try:
            import cv2
            import numpy as np
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                self.logger.error("Failed to decode image from bytes")
                return []
            
            return self.detect(image)
            
        except Exception as e:
            self.logger.error(f"Error processing image bytes: {e}")
            return []
    
    def validate_detection(self, detection: Dict[str, Any]) -> bool:
        """
        Validate a detection result meets minimum requirements
        
        Args:
            detection: Detection dictionary
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['type', 'class', 'confidence', 'bbox', 'data']
        
        for field in required_fields:
            if field not in detection:
                self.logger.warning(f"Detection missing required field: {field}")
                return False
        
        # Validate confidence
        confidence = detection['confidence']
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            self.logger.warning(f"Invalid confidence value: {confidence}")
            return False
        
        # Validate bounding box
        bbox = detection['bbox']
        if not isinstance(bbox, list) or len(bbox) != 4:
            self.logger.warning(f"Invalid bbox format: {bbox}")
            return False
        
        x, y, w, h = bbox
        if not all(isinstance(v, (int, float)) for v in [x, y, w, h]):
            self.logger.warning(f"Invalid bbox values: {bbox}")
            return False
        
        if w <= 0 or h <= 0:
            self.logger.warning(f"Invalid bbox dimensions: {bbox}")
            return False
        
        return True
    
    def post_process_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post-process detection results to ensure consistency and quality
        
        Args:
            detections: Raw detection results
        
        Returns:
            Processed and validated detections
        """
        processed = []
        
        for detection in detections:
            # Apply minimum confidence threshold
            min_confidence = self.config.get('min_confidence', 0.5)
            if detection['confidence'] < min_confidence:
                continue
            
            # Validate detection format
            if not self.validate_detection(detection):
                continue
            
            # Apply detector-specific post-processing
            detection = self._apply_detector_post_processing(detection)
            
            processed.append(detection)
        
        return processed
    
    def _apply_detector_post_processing(self, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply detector-specific post-processing
        Can be overridden by subclasses
        
        Args:
            detection: Detection dictionary
        
        Returns:
            Post-processed detection
        """
        return detection
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get detector information
        
        Returns:
            Dictionary with detector metadata
        """
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'supported_formats': self.supported_formats,
            'capabilities': self.capabilities,
            'config': self.config
        }
    
    def test_detector(self, test_image_path: str = None) -> Dict[str, Any]:
        """
        Test detector functionality
        
        Args:
            test_image_path: Path to test image (optional)
        
        Returns:
            Test results dictionary
        """
        try:
            if test_image_path:
                import cv2
                image = cv2.imread(test_image_path)
                if image is None:
                    return {
                        'status': 'error',
                        'message': f'Could not load test image: {test_image_path}'
                    }
                
                detections = self.detect(image)
                return {
                    'status': 'success',
                    'detections_count': len(detections),
                    'detections': detections[:5],  # Return first 5 detections
                    'message': 'Detector test completed successfully'
                }
            else:
                # No test image provided, just check if detector initializes properly
                return {
                    'status': 'success',
                    'message': f'Detector {self.name} initialized successfully',
                    'info': self.get_info()
                }
                
        except Exception as e:
            self.logger.error(f"Error testing detector: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @staticmethod
    def create_detection(type_name: str, class_name: str, confidence: float,
                         bbox: List[float], data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Helper method to create a standardized detection dictionary
        
        Args:
            type_name: Detection type (e.g., 'barcode', 'phone')
            class_name: Specific class name
            confidence: Confidence score (0.0 to 1.0)
            bbox: Bounding box [x, y, width, height]
            data: Additional detection data
        
        Returns:
            Standardized detection dictionary
        """
        return {
            'type': type_name,
            'class': class_name,
            'confidence': float(confidence),
            'bbox': [float(x) for x in bbox],
            'data': data or {}
        }


class DetectorError(Exception):
    """Base exception for detector-related errors"""
    pass


class DetectorInitializationError(DetectorError):
    """Raised when detector fails to initialize"""
    pass


class DetectionError(DetectorError):
    """Raised when detection process fails"""
    pass