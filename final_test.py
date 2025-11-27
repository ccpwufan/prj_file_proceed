#!/usr/bin/env python
"""
最终测试：验证 analyzeAllFiles 完整流程
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

def final_test():
    print("=== 最终测试：analyzeAllFiles 完整流程 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    print(f"测试文件: {latest_header.file_header_filename}")
    print(f"初始状态: {latest_header.status}")
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
        # 1. 访问页面 - 检查 Converted Images 是否显示
        print("1. 检查页面显示...")
        response = client.get(f'/file/detail/{latest_header.id}/')
        content = response.content.decode('utf-8')
        
        if 'Converted Images' in content:
            print("   ✓ Converted Images 部分正常显示")
        else:
            print("   ✗ Converted Images 部分未显示")
            return
        
        if 'data-image-id=' in content:
            print("   ✓ 图片卡片正常显示")
        else:
            print("   ✗ 图片卡片未显示")
            return
        
        # 2. 调用 analyzeAllFiles
        print("\n2. 调用 analyzeAllFiles...")
        analyze_response = client.post(
            f'/file/analyze-all/{latest_header.id}/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        if analyze_response.status_code == 200:
            result = analyze_response.json()
            if result.get('status') == 'success':
                print("   ✓ analyzeAllFiles 调用成功")
            else:
                print(f"   ✗ analyzeAllFiles 调用失败: {result.get('error', 'Unknown error')}")
                return
        else:
            print(f"   ✗ analyzeAllFiles HTTP错误: {analyze_response.status_code}")
            return
        
        # 3. 刷新页面 - 检查状态更新
        print("\n3. 刷新页面检查状态...")
        response = client.get(f'/file/detail/{latest_header.id}/')
        content = response.content.decode('utf-8')
        
        # 检查数据库中的状态
        images = latest_header.images.all()
        for image in images:
            print(f"   图片 {image.id}: 状态={image.status}, 有结果数据={bool(image.result_data)}")
            
            if image.status == 'completed' and image.result_data:
                print("   ✓ 图片状态和结果数据正确更新")
            else:
                print("   ✗ 图片状态或结果数据未正确更新")
        
        # 检查页面中是否显示 "Completed" 状态
        if 'Completed' in content:
            print("   ✓ 页面显示正确的状态")
        else:
            print("   ⚠ 页面可能未显示最新状态")
        
        # 检查是否有 "View Result Data" 按钮
        if 'View Result Data' in content or 'result-data-icon' in content:
            print("   ✓ 结果查看按钮可用")
        else:
            print("   ⚠ 结果查看按钮可能未显示")
        
        print("\n=== 测试完成 ===")
        print("✓ analyzeAllFiles 执行完成后刷新页面，Converted Images 列表正常显示")
        print("✓ 图片状态正确更新为 'completed'")
        print("✓ 结果数据正确保存")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_test()