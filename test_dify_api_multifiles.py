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
        
        print(f"Testing upload of {len(images)} images")
        
        # Upload each image individually and collect file IDs
        file_ids = []
        for img in images:
            file_id = service.upload_image(img.file_detail_filename.path)
            file_ids.append(file_id)
            print(f"✅ Uploaded image {img.id}, file_id: {file_id}")
        
        print(f"✅ Successfully uploaded {len(file_ids)} images")
        print(f"File IDs: {file_ids}")
        
        return file_ids  # Return file IDs for next test
        
    except Exception as e:
        print(f"❌ Multiple upload failed: {str(e)}")
        return False



def test_run_workflow_files_function():
    """Test specifically the new run_workflow_files function"""
    print("\n=== Run Workflow Files Test ===")
    
    from file_processor.models import FileDetail
    
    images = FileDetail.objects.all()[:3]  # Test with up to 3 images
    
    if len(images) < 1:
        print("❌ Need at least 1 image for workflow files test")
        return False
    
    try:
        service = DifyAPIService(DIFY_API_KEY)
        
        # Upload images and collect file IDs
        file_ids = []
        for img in images:
            file_id = service.upload_image(img.file_detail_filename.path)
            file_ids.append(file_id)
            print(f"✅ Uploaded image {img.id}, file_id: {file_id}")
        
        print(f"Testing run_workflow_files with {len(file_ids)} files")
        
        # Test the new run_workflow_files method
        success, result_data, error_msg = service.run_workflow_files(file_ids)
        
        if success:
            print("✅ run_workflow_files test successful")
            print(f"Analysis result length: {len(str(result_data))} characters")
            print("Result preview:")
            print("-" * 50)
            print(str(result_data)[:500])
            print("-" * 50)
            return True
        else:
            print(f"❌ run_workflow_files test failed: {error_msg}")
            return False
        
    except Exception as e:
        print(f"❌ run_workflow_files test error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting Dify API tests...\n")
    
    api_ok = test_dify_connection()
    files_ok = test_image_file_access()
    upload_ok = test_multiple_image_upload()
    workflow_files_ok = test_run_workflow_files_function()
    
    print(f"\n=== Test Results ===")
    print(f"API Connection: {'✅' if api_ok else '❌'}")
    print(f"File Access: {'✅' if files_ok else '❌'}")
    print(f"Multiple Upload: {'✅' if upload_ok else '❌'}")
    print(f"Run Workflow Files: {'✅' if workflow_files_ok else '❌'}")
    
    if all([api_ok, files_ok, upload_ok, workflow_files_ok]):
        print("\n🎉 All tests passed! Multi-file Dify API works.")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")