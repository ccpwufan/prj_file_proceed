#!/usr/bin/env python
"""
Test script for the new log functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader
from file_processor.views import append_log
from django.contrib.auth.models import User

def test_log_functionality():
    """Test the log functionality"""
    print("Testing log functionality...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    # Get a FileHeader to test with
    file_header = FileHeader.objects.first()
    if not file_header:
        print("No FileHeader found. Creating a test one...")
        file_header = FileHeader.objects.create(
            user=user,
            comments='Test file for logging'
        )
    
    print(f"Testing with FileHeader: {file_header.id}")
    
    # Test append_log function
    append_log(file_header, "Test log message 1")
    append_log(file_header, "Test log message 2")
    append_log(file_header, "Test log message 3")
    
    # Refresh from database
    file_header.refresh_from_db()
    
    print(f"Log content:\n{file_header.log}")
    
    print("Test completed successfully!")

if __name__ == '__main__':
    test_log_functionality()