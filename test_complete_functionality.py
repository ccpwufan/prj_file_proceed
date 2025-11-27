#!/usr/bin/env python
"""
Complete functionality test for log feature
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
import json

def test_complete_functionality():
    """Test the complete log functionality"""
    print("Testing complete log functionality...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com', 'password': 'testpass123'}
    )
    
    # Get a FileHeader with images owned by test user
    file_header = FileHeader.objects.filter(images__isnull=False, user=user).first()
    if not file_header:
        # Try to find any file header and assign it to test user
        file_header = FileHeader.objects.filter(images__isnull=False).first()
        if file_header:
            file_header.user = user
            file_header.save()
            print(f"Assigned FileHeader {file_header.id} to test user")
        else:
            print("No FileHeader with images found. Please upload a PDF first.")
            return
    
    print(f"Testing with FileHeader: {file_header.id}")
    print(f"Number of images: {file_header.images.count()}")
    
    # Test the get_log endpoint
    client = Client()
    client.force_login(user)
    
    # Test get_log endpoint
    url = reverse('get_log', kwargs={'pk': file_header.id})
    response = client.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Get log response: {data}")
        print("✓ Get log endpoint works")
    else:
        print(f"✗ Get log endpoint failed: {response.status_code}")
        return
    
    # Test analyze_all_files endpoint (simulate the request)
    url = reverse('analyze_all_files', kwargs={'pk': file_header.id})
    
    # Note: This will actually call the Dify API, so we'll just test the endpoint structure
    print(f"Analyze all files URL: {url}")
    print("✓ URL routing works")
    
    print("Complete functionality test finished!")
    print("\nTo test the full functionality:")
    print("1. Start the Django server")
    print("2. Go to a file detail page with converted images")
    print("3. Click 'Analyze All Files' button")
    print("4. The log modal should appear and show progress")
    print("5. After completion, modal should close and page should reload")

if __name__ == '__main__':
    test_complete_functionality()