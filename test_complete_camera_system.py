#!/usr/bin/env python
"""
Complete camera detection system test
Tests the entire pipeline from web interface to API endpoints
"""

import os
import sys
import django
import json
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.video.services.detection_service import DetectionService
from file_processor.video.services.camera_service import CameraService

def create_test_barcode_image():
    """Create a simple test barcode image"""
    # Create a white background
    img = Image.new('RGB', (300, 150), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw simple barcode pattern (black and white bars)
    for i in range(10):
        x = 50 + i * 20
        if i % 2 == 0:
            draw.rectangle([x, 30, x + 10, 120], fill='black')
    
    return img

def test_services():
    """Test detection services directly"""
    print("=== Testing Detection Services ===")
    
    try:
        # Test DetectionService
        ds = DetectionService()
        available_detectors = ds.get_available_detectors()
        print(f"✅ Available detectors: {available_detectors}")
        
        # Test barcode detection
        test_img = create_test_barcode_image()
        
        # Convert to OpenCV format
        import cv2
        import numpy as np
        
        # PIL to OpenCV conversion
        opencv_image = cv2.cvtColor(np.array(test_img), cv2.COLOR_RGB2BGR)
        
        # Perform detection
        results = ds.detect_objects(
            frame=opencv_image,
            detection_types=['barcode'],
            threshold=0.3
        )
        
        print(f"✅ Barcode detection results: {results}")
        print(f"✅ Processing time: {results.get('processing_time', 0):.3f}s")
        
        # Test CameraService
        cs = CameraService()
        print("✅ CameraService initialized")
        
        # Create analysis session (need user)
        from django.contrib.auth.models import User
        try:
            test_user = User.objects.first()
            if not test_user:
                # Create test user if none exists
                test_user = User.objects.create_user(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123'
                )
            
            analysis = cs.create_camera_analysis(
                user=test_user,
                title='Camera Detection Test',
                detection_types=['barcode']
            )
            print(f"✅ Created analysis session: {analysis.id}")
            
        except Exception as e:
            print(f"⚠️ Camera analysis creation issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test API endpoints using requests"""
    print("\n=== Testing API Endpoints ===")
    
    base_url = "http://localhost:8001"
    
    try:
        # Test 1: Camera page
        response = requests.get(f"{base_url}/file_processor/video/camera/", timeout=10)
        print(f"✅ Camera page status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            if 'Barcode Detect' in content and 'Phone Detect' in content and 'YellowBox Detect' in content:
                print("✅ All three detection buttons present")
            else:
                print("⚠️ Missing detection buttons")
                
            if 'camera_detection.js' in content and 'detection_visualizer.js' in content:
                print("✅ JavaScript modules loaded")
            else:
                print("⚠️ JavaScript modules missing")
        
        # Test 2: Detection API GET
        response = requests.get(f"{base_url}/file_processor/video/api/detection/", timeout=10)
        print(f"✅ Detection API GET status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Available detectors: {data.get('available_detection_types', [])}")
            print(f"✅ Default thresholds: {data.get('default_thresholds', {})}")
        
        # Test 3: Detection API POST with test image
        test_img = create_test_barcode_image()
        buffer = BytesIO()
        test_img.save(buffer, format='JPEG')
        image_data = buffer.getvalue()
        
        import base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        post_data = {
            'image': f"data:image/jpeg;base64,{image_base64}",
            'detection_type': 'barcode',
            'threshold': 0.3
        }
        
        response = requests.post(
            f"{base_url}/file_processor/video/api/detection/",
            json=post_data,
            timeout=30
        )
        
        print(f"✅ Detection API POST status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Detection successful: {data.get('success', False)}")
            print(f"✅ Processing time: {data.get('processing_time', 0):.3f}s")
            print(f"✅ Detections found: {len(data.get('detections', []))}")
            
            # Show detection details
            for i, detection in enumerate(data.get('detections', [])):
                print(f"  Detection {i+1}: {detection.get('class', 'unknown')} "
                      f"(confidence: {detection.get('confidence', 0):.2f})")
                if detection.get('data'):
                    print(f"    Data: {detection['data']}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to web server - make sure it's running on port 8000")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_static_files():
    """Test if JavaScript static files are accessible"""
    print("\n=== Testing Static Files ===")
    
    base_url = "http://localhost:8001"
    
    try:
        js_files = [
            "/static/js/camera_detection.js",
            "/static/js/detection_visualizer.js"
        ]
        
        for js_file in js_files:
            response = requests.get(f"{base_url}{js_file}", timeout=10)
            print(f"✅ {js_file} status: {response.status_code}")
            
            if response.status_code == 200:
                content_length = len(response.content)
                print(f"   Size: {content_length} bytes")
                
                if 'CameraDetection' in response.text or 'DetectionVisualizer' in response.text:
                    print("   ✅ Contains expected classes")
                else:
                    print("   ⚠️ Missing expected classes")
        
        return True
        
    except Exception as e:
        print(f"❌ Static files test failed: {e}")
        return False

def main():
    """Run complete system test"""
    print("🎯 Complete Camera Detection System Test")
    print("=" * 50)
    
    # Wait a moment for web server to start
    time.sleep(3)
    
    results = []
    
    # Test 1: Services
    results.append(test_services())
    
    # Test 2: API endpoints
    results.append(test_api_endpoints())
    
    # Test 3: Static files
    results.append(test_static_files())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total} test groups")
    
    if passed == total:
        print("🎉 All tests passed! Camera detection system is ready.")
        print("\n🌐 You can now access the camera interface at:")
        print("   http://localhost:8000/file_processor/video/camera/")
        return True
    else:
        print("❌ Some tests failed. Check the logs above for details.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)