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
        logger.debug(f"[BARCODE_DETECT] Starting image preprocessing - input shape: {image.shape}, dtype: {image.dtype}")
        
        if not self.config.get('enable_preprocessing', True):
            logger.debug(f"[BARCODE_DETECT] Preprocessing disabled, returning original image")
            return image
        
        # Convert to grayscale
        if len(image.shape) == 3:
            logger.debug(f"[BARCODE_DETECT] Converting BGR to grayscale - input channels: {image.shape[2]}")
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            logger.debug(f"[BARCODE_DETECT] Grayscale conversion completed - shape: {gray.shape}")
        else:
            logger.debug(f"[BARCODE_DETECT] Image already grayscale")
            gray = image
        
        # Apply adaptive histogram equalization to improve contrast
        logger.debug(f"[BARCODE_DETECT] Applying CLAHE - clipLimit: 2.0, tileGridSize: (8, 8)")
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        logger.debug(f"[BARCODE_DETECT] CLAHE applied - output range: [{gray.min()}, {gray.max()}]")
        
        # Apply median blur to reduce noise
        logger.debug(f"[BARCODE_DETECT] Applying median blur - kernel size: 3")
        gray = cv2.medianBlur(gray, 3)
        logger.debug(f"[BARCODE_DETECT] Median blur completed")
        
        # Apply sharpening kernel
        logger.debug(f"[BARCODE_DETECT] Applying sharpening kernel")
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        gray = cv2.filter2D(gray, -1, kernel)
        logger.debug(f"[BARCODE_DETECT] Sharpening applied - output range: [{gray.min()}, {gray.max()}]")
        
        logger.debug(f"[BARCODE_DETECT] Image preprocessing completed - final shape: {gray.shape}, dtype: {gray.dtype}")
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
            logger.debug(f"[BARCODE_DETECT] Starting barcode detection - Image shape: {image.shape}, dtype: {image.dtype}")
            
            if not PYZBAR_AVAILABLE:
                logger.debug(f"[BARCODE_DETECT] pyzbar not available for barcode detection")
                return []
            
            # Preprocess image
            logger.debug(f"[BARCODE_DETECT] Starting image preprocessing - enable_preprocessing: {self.config.get('enable_preprocessing', True)}")
            processed_image = self._preprocess_image(image)
            logger.debug(f"[BARCODE_DETECT] Image preprocessing completed - processed shape: {processed_image.shape}")
            
            # Detect barcodes using pyzbar
            logger.debug(f"[BARCODE_DETECT] Running pyzbar.decode on processed image")
            barcodes = pyzbar.decode(processed_image)
            
            logger.debug(f"[BARCODE_DETECT] Found {len(barcodes)} potential barcodes from pyzbar")
            
            # Convert pyzbar results to standardized format
            logger.debug(f"[BARCODE_DETECT] Converting {len(barcodes)} barcodes to standard format")
            detections = []
            for i, barcode in enumerate(barcodes):
                logger.debug(f"[BARCODE_DETECT] Processing barcode {i+1}/{len(barcodes)}")
                detection = self._convert_to_standard_format(barcode, image.shape)
                if detection:
                    detections.append(detection)
                    logger.debug(f"[BARCODE_DETECT] Successfully converted barcode {i+1} - type: {detection['class']}, confidence: {detection['confidence']:.3f}")
                else:
                    logger.debug(f"[BARCODE_DETECT] Failed to convert barcode {i+1} to standard format")
            
            # Limit number of detections
            max_barcodes = self.config.get('max_barcodes', 10)
            if len(detections) > max_barcodes:
                # Sort by confidence and keep top N
                detections.sort(key=lambda x: x['confidence'], reverse=True)
                logger.debug(f"[BARCODE_DETECT] Limiting detections from {len(detections)} to {max_barcodes} barcodes (highest confidence)")
                detections = detections[:max_barcodes]
            
            # Post-process detections
            logger.debug(f"[BARCODE_DETECT] Starting post-processing of {len(detections)} detections")
            detections = self.post_process_detections(detections)
            logger.debug(f"[BARCODE_DETECT] Post-processing completed - {len(detections)} final detections")
            
            logger.debug(f"[BARCODE_DETECT] Successfully detected {len(detections)} barcodes")
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
            logger.debug(f"[BARCODE_DETECT] Converting barcode to standard format - type: {barcode.type}")
            
            # Extract barcode information
            barcode_type = barcode.type
            barcode_data = barcode.data.decode('utf-8') if barcode.data else ""
            
            logger.debug(f"[BARCODE_DETECT] Extracted barcode info - type: {barcode_type}, data: '{barcode_data}', data_length: {len(barcode_data)}")
            
            # Get bounding box
            rect = barcode.rect
            x, y, w, h = rect.left, rect.top, rect.width, rect.height
            
            logger.debug(f"[BARCODE_DETECT] Bounding box - x: {x}, y: {y}, width: {w}, height: {h}")
            
            # Calculate quality metrics for confidence
            logger.debug(f"[BARCODE_DETECT] Calculating confidence for barcode")
            confidence = self._calculate_confidence(barcode, image_shape)
            
            logger.debug(f"[BARCODE_DETECT] Calculated confidence: {confidence:.3f}")
            
            # Get polygon points if available
            polygon_points = None
            if barcode.polygon:
                polygon_points = [(point.x, point.y) for point in barcode.polygon]
                logger.debug(f"[BARCODE_DETECT] Polygon points: {len(polygon_points)} points")
            else:
                logger.debug(f"[BARCODE_DETECT] No polygon points available")
            
            # Create standardized detection
            class_name = self.BARCODE_TYPES.get(barcode_type, barcode_type)
            logger.debug(f"[BARCODE_DETECT] Creating standardized detection - class_name: {class_name}")
            
            detection = self.create_detection(
                type_name='barcode',
                class_name=class_name,
                confidence=confidence,
                bbox=[x, y, w, h],
                data={
                    'content': barcode_data,
                    'format': barcode_type,
                    'format_name': class_name,
                    'quality': getattr(barcode, 'quality', None),
                    'polygon_points': polygon_points,
                    'rect': {
                        'x': x, 'y': y, 'width': w, 'height': h
                    }
                }
            )
            
            logger.debug(f"[BARCODE_DETECT] Successfully converted {barcode_type} barcode: '{barcode_data}' with confidence {confidence:.3f}")
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
            logger.debug(f"[BARCODE_DETECT] Calculating confidence for {barcode.type}")
            
            confidence = 0.8  # Base confidence for detected barcodes
            logger.debug(f"[BARCODE_DETECT] Base confidence: {confidence}")
            
            # Adjust confidence based on barcode quality if available
            if hasattr(barcode, 'quality') and barcode.quality is not None:
                quality_factor = min(barcode.quality / 100.0, 1.0)
                confidence *= (0.5 + 0.5 * quality_factor)
                logger.debug(f"[BARCODE_DETECT] Quality adjustment - quality: {barcode.quality}, factor: {quality_factor:.3f}, new_confidence: {confidence:.3f}")
            else:
                logger.debug(f"[BARCODE_DETECT] No quality information available")
            
            # Adjust confidence based on barcode size
            rect = barcode.rect
            image_area = image_shape[0] * image_shape[1]
            barcode_area = rect.width * rect.height
            size_factor = min(barcode_area / image_area, 0.1) * 10  # Scale to 0-1 range
            
            logger.debug(f"[BARCODE_DETECT] Size analysis - barcode_area: {barcode_area}, image_area: {image_area}, size_factor: {size_factor:.3f}")
            
            if size_factor < 0.01:  # Very small barcode
                confidence *= 0.7
                logger.debug(f"[BARCODE_DETECT] Very small barcode penalty applied - confidence: {confidence:.3f}")
            elif size_factor > 0.5:  # Very large barcode
                confidence *= 0.9
                logger.debug(f"[BARCODE_DETECT] Very large barcode penalty applied - confidence: {confidence:.3f}")
            else:
                logger.debug(f"[BARCODE_DETECT] Normal size barcode - no size penalty")
            
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
            logger.debug(f"[BARCODE_DETECT] Type adjustment - type: {barcode.type}, multiplier: {type_multiplier:.3f}, new_confidence: {confidence:.3f}")
            
            # Ensure confidence is within valid range
            final_confidence = min(max(confidence, 0.0), 1.0)
            logger.debug(f"[BARCODE_DETECT] Final confidence after clamping: {final_confidence:.3f}")
            
            return final_confidence
            
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
        logger.debug(f"[BARCODE_DETECT] Starting post-processing for detection - class: {detection['class']}")
        
        # Add barcode data validation
        barcode_data = detection['data']['content']
        logger.debug(f"[BARCODE_DETECT] Validating barcode content - data: '{barcode_data}'")
        
        # Validate barcode content based on type
        barcode_type = detection['data']['format']
        logger.debug(f"[BARCODE_DETECT] Validating content for barcode type: {barcode_type}")
        validated_data = self._validate_barcode_content(barcode_data, barcode_type)
        detection['data']['validated_content'] = validated_data
        logger.debug(f"[BARCODE_DETECT] Content validation completed - is_valid: {validated_data.get('is_valid', 'unknown')}")
        
        # Add readability score
        logger.debug(f"[BARCODE_DETECT] Calculating readability score")
        readability_score = self._calculate_readability_score(barcode_data)
        detection['data']['readability_score'] = readability_score
        logger.debug(f"[BARCODE_DETECT] Readability score: {readability_score:.3f}")
        
        # Add data length information
        detection['data']['data_length'] = len(barcode_data)
        logger.debug(f"[BARCODE_DETECT] Data length: {len(barcode_data)} characters")
        
        logger.debug(f"[BARCODE_DETECT] Post-processing completed for detection")
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
        logger.debug(f"[BARCODE_DETECT] Validating barcode content - type: {barcode_type}, content: '{content}'")
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not content:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Empty barcode content')
            logger.debug(f"[BARCODE_DETECT] Validation failed - empty content")
            return validation_result
        
        # Type-specific validation
        if barcode_type in ['EAN13', 'UPCA']:
            logger.debug(f"[BARCODE_DETECT] Validating numeric barcode type: {barcode_type}")
            # Should be numeric and specific length
            if not content.isdigit():
                validation_result['is_valid'] = False
                validation_result['errors'].append(f'{barcode_type} should contain only digits')
                logger.debug(f"[BARCODE_DETECT] Validation error - {barcode_type} contains non-numeric characters")
            
            expected_length = 12 if barcode_type == 'UPCA' else 13
            if len(content) != expected_length:
                validation_result['warnings'].append(f'{barcode_type} expected length {expected_length}, got {len(content)}')
                logger.debug(f"[BARCODE_DETECT] Validation warning - {barcode_type} length mismatch: expected {expected_length}, got {len(content)}")
            else:
                logger.debug(f"[BARCODE_DETECT] {barcode_type} length validation passed")
        
        elif barcode_type == 'QRCODE':
            logger.debug(f"[BARCODE_DETECT] Analyzing QR code content type")
            # QR codes can contain any data, but check for common patterns
            if content.startswith('http://') or content.startswith('https://'):
                validation_result['data_type'] = 'URL'
                logger.debug(f"[BARCODE_DETECT] QR code identified as URL")
            elif content.startswith('WIFI:'):
                validation_result['data_type'] = 'WiFi Configuration'
                logger.debug(f"[BARCODE_DETECT] QR code identified as WiFi Configuration")
            elif '@' in content and '.' in content:
                validation_result['data_type'] = 'Email Address'
                logger.debug(f"[BARCODE_DETECT] QR code identified as Email Address")
            else:
                validation_result['data_type'] = 'Text'
                logger.debug(f"[BARCODE_DETECT] QR code identified as general text")
        
        elif barcode_type == 'CODE128':
            # Code 128 can contain various data types
            validation_result['data_type'] = 'General Purpose'
            logger.debug(f"[BARCODE_DETECT] {barcode_type} classified as General Purpose")
        else:
            logger.debug(f"[BARCODE_DETECT] No specific validation rules for barcode type: {barcode_type}")
        
        logger.debug(f"[BARCODE_DETECT] Content validation completed - is_valid: {validation_result['is_valid']}, errors: {len(validation_result['errors'])}, warnings: {len(validation_result['warnings'])}")
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