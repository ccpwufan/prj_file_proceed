#!/usr/bin/env python
"""
测试 AJAX 端点
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from file_processor.models import FileHeader

def test_ajax_endpoint():
    print("=== 测试 AJAX 端点 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    print(f"测试文件ID: {latest_header.id}")
    
    # 创建测试客户端
    client = Client()
    user = User.objects.first()
    if not user:
        print("没有找到用户")
        return
    
    client.force_login(user)
    
    try:
        # 测试 AJAX 端点
        response = client.get(f'/file/detail-partial/{latest_header.id}/')
        
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type')}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"JSON keys: {list(data.keys())}")
            
            if 'html' in data:
                html = data['html']
                print(f"HTML 长度: {len(html)}")
                
                if 'Converted Images' in html:
                    print("✓ HTML 包含 Converted Images")
                else:
                    print("✗ HTML 不包含 Converted Images")
                
                if 'data-image-id=' in html:
                    print("✓ HTML 包含图片卡片")
                else:
                    print("✗ HTML 不包含图片卡片")
            else:
                print("✗ 响应中没有 HTML 字段")
        else:
            print("✗ 请求失败")
            print(response.content.decode('utf-8'))
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ajax_endpoint()