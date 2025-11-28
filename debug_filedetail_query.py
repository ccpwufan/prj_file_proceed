#!/usr/bin/env python
"""
调试FileDetail查询
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileDetail, FileAnalysis
from django.db import models

def debug_filedetail():
    """调试FileDetail查询"""
    print("=== 调试FileDetail查询 ===")
    
    # 总数
    total_details = FileDetail.objects.count()
    print(f"FileDetail总数: {total_details}")
    
    # 检查result_data字段的各种情况
    with_result_data = FileDetail.objects.exclude(result_data__isnull=True)
    print(f"result_data不为null: {with_result_data.count()}")
    
    not_empty_result = with_result_data.exclude(result_data='')
    print(f"result_data不为null且不为空字符串: {not_empty_result.count()}")
    
    # 检查result_data为空字典的情况
    empty_dict = FileDetail.objects.filter(result_data={})
    print(f"result_data为空字典: {empty_dict.count()}")
    
    # 检查result_data不为空字典的情况
    not_empty_dict = FileDetail.objects.exclude(result_data={})
    print(f"result_data不为空字典: {not_empty_dict.count()}")
    
    # 显示前几个样本
    print("\n前5个FileDetail的result_data:")
    for detail in FileDetail.objects.all()[:5]:
        print(f"  ID: {detail.id}")
        print(f"  result_data类型: {type(detail.result_data)}")
        print(f"  result_data值: {detail.result_data}")
        print(f"  result_data是否为空: {not detail.result_data}")
        print("  ---")
    
    # 尝试不同的查询方式
    print("\n=== 尝试不同查询方式 ===")
    
    # 方式1: 检查result_data是否存在且不为空
    query1 = FileDetail.objects.filter(
        result_data__isnull=False
    ).exclude(
        models.Q(result_data='') | models.Q(result_data={})
    )
    print(f"方式1结果: {query1.count()}")
    
    # 方式2: 检查result_data是否有内容
    query2 = FileDetail.objects.exclude(
        models.Q(result_data__isnull=True) | 
        models.Q(result_data='') | 
        models.Q(result_data={})
    )
    print(f"方式2结果: {query2.count()}")

if __name__ == "__main__":
    debug_filedetail()