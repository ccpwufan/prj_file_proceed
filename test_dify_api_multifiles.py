#!/usr/bin/env python3
"""
Test script to verify Dify API connection
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from django.conf import settings
from file_processor.services import DifyAPIService
import requests
DIFY_API_KEY = settings.DIFY_API_KEY_INVICE_FILES

def test_dify_connection():
    """Test basic Dify API connection"""
    print("=== Dify API Connection Test ===")
    
    # Check environment variables

    print(f"DIFY_API_KEY: {'✓' if DIFY_API_KEY else '✗'}")
    print(f"DIFY_USER: {settings.DIFY_USER}")
    print(f"DIFY_SERVER: {settings.DIFY_SERVER}")
    
    if not DIFY_API_KEY:
        print("❌ DIFY_API_KEY not found in environment variables")
        return False
    
    # Test basic API connectivity
    try:
        service = DifyAPIService(DIFY_API_KEY)
        print(f"Service initialized with timeout: {service.timeout}s")
        
        # Test a simple API call (this might fail but will show connectivity)
        url = f"{settings.DIFY_SERVER}/v1/files/upload"
        headers = {'Authorization': f'Bearer {settings.DIFY_API_KEY}'}
        
        print(f"Testing connection to: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code in [200, 400, 401, 405]:  # Any response means connectivity is OK
            print("✅ Dify API is reachable")
            return True
        else:
            print(f"❌ Unexpected response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_image_file_access():
    """Test if we can access image files"""
    print("\n=== Image File Access Test ===")
    
    from file_processor.models import FileDetail
    
    images = FileDetail.objects.all()[:3]  # Test first 3 images
    
    if not images:
        print("❌ No images found in database")
        return False
    
    for image in images:
        print(f"Testing image: {image}")
        print(f"File path: {image.file_detail_filename.path}")
        
        if os.path.exists(image.file_detail_filename.path):
            file_size = os.path.getsize(image.file_detail_filename.path)
            print(f"✅ File exists, size: {file_size} bytes")
        else:
            print(f"❌ File not found: {image.file_detail_filename.path}")
            return False
    
    return True

def test_multiple_image_upload():
    """Test multiple image upload functionality"""
    print("\n=== Multiple Image Upload Test ===")
    
    from file_processor.models import FileDetail
    
    images = FileDetail.objects.all()[:2]
    
    if len(images) < 2:
        print("❌ Need at least 2 images for multiple upload test")
        return False
    
    try:
        service = DifyAPIService(DIFY_API_KEY)
        
        image_paths = [img.file_detail_filename.path for img in images]
        print(f"Testing upload of {len(image_paths)} images")
        
        file_ids = service.upload_multiple_images(image_paths)
        print(f"✅ Successfully uploaded {len(file_ids)} images")
        print(f"File IDs: {file_ids}")
        
        return True
        
    except Exception as e:
        print(f"❌ Multiple upload failed: {str(e)}")
        return False

def test_multiple_image_analysis():
    """Test multiple image analysis functionality"""
    print("\n=== Multiple Image Analysis Test ===")
    
    from file_processor.models import FileDetail
    
    images = FileDetail.objects.all()[:2]
    
    if len(images) < 2:
        print("❌ Need at least 2 images for multiple analysis test")
        return False
    
    try:
        service = DifyAPIService(DIFY_API_KEY)
        
        print(f"Testing analysis of {len(images)} images")
        
        result = service.analyze_multiple_images(images)
        
        if "error" in result:
            print(f"❌ Analysis failed: {result['error']}")
            return False
        else:
            print("✅ Multiple image analysis completed successfully")
            return True
        
    except Exception as e:
        print(f"❌ Multiple analysis failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting Dify API tests...\n")
    
    api_ok = test_dify_connection()
    files_ok = test_image_file_access()
    upload_ok = test_multiple_image_upload()
    analysis_ok = test_multiple_image_analysis()
    
    print(f"\n=== Test Results ===")
    print(f"API Connection: {'✅' if api_ok else '❌'}")
    print(f"File Access: {'✅' if files_ok else '❌'}")
    print(f"Multiple Upload: {'✅' if upload_ok else '❌'}")
    print(f"Multiple Analysis: {'✅' if analysis_ok else '❌'}")
    
    if all([api_ok, files_ok, upload_ok, analysis_ok]):
        print("\n🎉 All tests passed! Multi-file Dify API works.")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")