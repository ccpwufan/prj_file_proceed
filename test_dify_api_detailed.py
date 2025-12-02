#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from django.conf import settings
from file_processor.models import FileDetail

def test_dify_api_directly():
    print("=== Testing Dify API Directly ===")
    
    # Get a FileDetail object with an actual image
    first_detail = FileDetail.objects.first()
    if not first_detail or not first_detail.file_detail_filename:
        print("❌ No FileDetail with file found")
        return
    
    image_path = first_detail.file_detail_filename.path
    print(f"Image path: {image_path}")
    
    # Test upload step by step
    api_key = settings.DIFY_API_KEY
    user = settings.DIFY_USER
    server = settings.DIFY_SERVER
    
    print(f"API Key: {api_key[:10]}...")
    print(f"User: {user}")
    print(f"Server: {server}")
    
    # Step 1: Test upload
    print("\n--- Step 1: Testing Upload ---")
    upload_url = f'{server}/v1/files/upload'
    headers = {'Authorization': f'Bearer {api_key}'}
    
    ext = os.path.splitext(image_path)[-1].lower()
    mime = 'image/png' if ext == '.png' else 'image/jpeg'
    
    try:
        with open(image_path, 'rb') as file:
            files = {'file': (os.path.basename(image_path), file, mime)}
            data = {'user': user}
            response = requests.post(upload_url, headers=headers, files=files, data=data, timeout=60)
        
        print(f"Upload Status Code: {response.status_code}")
        print(f"Upload Headers: {dict(response.headers)}")
        print(f"Upload Response (raw): {response.text[:500]}...")
        
        if response.status_code == 201:
            upload_result = response.json()
            file_id = upload_result['id']
            print(f"✓ Upload successful, file_id: {file_id}")
            
            # Step 2: Test workflow
            print("\n--- Step 2: Testing Workflow ---")
            workflow_url = f"{server}/v1/workflows/run"
            workflow_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            workflow_data = {
                "inputs": {
                    "upload": {
                        "type": "image",
                        "transfer_method": "local_file",
                        "upload_file_id": file_id
                    }
                },
                "user": user,
                "response_mode": "blocking"
            }
            
            print(f"Workflow URL: {workflow_url}")
            print(f"Workflow Data: {json.dumps(workflow_data, indent=2)}")
            
            workflow_response = requests.post(workflow_url, headers=workflow_headers, json=workflow_data, timeout=60)
            
            print(f"Workflow Status Code: {workflow_response.status_code}")
            print(f"Workflow Headers: {dict(workflow_response.headers)}")
            print(f"Workflow Response (raw): {workflow_response.text[:1000]}...")
            
            if workflow_response.status_code == 200:
                try:
                    workflow_result = workflow_response.json()
                    print(f"✓ Workflow JSON parsed successfully")
                    print(f"Workflow Result: {json.dumps(workflow_result, indent=2)[:500]}...")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON Decode Error: {e}")
                    print(f"Response text: {repr(workflow_response.text[:200])}")
            else:
                print(f"❌ Workflow failed with status {workflow_response.status_code}")
                
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dify_api_directly()