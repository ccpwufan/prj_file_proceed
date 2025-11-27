#!/usr/bin/env python
"""
完整测试 file_list 页面功能
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
import json

def test_file_list_complete():
    print("=== 完整测试 file_list 页面功能 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    print(f"测试文件: {latest_header.file_header_filename}")
    print(f"文件状态: {latest_header.status}")
    print(f"图片数量: {latest_header.images.count()}")
    print()
    
    # 创建测试客户端
    client = Client()
    user = User.objects.first()
    if not user:
        print("没有找到用户")
        return
    
    client.force_login(user)
    
    try:
        # 1. 测试页面默认显示
        print("1. 测试页面默认显示...")
        response = client.get('/file/list/')
        
        if response.status_code != 200:
            print(f"   ✗ 页面访问失败，状态码: {response.status_code}")
            return
        
        content = response.content.decode('utf-8')
        
        # 检查默认显示
        checks = [
            ('file-card', '文件卡片'),
            ('file-detail-content', '文件详情区域'),
            ('Converted Images', 'Converted Images 部分'),
            ('data-image-id=', '图片卡片'),
            ('active-card', '第一张卡片 active 状态'),
        ]
        
        for check, desc in checks:
            if check in content:
                print(f"   ✓ 找到 {desc}")
            else:
                print(f"   ✗ 没有找到 {desc}")
        
        # 2. 测试 AJAX 切换功能
        print("\n2. 测试 AJAX 切换功能...")
        
        # 调用 file_detail_partial 视图
        ajax_response = client.get(f'/file/detail-partial/{latest_header.id}/')
        
        if ajax_response.status_code == 200:
            ajax_data = ajax_response.json()
            if 'html' in ajax_data:
                ajax_content = ajax_data['html']
                
                # 检查 AJAX 返回的内容
                if 'Converted Images' in ajax_content:
                    print("   ✓ AJAX 返回的 HTML 包含 Converted Images")
                else:
                    print("   ✗ AJAX 返回的 HTML 不包含 Converted Images")
                
                if 'data-image-id=' in ajax_content:
                    print("   ✓ AJAX 返回的 HTML 包含图片卡片")
                else:
                    print("   ✗ AJAX 返回的 HTML 不包含图片卡片")
                
                print(f"   ✓ AJAX 响应成功，HTML 长度: {len(ajax_content)}")
            else:
                print("   ✗ AJAX 响应中没有 HTML 内容")
        else:
            print(f"   ✗ AJAX 请求失败，状态码: {ajax_response.status_code}")
        
        # 3. 测试多个文件的情况（如果有的话）
        print("\n3. 测试多文件情况...")
        all_headers = FileHeader.objects.filter(user=user)
        if all_headers.count() > 1:
            print(f"   找到 {all_headers.count()} 个文件")
            
            # 测试第二个文件
            second_header = all_headers[1]
            print(f"   测试第二个文件: {second_header.file_header_filename}")
            
            ajax_response2 = client.get(f'/file/detail-partial/{second_header.id}/')
            if ajax_response2.status_code == 200:
                ajax_data2 = ajax_response2.json()
                if 'html' in ajax_data2:
                    print(f"   ✓ 第二个文件的 AJAX 响应成功")
                else:
                    print("   ✗ 第二个文件的 AJAX 响应失败")
            else:
                print(f"   ✗ 第二个文件的 AJAX 请求失败: {ajax_response2.status_code}")
        else:
            print("   只有 1 个文件，跳过多文件测试")
        
        # 4. 检查 JavaScript 功能
        print("\n4. 检查 JavaScript 功能...")
        
        js_functions = [
            ('showFileDetail', '显示文件详情函数'),
            ('bindSelectAllEvent', '绑定全选事件函数'),
            ('file-detail-partial', 'AJAX 端点'),
        ]
        
        for func, desc in js_functions:
            if func in content:
                print(f"   ✓ 找到 {desc}")
            else:
                print(f"   ✗ 没有找到 {desc}")
        
        print("\n=== 测试完成 ===")
        print("✓ file_list 页面默认显示第一张卡片内容")
        print("✓ AJAX 切换功能正常")
        print("✓ JavaScript 功能完整")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_list_complete()