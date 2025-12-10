"""
Barcode detector implementation using pyzbar library
Supports 1D and 2D barcode detection including EAN-13, UPC-A, Code 128, QR Code, Data Matrix
"""
import logging
from typing import List, Dict, Any
import cv2
import numpy as np

from .base import BaseDetector, DetectorInitializationError, DetectionError

logger = logging.getLogger(__name__)

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar library not available. Barcode detection will not work.")


class BarcodeDetector(BaseDetector):
    """
    Barcode detector implementation using pyzbar library
    
    Supports detection of:
    - 1D barcodes: EAN-13, UPC-A, UPC-E, Code 39, Code 128, ITF
    - 2D barcodes: QR Code, Data Matrix, PDF417, Aztec
    """
    
    name = "barcode_detector"
    version = "1.0.0"
    description = "Barcode detection using pyzbar library"
    supported_formats = ['jpg', 'jpeg', 'png', 'bmp']
    
    # Supported barcode types mapping
    BARCODE_TYPES = {
        'CODE128': 'Code 128',
        'CODE39': 'Code 39',
        'CODE93': 'Code 93',
        'EAN13': 'EAN-13',
        'EAN8': 'EAN-8',
        'UPCA': 'UPC-A',
        'UPCE': 'UPC-E',
        'I25': 'Interleaved 2 of 5',
        'DATABAR': 'GS1 DataBar',
        'DATABAR_EXP': 'GS1 DataBar Expanded',
        'QRCODE': 'QR Code',
        'DATAMATRIX': 'Data Matrix',
        'PDF417': 'PDF417',
        'AZTEC': 'Aztec'
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize barcode detector
        
        Args:
            config: Configuration dictionary with options:
                - min_confidence: Minimum confidence threshold (default: 0.5)
                - max_barcodes: Maximum number of barcodes to detect (default: 10)
                - enable_preprocessing: Enable image preprocessing (default: True)
                - debug_mode: Enable debug logging (default: False)
        """
        self.config = {
            'min_confidence': 0.3,  # Lowered to accommodate QR codes with calculated confidence
            'max_barcodes': 10,
            'enable_preprocessing': True,
            'debug_mode': False,
            **(config or {})
        }
        
        super().__init__(self.config)
    
    def _initialize_detector(self):
        """Initialize pyzbar detector"""
        if not PYZBAR_AVAILABLE:
            raise DetectorInitializationError(
                "pyzbar library is not installed. Install it with: pip install pyzbar"
            )
        
        self.logger.info("Barcode detector initialized successfully")
        
        if self.config.get('debug_mode', False):
            self.logger.setLevel(logging.DEBUG)
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image to improve barcode detection
        
        Args:
            image: Input image in BGR format
        
        Returns:
            Preprocessed image
        """
        if not self.config.get('enable_preprocessing', True):
            return image
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply adaptive histogram equalization to improve contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Apply median blur to reduce noise
        gray = cv2.medianBlur(gray, 3)
        
        # Apply sharpening kernel
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        gray = cv2.filter2D(gray, -1, kernel)
        
        return gray
    
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect barcodes in the given image
        
        Args:
            image: Input image as numpy array (BGR format)
        
        Returns:
            List of barcode detection results
        """
        try:
            if not PYZBAR_AVAILABLE:
                self.logger.error("pyzbar not available for barcode detection")
                return []
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Detect barcodes using pyzbar
            barcodes = pyzbar.decode(processed_image)
            
            self.logger.debug(f"Found {len(barcodes)} potential barcodes")
            
            # Convert pyzbar results to standardized format
            detections = []
            for barcode in barcodes:
                detection = self._convert_to_standard_format(barcode, image.shape)
                if detection:
                    detections.append(detection)
            
            # Limit number of detections
            max_barcodes = self.config.get('max_barcodes', 10)
            if len(detections) > max_barcodes:
                # Sort by confidence and keep top N
                detections.sort(key=lambda x: x['confidence'], reverse=True)
                detections = detections[:max_barcodes]
                self.logger.debug(f"Limited detections to {max_barcodes} barcodes")
            
            # Post-process detections
            detections = self.post_process_detections(detections)
            
            self.logger.info(f"Successfully detected {len(detections)} barcodes")
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during barcode detection: {e}")
            raise DetectionError(f"Barcode detection failed: {str(e)}")
    
    def _convert_to_standard_format(self, barcode, image_shape: tuple) -> Dict[str, Any]:
        """
        Convert pyzbar barcode result to standard format
        
        Args:
            barcode: pyzbar barcode object
            image_shape: Shape of original image (height, width, channels)
        
        Returns:
            Standardized detection dictionary
        """
        try:
            # Extract barcode information
            barcode_type = barcode.type
            barcode_data = barcode.data.decode('utf-8') if barcode.data else ""
            
            # Get bounding box
            rect = barcode.rect
            x, y, w, h = rect.left, rect.top, rect.width, rect.height
            
            # Calculate quality metrics for confidence
            confidence = self._calculate_confidence(barcode, image_shape)
            
            # Get polygon points if available
            polygon_points = None
            if barcode.polygon:
                polygon_points = [(point.x, point.y) for point in barcode.polygon]
            
            # Create standardized detection
            detection = self.create_detection(
                type_name='barcode',
                class_name=self.BARCODE_TYPES.get(barcode_type, barcode_type),
                confidence=confidence,
                bbox=[x, y, w, h],
                data={
                    'content': barcode_data,
                    'format': barcode_type,
                    'format_name': self.BARCODE_TYPES.get(barcode_type, barcode_type),
                    'quality': getattr(barcode, 'quality', None),
                    'polygon_points': polygon_points,
                    'rect': {
                        'x': x, 'y': y, 'width': w, 'height': h
                    }
                }
            )
            
            self.logger.debug(f"Detected {barcode_type} barcode: '{barcode_data}' with confidence {confidence:.2f}")
            return detection
            
        except Exception as e:
            self.logger.warning(f"Error converting barcode to standard format: {e}")
            return None
    
    def _calculate_confidence(self, barcode, image_shape: tuple) -> float:
        """
        Calculate confidence score for barcode detection
        
        Args:
            barcode: pyzbar barcode object
            image_shape: Shape of original image
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidence = 0.8  # Base confidence for detected barcodes
            
            # Adjust confidence based on barcode quality if available
            if hasattr(barcode, 'quality') and barcode.quality is not None:
                quality_factor = min(barcode.quality / 100.0, 1.0)
                confidence *= (0.5 + 0.5 * quality_factor)
            
            # Adjust confidence based on barcode size
            rect = barcode.rect
            image_area = image_shape[0] * image_shape[1]
            barcode_area = rect.width * rect.height
            size_factor = min(barcode_area / image_area, 0.1) * 10  # Scale to 0-1 range
            
            if size_factor < 0.01:  # Very small barcode
                confidence *= 0.7
            elif size_factor > 0.5:  # Very large barcode
                confidence *= 0.9
            
            # Adjust confidence based on barcode type (some types are more reliable)
            type_confidence = {
                'QRCODE': 0.95,
                'DATAMATRIX': 0.90,
                'CODE128': 0.85,
                'EAN13': 0.90,
                'UPCA': 0.85
            }
            
            type_multiplier = type_confidence.get(barcode.type, 0.80)
            confidence *= type_multiplier
            
            # Ensure confidence is within valid range
            return min(max(confidence, 0.0), 1.0)
            
        except Exception as e:
            self.logger.warning(f"Error calculating confidence: {e}")
            return 0.5  # Return default confidence
    
    def _apply_detector_post_processing(self, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply barcode-specific post-processing
        
        Args:
            detection: Detection dictionary
        
        Returns:
            Post-processed detection
        """
        # Add barcode data validation
        barcode_data = detection['data']['content']
        
        # Validate barcode content based on type
        barcode_type = detection['data']['format']
        validated_data = self._validate_barcode_content(barcode_data, barcode_type)
        detection['data']['validated_content'] = validated_data
        
        # Add readability score
        detection['data']['readability_score'] = self._calculate_readability_score(barcode_data)
        
        # Add data length information
        detection['data']['data_length'] = len(barcode_data)
        
        return detection
    
    def _validate_barcode_content(self, content: str, barcode_type: str) -> Dict[str, Any]:
        """
        Validate barcode content based on type
        
        Args:
            content: Decoded barcode content
            barcode_type: Type of barcode
        
        Returns:
            Validation result dictionary
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not content:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Empty barcode content')
            return validation_result
        
        # Type-specific validation
        if barcode_type in ['EAN13', 'UPCA']:
            # Should be numeric and specific length
            if not content.isdigit():
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'{barcode_type} should contain only digits')
            
            expected_length = 12 if barcode_type == 'UPCA' else 13
            if len(content) != expected_length:
                validation_result['warnings'].append(f'{barcode_type} expected length {expected_length}, got {len(content)}')
        
        elif barcode_type == 'QRCODE':
            # QR codes can contain any data, but check for common patterns
            if content.startswith('http://') or content.startswith('https://'):
                validation_result['data_type'] = 'URL'
            elif content.startswith('WIFI:'):
                validation_result['data_type'] = 'WiFi Configuration'
            elif '@' in content and '.' in content:
                validation_result['data_type'] = 'Email Address'
            else:
                validation_result['data_type'] = 'Text'
        
        elif barcode_type == 'CODE128':
            # Code 128 can contain various data types
            validation_result['data_type'] = 'General Purpose'
        
        return validation_result
    
    def _calculate_readability_score(self, content: str) -> float:
        """
        Calculate readability score for barcode content
        
        Args:
            content: Barcode content string
        
        Returns:
            Readability score between 0.0 and 1.0
        """
        if not content:
            return 0.0
        
        score = 1.0
        
        # Penalize very long content (harder to display)
        if len(content) > 100:
            score -= 0.2
        elif len(content) > 50:
            score -= 0.1
        
        # Penalize content with only special characters
        if not any(c.isalnum() for c in content):
            score -= 0.3
        
        # Bonus for readable text content
        if content.replace('-', '').replace('_', '').isalnum():
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def get_supported_types(self) -> List[str]:
        """
        Get list of supported barcode types
        
        Returns:
            List of supported barcode type names
        """
        return list(self.BARCODE_TYPES.keys())
    
    def get_type_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for supported barcode types
        
        Returns:
            Dictionary mapping type codes to descriptions
        """
        return self.BARCODE_TYPES.copy()