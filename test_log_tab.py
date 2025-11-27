#!/usr/bin/env python3
"""
Test script to verify Log tab functionality in result_detail.html
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader
from file_processor.views import result_detail
from django.test import RequestFactory
from django.contrib.auth.models import User

def test_result_detail_with_log():
    """Test that result_detail view includes log_content"""
    print("Testing result_detail view with log content...")
    
    # Get a test file header
    file_header = FileHeader.objects.first()
    if not file_header:
        print("No file headers found.")
        return False
    
    print(f"Testing with file header: {file_header}")
    print(f"Current log: {file_header.log}")
    
    # Create a mock request
    factory = RequestFactory()
    user = User.objects.first()
    if not user:
        print("No users found.")
        return False
    
    request = factory.get(f'/result/detail/{file_header.pk}/')
    request.user = user
    
    try:
        # Call the view
        response = result_detail(request, file_header.pk)
        
        # Check if response is successful
        if response.status_code == 200:
            print("✓ View executed successfully")
            
            # Check context
            context = response.context_data
            if 'log_content' in context:
                print("✓ log_content found in context")
                print(f"Log content length: {len(context['log_content'])}")
                return True
            else:
                print("✗ log_content not found in context")
                return False
        else:
            print(f"✗ View returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error executing view: {e}")
        return False

def check_template_changes():
    """Check if template has Log tab"""
    print("\nChecking template changes...")
    
    template_path = "d:/Projects/prj_file_proceed/file_processor/templates/file_processor/result_detail.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for Log tab button
    if 'switchTab(\'log\')' in content and 'Log' in content:
        print("✓ Log tab button found")
    else:
        print("✗ Log tab button not found")
        return False
    
    # Check for Log tab content
    if 'id="log-content"' in content:
        print("✓ Log tab content found")
    else:
        print("✗ Log tab content not found")
        return False
    
    # Check for log_content variable
    if '{{ log_content }}' in content:
        print("✓ log_content variable found in template")
        return True
    else:
        print("✗ log_content variable not found in template")
        return False

if __name__ == "__main__":
    print("Testing Log tab functionality in result_detail")
    print("=" * 50)
    
    view_test_passed = test_result_detail_with_log()
    template_test_passed = check_template_changes()
    
    print("\n" + "=" * 50)
    if view_test_passed and template_test_passed:
        print("✅ All tests passed! Log tab functionality is working correctly.")
    else:
        print("❌ Some tests failed. Please review the implementation.")