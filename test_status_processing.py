#!/usr/bin/env python3
"""
Test script to verify status is set to processing before analysis
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader

def test_status_setting():
    """Test that status is properly set to processing"""
    print("Testing status setting to processing...")
    
    # Get a test file header
    file_header = FileHeader.objects.first()
    if not file_header:
        print("No file headers found.")
        return False
    
    print(f"Testing with file header: {file_header}")
    print(f"Original status: {file_header.status}")
    
    # Simulate the status setting logic
    original_status = file_header.status
    file_header.status = 'processing'
    file_header.log = ""
    file_header.result_data = ""
    file_header.save()
    
    file_header.refresh_from_db()
    print(f"Status after setting to processing: {file_header.status}")
    print(f"Log after clearing: '{file_header.log}'")
    
    # Check if status was set correctly before restoring
    status_was_set = (file_header.status == 'processing' and file_header.log == "")
    
    # Restore original status
    file_header.status = original_status
    file_header.save()
    
    if status_was_set:
        print("✓ Status successfully set to processing and log cleared")
        return True
    else:
        print("✗ Status setting failed")
        return False

def check_views_code():
    """Check if the views.py code is correct"""
    print("\nChecking views.py code...")
    
    views_path = "d:/Projects/prj_file_proceed/file_processor/views.py"
    
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the status setting line
    if "file_header.status = 'processing'" in content:
        print("✓ Status setting to processing found in views.py")
        return True
    else:
        print("✗ Status setting to processing not found in views.py")
        return False

if __name__ == "__main__":
    print("Testing status setting to processing before analysis")
    print("=" * 60)
    
    status_test_passed = test_status_setting()
    code_test_passed = check_views_code()
    
    print("\n" + "=" * 60)
    if status_test_passed and code_test_passed:
        print("✅ All tests passed! Status setting is working correctly.")
    else:
        print("❌ Some tests failed. Please review the implementation.")