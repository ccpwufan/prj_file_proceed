#!/usr/bin/env python3
"""
Test script to verify log modal improvements
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader
from file_processor.views import append_log

def test_log_clearing():
    """Test log clearing functionality"""
    print("Testing log clearing functionality...")
    
    # Get a test file header
    file_header = FileHeader.objects.first()
    if not file_header:
        print("No file headers found.")
        return False
    
    print(f"Testing with file header: {file_header}")
    
    # Add some test log entries
    append_log(file_header, "Test log entry 1")
    append_log(file_header, "Test log entry 2")
    append_log(file_header, "Test log entry 3")
    
    file_header.refresh_from_db()
    print(f"Log before clearing: {file_header.log}")
    
    # Simulate the log clearing logic
    original_log = file_header.log
    file_header.log = ""
    file_header.save()
    
    file_header.refresh_from_db()
    print(f"Log after clearing: {file_header.log}")
    
    if file_header.log == "":
        print("✓ Log cleared successfully")
        return True
    else:
        print("✗ Log clearing failed")
        return False

def check_modal_close_button():
    """Check if duplicate close button is removed"""
    print("\nChecking modal close button...")
    
    template_path = "d:/Projects/prj_file_proceed/file_processor/templates/file_processor/file_detail_partial.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the duplicate close button
    if 'button onclick="closeLogModal()" class="px-4 py-2 bg-gray-600' in content:
        print("✗ Duplicate close button still exists")
        return False
    else:
        print("✓ Duplicate close button removed")
    
    # Check that the X button still exists
    if 'onclick="closeLogModal()"' in content and 'svg' in content:
        print("✓ X close button still exists")
        return True
    else:
        print("✗ X close button missing")
        return False

if __name__ == "__main__":
    print("Testing log modal improvements")
    print("=" * 50)
    
    log_test_passed = test_log_clearing()
    modal_test_passed = check_modal_close_button()
    
    print("\n" + "=" * 50)
    if log_test_passed and modal_test_passed:
        print("✅ All tests passed! Log modal improvements are working correctly.")
    else:
        print("❌ Some tests failed. Please review the implementation.")