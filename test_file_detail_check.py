#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail

def check_file_detail_data():
    print("=== FileHeader 和 FileDetail 数据检查 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    print(f"FileHeader ID: {latest_header.id}")
    print(f"FileHeader 状态: {latest_header.status}")
    print(f"FileHeader 文件名: {latest_header.file_header_filename}")
    print(f"总页数: {latest_header.total_pages}")
    print()
    
    # 获取所有相关的 FileDetail
    images = latest_header.images.all()
    print(f"FileDetail 数量: {images.count()}")
    print()
    
    # 检查每个 FileDetail
    for i, image in enumerate(images, 1):
        print(f"--- FileDetail {i} ---")
        print(f"ID: {image.id}")
        print(f"页码: {image.page_number}")
        print(f"状态: {image.status}")
        print(f"文件路径: {image.file_detail_filename}")
        print(f"文件是否存在: {image.file_detail_filename.path if image.file_detail_filename else 'None'}")
        print(f"结果数据: {image.result_data}")
        print()
    
    # 检查模板中需要的字段
    print("=== 模板字段检查 ===")
    for image in images:
        print(f"图片 ID: {image.id}")
        print(f"image.status: '{image.status}'")
        print(f"image.get_status_display(): '{image.get_status_display()}'")
        print(f"image.file_detail_filename.url: '{image.file_detail_filename.url if image.file_detail_filename else 'None'}")
        print(f"image.page_number: {image.page_number}")
        print("---")

if __name__ == "__main__":
    check_file_detail_data()