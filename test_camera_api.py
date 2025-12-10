#!/usr/bin/env python
"""
Test script for camera detection API endpoints
"""

import os
import sys
import django
import json
import base64
import io
from PIL import Image
import numpy as np

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from django.test import Client
from django.conf import settings

def test_detection_api():
    """Test detection API endpoints"""
    
    # Temporarily update ALLOWED_HOSTS
    original_allowed_hosts = settings.ALLOWED_HOSTS
    settings.ALLOWED_HOSTS = ['*']
    
    try:
        client = Client()
        
        print("=== Testing Detection API ===")
        
        # Test 1: GET request - get configuration
        print("\n1. Testing GET /api/detection/ (get config)")
        response = client.get('/file_processor/video/api/detection/')
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"✅ GET Status: {response.status_code}")
            print(f"✅ Available detectors: {data.get('available_detection_types', [])}")
            print(f"✅ Default thresholds: {data.get('default_thresholds', {})}")
            print(f"✅ Service status: {data.get('service_status', 'unknown')}")
        else:
            print(f"❌ GET failed with status {response.status_code}")
            print(f"Response: {response.content[:200]}...")
            return False
        
        # Test 2: POST request - barcode detection with test image
        print("\n2. Testing POST /api/detection/ (barcode detection)")
        
        # Create a simple test image with barcode-like pattern
        test_image = Image.new('RGB', (200, 100), color='white')
        # Add some black bars to simulate a barcode
        for i in range(0, 200, 10):
            for y in range(20, 80):
                test_image.putpixel((i, y), (0, 0, 0))
        
        # Convert to base64
        buffer = io.BytesIO()
        test_image.save(buffer, format='JPEG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        image_base64 = f"data:image/jpeg;base64,{image_data}"
        
        post_data = {
            'image': image_base64,
            'detection_type': 'barcode',
            'threshold': 0.3
        }
        
        response = client.post(
            '/file_processor/video/api/detection/',
            data=json.dumps(post_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"✅ POST Status: {response.status_code}")
            print(f"✅ Detection successful: {data.get('success', False)}")
            print(f"✅ Processing time: {data.get('processing_time', 0):.3f}s")
            print(f"✅ Detections found: {len(data.get('detections', []))}")
            
            # Print detection details
            for i, detection in enumerate(data.get('detections', [])):
                print(f"  Detection {i+1}: {detection.get('class', 'unknown')} (confidence: {detection.get('confidence', 0):.2f})")
                if detection.get('data'):
                    print(f"    Data: {detection['data']}")
        else:
            print(f"❌ POST failed with status {response.status_code}")
            print(f"Response: {response.content[:200]}...")
            return False
        
        # Test 3: Test snapshot capture
        print("\n3. Testing POST /api/capture-snapshot/ (save snapshot)")
        
        snapshot_data = {
            'image': image_base64,
            'detections': data.get('detections', []),
            'detection_type': 'barcode',
            'threshold': 0.3,
            'timestamp': '2025-12-09T12:00:00Z'
        }
        
        response = client.post(
            '/file_processor/video/api/capture-snapshot/',
            data=json.dumps(snapshot_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            result = json.loads(response.content)
            print(f"✅ Snapshot Status: {response.status_code}")
            print(f"✅ Snapshot saved: {result.get('success', False)}")
            print(f"✅ Analysis ID: {result.get('analysis_id', 'N/A')}")
        else:
            print(f"❌ Snapshot failed with status {response.status_code}")
            print(f"Response: {response.content[:200]}...")
        
        # Test 4: Test detection history
        print("\n4. Testing GET /api/detection-history/ (get history)")
        
        response = client.get('/file_processor/video/api/detection-history/')
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f"✅ History Status: {response.status_code}")
            print(f"✅ Total history items: {data.get('total_count', 0)}")
            print(f"✅ History returned: {len(data.get('history', []))} items")
        else:
            print(f"❌ History failed with status {response.status_code}")
            print(f"Response: {response.content[:200]}...")
        
        print("\n=== All API Tests Completed ===")
        return True
        
    except Exception as e:
        print(f"❌ API test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Restore original ALLOWED_HOSTS
        settings.ALLOWED_HOSTS = original_allowed_hosts


if __name__ == '__main__':
    success = test_detection_api()
    sys.exit(0 if success else 1)