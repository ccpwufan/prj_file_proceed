#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail
from django.test import RequestFactory
from file_processor.views import file_detail

def test_view_render():
    print("=== 视图渲染测试 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    print(f"FileHeader ID: {latest_header.id}")
    print(f"FileHeader 状态: {latest_header.status}")
    print(f"图片数量: {latest_header.images.count()}")
    print()
    
    # 创建模拟请求
    factory = RequestFactory()
    request = factory.get(f'/file/detail/{latest_header.id}/')
    
    # 模拟用户登录（假设用户ID为1）
    from django.contrib.auth.models import User
    user = User.objects.first()
    if user:
        request.user = user
    else:
        print("没有找到用户，跳过测试")
        return
    
    try:
        # 调用视图
        response = file_detail(request, latest_header.id)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容长度: {len(response.content)}")
        print()
        
        # 检查响应内容中是否包含关键信息
        content = response.content.decode('utf-8')
        
        # 检查是否包含 Converted Images 标题
        if 'Converted Images' in content:
            print("✓ 找到 'Converted Images' 标题")
        else:
            print("✗ 没有找到 'Converted Images' 标题")
        
        # 检查是否包含图片ID
        if f'data-image-id="{latest_header.images.first().id}"' in content:
            print("✓ 找到图片ID")
        else:
            print("✗ 没有找到图片ID")
        
        # 检查是否包含图片URL
        first_image = latest_header.images.first()
        if first_image and first_image.file_detail_filename.url in content:
            print("✓ 找到图片URL")
        else:
            print("✗ 没有找到图片URL")
        
        # 检查是否包含图片状态
        if 'Pending' in content:
            print("✓ 找到图片状态")
        else:
            print("✗ 没有找到图片状态")
            
        # 检查是否有隐藏的CSS
        if 'display:none' in content or 'display: none' in content:
            print("⚠ 发现 display:none 样式")
        
        # 输出包含 Converted Images 的部分
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'Converted Images' in line:
                print(f"\n=== Converted Images 附近的内容 ===")
                start = max(0, i-2)
                end = min(len(lines), i+10)
                for j in range(start, end):
                    print(f"{j+1:3}: {lines[j]}")
                break
        
    except Exception as e:
        print(f"视图渲染出错: {e}")

if __name__ == "__main__":
    test_view_render()