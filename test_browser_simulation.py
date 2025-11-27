#!/usr/bin/env python
"""
模拟浏览器行为，检查页面加载后的状态
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
import re

def test_browser_simulation():
    print("=== 模拟浏览器行为测试 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    print(f"FileHeader ID: {latest_header.id}")
    print(f"FileHeader 状态: {latest_header.status}")
    print(f"图片数量: {latest_header.images.count()}")
    print()
    
    # 创建测试客户端
    client = Client()
    
    # 获取现有用户
    user = User.objects.first()
    if not user:
        print("没有找到用户")
        return
    
    client.force_login(user)
    
    try:
        # 第一次访问页面（模拟 analyzeAllFiles 之前）
        print("--- 第一次访问页面 ---")
        response1 = client.get(f'/file/detail/{latest_header.id}/')
        print(f"状态码: {response1.status_code}")
        
        content1 = response1.content.decode('utf-8')
        
        # 检查关键元素
        converted_images_count1 = content1.count('Converted Images')
        grid_count1 = content1.count('class="mt-4 grid')
        card_count1 = content1.count('data-image-id=')
        
        print(f"'Converted Images' 出现次数: {converted_images_count1}")
        print(f"Grid 容器出现次数: {grid_count1}")
        print(f"图片卡片出现次数: {card_count1}")
        
        # 模拟 analyzeAllFiles 调用
        print("\n--- 模拟 analyzeAllFiles 调用 ---")
        import json
        analyze_response = client.post(
            f'/file/analyze-all/{latest_header.id}/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        print(f"Analyze 响应状态码: {analyze_response.status_code}")
        if analyze_response.status_code == 200:
            result = analyze_response.json()
            print(f"Analyze 结果: {result.get('status', 'unknown')}")
        
        # 第二次访问页面（模拟 reload 之后）
        print("\n--- 第二次访问页面（reload之后）---")
        response2 = client.get(f'/file/detail/{latest_header.id}/')
        print(f"状态码: {response2.status_code}")
        
        content2 = response2.content.decode('utf-8')
        
        # 检查关键元素
        converted_images_count2 = content2.count('Converted Images')
        grid_count2 = content2.count('class="mt-4 grid')
        card_count2 = content2.count('data-image-id=')
        
        print(f"'Converted Images' 出现次数: {converted_images_count2}")
        print(f"Grid 容器出现次数: {grid_count2}")
        print(f"图片卡片出现次数: {card_count2}")
        
        # 比较两次访问的差异
        print("\n--- 比较差异 ---")
        print(f"'Converted Images' 差异: {converted_images_count2 - converted_images_count1}")
        print(f"Grid 容器差异: {grid_count2 - grid_count1}")
        print(f"图片卡片差异: {card_count2 - card_count1}")
        
        # 检查图片状态变化
        print(f"\n--- 数据库状态变化 ---")
        images_after = latest_header.images.all()
        for image in images_after:
            print(f"图片 {image.id}: 状态={image.status}, 结果数据={bool(image.result_data)}")
        
        # 检查是否有隐藏的CSS或JavaScript
        print(f"\n--- 检查潜在的隐藏代码 ---")
        
        # 查找可能的隐藏CSS
        hidden_patterns = [
            r'display\s*:\s*none',
            r'visibility\s*:\s*hidden',
            r'opacity\s*:\s*0',
            r'height\s*:\s*0',
            r'width\s*:\s*0'
        ]
        
        for pattern in hidden_patterns:
            matches = re.findall(pattern, content2, re.IGNORECASE)
            if matches:
                print(f"发现可能的隐藏样式: {pattern} - {len(matches)} 次")
        
        # 查找可能影响显示的JavaScript
        js_patterns = [
            r'\.hide\(\)',
            r'\.fadeOut\(\)',
            r'\.slideUp\(\)',
            r'style\.display\s*=\s*["\']none["\']',
            r'style\.visibility\s*=\s*["\']hidden["\']'
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, content2, re.IGNORECASE)
            if matches:
                print(f"发现可能的隐藏JavaScript: {pattern} - {len(matches)} 次")
        
        # 如果内容相同，问题可能在前端
        if content1 == content2:
            print("\n⚠  两次访问的HTML内容完全相同，问题可能在于：")
            print("   1. 浏览器缓存")
            print("   2. JavaScript 执行时机问题")
            print("   3. CSS 动画或过渡效果")
        else:
            print("\n✓ 两次访问的HTML内容有差异，后端数据已更新")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_browser_simulation()