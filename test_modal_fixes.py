#!/usr/bin/env python3
"""
Test script to verify modal and log functionality fixes
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail
from django.contrib.auth.models import User

def test_log_functionality():
    """Test the log functionality"""
    print("Testing log functionality...")
    
    # Get a test file header
    file_header = FileHeader.objects.first()
    if not file_header:
        print("No file headers found. Creating test data...")
        # You would need to create test data here
        return
    
    print(f"Found file header: {file_header}")
    print(f"Current status: {file_header.status}")
    print(f"Current log: {file_header.log}")
    
    # Test append_log function
    from file_processor.views import append_log
    append_log(file_header, "Test log entry from test script")
    
    # Refresh and check
    file_header.refresh_from_db()
    print(f"Updated log: {file_header.log}")

def check_modal_fixes():
    """Check if modal fixes are applied correctly"""
    print("\nChecking modal fixes...")
    
    template_path = "d:/Projects/prj_file_proceed/file_processor/templates/file_processor/file_detail_partial.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for background color changes
    if 'bg-gray-500 bg-opacity-50' in content:
        print("✓ Modal background color changed to light gray")
    else:
        print("✗ Modal background color not changed")
    
    # Check for correct URL path
    if '/file/get-log/' in content:
        print("✓ Correct log URL path found")
    else:
        print("✗ Incorrect log URL path")
    
    # Check for improved error handling
    if 'Error polling log:' in content:
        print("✓ Improved error handling in pollLog function")
    else:
        print("✗ Error handling not improved")

if __name__ == "__main__":
    print("Testing fixes for modal and log functionality")
    print("=" * 50)
    
    test_log_functionality()
    check_modal_fixes()
    
    print("\n" + "=" * 50)
    print("Test completed!")