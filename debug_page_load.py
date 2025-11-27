#!/usr/bin/env python
"""
调试页面加载问题
检查页面刷新后 Converted Images 部分是否正确显示
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
from bs4 import BeautifulSoup

def debug_page_load():
    print("=== 调试页面加载问题 ===")
    
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
        print("没有找到用户，请先创建用户")
        return
    
    print(f"使用用户: {user.username}")
    
    # 强制登录
    client.force_login(user)
    
    try:
        # 访问页面
        response = client.get(f'/file/detail/{latest_header.id}/')
        
        if response.status_code != 200:
            print(f"页面访问失败，状态码: {response.status_code}")
            return
        
        # 解析 HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("=== HTML 结构分析 ===")
        
        # 检查 Converted Images 标题
        converted_images_title = soup.find('h3', string='Converted Images')
        if converted_images_title:
            print("✓ 找到 'Converted Images' 标题")
            
            # 找到包含标题的 div
            title_parent = converted_images_title.find_parent('div')
            if title_parent:
                print(f"  标题父元素: {title_parent.name}")
                print(f"  标题父元素类: {title_parent.get('class', [])}")
        else:
            print("✗ 没有找到 'Converted Images' 标题")
        
        # 检查 grid 元素
        grid_elements = soup.find_all(class_='grid')
        print(f"\n找到 {len(grid_elements)} 个 .grid 元素:")
        
        for i, grid in enumerate(grid_elements):
            print(f"  Grid {i+1}: {grid.get('class', [])}")
            
            # 检查 grid 内的图片卡片
            image_cards = grid.find_all(attrs={'data-image-id': True})
            print(f"    包含 {len(image_cards)} 个图片卡片")
            
            for j, card in enumerate(image_cards):
                image_id = card.get('data-image-id')
                print(f"      卡片 {j+1}: data-image-id={image_id}")
                
                # 检查卡片内的图片元素
                img = card.find('img')
                if img:
                    print(f"        图片 src: {img.get('src', 'None')}")
                
                # 检查状态元素
                status_elem = card.find(class_='image-status')
                if status_elem:
                    print(f"        状态文本: {status_elem.get_text(strip=True)}")
        
        # 检查是否有隐藏的元素
        hidden_elements = soup.find_all(attrs={'style': lambda x: x and 'display:none' in x})
        if hidden_elements:
            print(f"\n⚠ 发现 {len(hidden_elements)} 个隐藏元素 (display:none)")
            for elem in hidden_elements:
                print(f"  {elem.name}: {elem.get('class', [])}")
        
        # 检查是否有 visibility:hidden 的元素
        hidden_elements = soup.find_all(attrs={'style': lambda x: x and 'visibility:hidden' in x})
        if hidden_elements:
            print(f"\n⚠ 发现 {len(hidden_elements)} 个隐藏元素 (visibility:hidden)")
            for elem in hidden_elements:
                print(f"  {elem.name}: {elem.get('class', [])}")
        
        # 输出 Converted Images 部分的完整 HTML
        if converted_images_title:
            print(f"\n=== Converted Images 部分 HTML ===")
            # 找到包含 Converted Images 的整个部分
            section = converted_images_title.find_parent('div', class_='border-t')
            if section:
                print(section.prettify()[:1000] + "..." if len(str(section)) > 1000 else section.prettify())
        
    except Exception as e:
        print(f"调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_page_load()