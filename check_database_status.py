#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader

def check_database_status():
    """检查数据库状态"""
    print("=== 数据库状态检查 ===")
    total_records = FileHeader.objects.count()
    records_with_result_data = FileHeader.objects.filter(result_data__isnull=False).exclude(result_data='').count()
    records_to_update = FileHeader.objects.filter(
        result_data__isnull=False
    ).exclude(
        result_data=''
    ).filter(
        comments__isnull=True
    ).count()
    
    print(f"总记录数: {total_records}")
    print(f"有result_data的记录数: {records_with_result_data}")
    print(f"需要更新的记录数 (有result_data但comments为空): {records_to_update}")
    
    # 显示前5条需要更新的记录
    records = FileHeader.objects.filter(
        result_data__isnull=False
    ).exclude(
        result_data=''
    ).filter(
        comments__isnull=True
    )[:5]
    
    print("\n=== 前5条需要更新的记录 ===")
    for record in records:
        print(f"ID: {record.id}, 文件: {record.file_header_filename}")
        print(f"result_data前100字符: {record.result_data[:100] if record.result_data else 'None'}")
        print(f"comments: {record.comments}")
        print("-" * 50)

if __name__ == "__main__":
    check_database_status()