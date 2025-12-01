#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader

def main():
    print("=== 批量更新结果检查 ===")
    
    # 统计信息
    total_records = FileHeader.objects.count()
    records_with_result_data = FileHeader.objects.exclude(
        result_data__isnull=True
    ).exclude(
        result_data=''
    ).count()
    records_with_comments = FileHeader.objects.exclude(
        comments__isnull=True
    ).exclude(
        comments=''
    ).count()
    records_empty_comments = FileHeader.objects.filter(
        comments__isnull=True
    ).count()
    
    print(f"总记录数：{total_records}")
    print(f"有result_data的记录：{records_with_result_data}")
    print(f"有comments的记录：{records_with_comments}")
    print(f"comments为空的记录：{records_empty_comments}")
    
    print("\n=== 已更新的记录 ===")
    updated_records = FileHeader.objects.exclude(
        comments__isnull=True
    ).exclude(
        comments=''
    )
    
    for header in updated_records:
        filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
        print(f"ID: {header.id}, 文件: {filename}, comments: {header.comments}")
    
    print("\n=== 未更新的记录 ===")
    not_updated = FileHeader.objects.filter(comments__isnull=True)
    
    for header in not_updated:
        filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
        has_result_data = bool(header.result_data)
        result_data_length = len(header.result_data) if header.result_data else 0
        print(f"ID: {header.id}, 文件: {filename}, 有result_data: {has_result_data}, 长度: {result_data_length}")

if __name__ == "__main__":
    main()