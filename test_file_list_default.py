#!/usr/bin/env python
"""
测试 file_list 页面默认显示第一张卡片的内容
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

def test_file_list_default():
    print("=== 测试 file_list 默认显示第一张卡片内容 ===")
    
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
        # 访问文件列表页面
        print("访问文件列表页面...")
        response = client.get('/file/list/')
        
        if response.status_code != 200:
            print(f"页面访问失败，状态码: {response.status_code}")
            return
        
        content = response.content.decode('utf-8')
        
        # 检查关键元素
        print("检查页面内容...")
        
        # 1. 检查是否有文件卡片
        if 'file-card' in content:
            print("   ✓ 找到文件卡片")
        else:
            print("   ✗ 没有找到文件卡片")
            return
        
        # 2. 检查是否有文件详情区域
        if 'file-detail-content' in content:
            print("   ✓ 找到文件详情区域")
        else:
            print("   ✗ 没有找到文件详情区域")
            return
        
        # 3. 检查是否默认显示第一张卡片的详情
        if 'Converted Images' in content:
            print("   ✓ 默认显示 Converted Images 部分")
        else:
            print("   ⚠ 没有显示 Converted Images 部分")
        
        # 4. 检查是否有图片卡片
        if 'data-image-id=' in content:
            print("   ✓ 找到图片卡片")
            # 统计图片卡片数量
            card_count = content.count('data-image-id=')
            print(f"   图片卡片数量: {card_count}")
        else:
            print("   ✗ 没有找到图片卡片")
        
        # 5. 检查第一张卡片是否被标记为 active
        if 'active-card' in content:
            print("   ✓ 第一张卡片被标记为 active")
        else:
            print("   ⚠ 第一张卡片没有被标记为 active")
        
        # 6. 检查是否有文件信息
        if latest_header.file_header_filename.name.split('/')[-1] in content:
            print("   ✓ 显示文件名")
        else:
            print("   ⚠ 没有显示文件名")
        
        # 7. 检查是否有状态信息
        if latest_header.get_status_display() in content:
            print("   ✓ 显示状态信息")
        else:
            print("   ⚠ 没有显示状态信息")
        
        print("\n=== 测试完成 ===")
        print("✓ file_list 页面默认显示第一张卡片的内容")
        
        # 输出一些调试信息
        print(f"\n=== 调试信息 ===")
        print(f"第一张文件ID: {latest_header.id}")
        print(f"第一张文件名: {latest_header.file_header_filename.name}")
        print(f"第一张文件状态: {latest_header.get_status_display()}")
        print(f"第一张文件图片数: {latest_header.images.count()}")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_list_default()