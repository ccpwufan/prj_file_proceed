#!/usr/bin/env python3
"""
Test script for barcode detector functionality in Docker environment
"""
import os
import sys
import django
import logging
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_pyzbar_import():
    """Test if pyzbar can be imported"""
    try:
        from pyzbar import pyzbar
        logger.info("✅ pyzbar imported successfully")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import pyzbar: {e}")
        return False

def test_opencv_import():
    """Test if opencv can be imported"""
    try:
        import cv2
        import numpy as np
        logger.info(f"✅ OpenCV version: {cv2.__version__}")
        logger.info(f"✅ NumPy version: {np.__version__}")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import OpenCV/NumPy: {e}")
        return False

def test_detector_initialization():
    """Test barcode detector initialization"""
    try:
        from file_processor.video.detectors import BarcodeDetector
        
        # Create detector with default config
        detector = BarcodeDetector()
        logger.info("✅ BarcodeDetector initialized successfully")
        
        # Get detector info
        info = detector.get_info()
        logger.info(f"Detector info: {info}")
        
        return detector
    except Exception as e:
        logger.error(f"❌ Failed to initialize BarcodeDetector: {e}")
        return None

def test_detector_with_sample_image(detector):
    """Test detector with a sample image"""
    try:
        import cv2
        import numpy as np
        
        # Create a simple test image with a QR code pattern
        # First, create a basic QR code using qrcode library if available
        try:
            import qrcode
            
            # Generate a simple QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data('TEST_BARCODE_123')
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert PIL image to numpy array
            qr_img_array = np.array(qr_img)
            
            # Convert to uint8 if needed
            if qr_img_array.dtype == bool:
                qr_img_array = qr_img_array.astype(np.uint8) * 255
            
            # Ensure we have a proper 3-channel image
            if len(qr_img_array.shape) == 2:
                # Grayscale to BGR
                qr_img_cv2 = cv2.cvtColor(qr_img_array, cv2.COLOR_GRAY2BGR)
            else:
                # RGB/RGBA to BGR
                if qr_img_array.shape[2] >= 3:
                    qr_img_cv2 = qr_img_array[:, :, :3][:, :, ::-1]  # RGB to BGR
                else:
                    # Fallback to grayscale
                    qr_img_cv2 = cv2.cvtColor(qr_img_array, cv2.COLOR_GRAY2BGR)
            
            logger.info("✅ Test QR code generated successfully")
            
        except ImportError:
            logger.warning("qrcode library not available, creating simple test image")
            # Create a simple test image
            qr_img_cv2 = np.ones((200, 200, 3), dtype=np.uint8) * 255
            # Add some black rectangles to simulate barcode pattern
            qr_img_cv2[50:60, :] = 0  # Black line
            qr_img_cv2[70:80, :] = 0  # Black line
            qr_img_cv2[90:100, :] = 0  # Black line
        
        # Test detection
        detections = detector.detect(qr_img_cv2)
        
        logger.info(f"✅ Detection completed, found {len(detections)} barcodes")
        
        for i, detection in enumerate(detections):
            logger.info(f"Detection {i+1}: {detection}")
        
        return len(detections) > 0
        
    except Exception as e:
        logger.error(f"❌ Error during detection test: {e}")
        return False

def test_multi_detector_manager():
    """Test MultiTypeDetector manager"""
    try:
        from file_processor.video.detectors import MultiTypeDetector
        
        # Create manager
        manager = MultiTypeDetector()
        logger.info("✅ MultiTypeDetector initialized successfully")
        
        # Get available detectors
        available = manager.get_available_detectors()
        logger.info(f"Available detectors: {available}")
        
        # Get manager statistics
        stats = manager.get_statistics()
        logger.info(f"Manager statistics: {stats}")
        
        # Test detectors
        test_results = manager.test_detectors()
        logger.info(f"Detector test results: {test_results}")
        
        return manager
        
    except Exception as e:
        logger.error(f"❌ Error testing MultiTypeDetector: {e}")
        return None

def test_detection_service():
    """Test DetectionService integration"""
    try:
        from file_processor.video.services import DetectionService
        
        # Create service
        service = DetectionService()
        logger.info("✅ DetectionService initialized successfully")
        
        # Get available detectors
        available = service.get_available_detectors()
        logger.info(f"Available detectors in service: {available}")
        
        # Get detector info
        if 'barcode' in available:
            info = service.get_detector_info('barcode')
            logger.info(f"Barcode detector info: {info}")
        
        return service
        
    except Exception as e:
        logger.error(f"❌ Error testing DetectionService: {e}")
        return None

def test_video_processor():
    """Test VideoProcessor integration"""
    try:
        from file_processor.video.services import VideoProcessor
        
        # Create processor
        processor = VideoProcessor()
        logger.info("✅ VideoProcessor initialized successfully")
        
        # Check if detection service is available
        if hasattr(processor, 'detection_service') and processor.detection_service:
            logger.info("✅ Detection service is available in VideoProcessor")
        else:
            logger.warning("⚠️ Detection service not available in VideoProcessor")
        
        return processor
        
    except Exception as e:
        logger.error(f"❌ Error testing VideoProcessor: {e}")
        return None

def test_database_connection():
    """Test database connection and models"""
    try:
        from file_processor.video.models import VideoFile, VideoAnalysis, VideoDetectionFrame
        
        # Test database access (just check if models are accessible)
        logger.info("✅ Database models imported successfully")
        
        # Check if we can query the database
        video_count = VideoFile.objects.count()
        analysis_count = VideoAnalysis.objects.count()
        frame_count = VideoDetectionFrame.objects.count()
        
        logger.info(f"Database stats - Videos: {video_count}, Analyses: {analysis_count}, Frames: {frame_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting barcode detector tests in Docker environment")
    logger.info("=" * 60)
    
    tests = [
        ("Pyzbar Import", test_pyzbar_import),
        ("OpenCV Import", test_opencv_import),
        ("Database Connection", test_database_connection),
    ]
    
    # Run basic tests
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} test...")
        results[test_name] = test_func()
    
    # If basic tests pass, run more complex tests
    if all(results.values()):
        logger.info("\n" + "=" * 60)
        logger.info("📊 Basic tests passed, running advanced tests...")
        
        advanced_tests = [
            ("Detector Initialization", test_detector_initialization),
            ("MultiDetector Manager", test_multi_detector_manager),
            ("Detection Service", test_detection_service),
            ("Video Processor", test_video_processor),
        ]
        
        for test_name, test_func in advanced_tests:
            logger.info(f"\n🧪 Running {test_name} test...")
            try:
                result = test_func()
                results[test_name] = result is not None
                
                # If detector was created, test it with sample image
                if test_name == "Detector Initialization" and result:
                    logger.info("\n🧪 Running Sample Image Detection test...")
                    detection_result = test_detector_with_sample_image(result)
                    results["Sample Image Detection"] = detection_result
                    
            except Exception as e:
                logger.error(f"❌ {test_name} test failed: {e}")
                results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Barcode detector is ready for use.")
        return 0
    else:
        logger.error(f"💥 {total - passed} tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())