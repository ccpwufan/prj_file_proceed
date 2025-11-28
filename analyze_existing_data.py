#!/usr/bin/env python
"""
分析现有数据结构
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail, FileAnalysis
from django.contrib.auth.models import User

def analyze_data():
    """分析现有数据"""
    print("=== 分析现有数据结构 ===")
    
    # 统计FileHeader数据
    file_headers = FileHeader.objects.all()
    print(f"FileHeader总数: {file_headers.count()}")
    
    header_with_result = file_headers.exclude(result_data__isnull=True).exclude(result_data='')
    print(f"有result_data的FileHeader: {header_with_result.count()}")
    
    header_with_log = file_headers.exclude(log__isnull=True).exclude(log='')
    print(f"有log的FileHeader: {header_with_log.count()}")
    
    # 统计FileDetail数据
    file_details = FileDetail.objects.all()
    print(f"FileDetail总数: {file_details.count()}")
    
    detail_with_result = file_details.exclude(result_data__isnull=True).exclude(result_data='')
    print(f"有result_data的FileDetail: {detail_with_result.count()}")
    
    # 统计现有FileAnalysis数据
    existing_analyses = FileAnalysis.objects.all()
    print(f"现有FileAnalysis记录: {existing_analyses.count()}")
    
    print("\n=== 详细数据样本 ===")
    
    # 显示有数据的FileHeader样本
    if header_with_result.exists():
        print("\n有result_data的FileHeader样本:")
        for header in header_with_result[:3]:
            print(f"  ID: {header.id}, User: {header.user.username}, Status: {header.status}")
            print(f"  result_data长度: {len(header.result_data or '')}")
            print(f"  log长度: {len(header.log or '')}")
            print(f"  created_at: {header.created_at}")
            print("  ---")
    
    # 显示有数据的FileDetail样本
    if detail_with_result.exists():
        print("\n有result_data的FileDetail样本:")
        for detail in detail_with_result[:3]:
            print(f"  ID: {detail.id}, FileHeader: {detail.file_header.id}, Page: {detail.page_number}")
            print(f"  Status: {detail.status}")
            print(f"  result_data类型: {type(detail.result_data)}")
            if detail.result_data:
                print(f"  result_data长度: {len(str(detail.result_data))}")
                if isinstance(detail.result_data, dict):
                    print(f"  result_data键: {list(detail.result_data.keys())}")
            print("  ---")
    
    return {
        'header_with_result': header_with_result.count(),
        'header_with_log': header_with_log.count(),
        'detail_with_result': detail_with_result.count(),
        'existing_analyses': existing_analyses.count()
    }

if __name__ == "__main__":
    stats = analyze_data()
    print(f"\n=== 数据统计汇总 ===")
    print(f"需要迁移的FileHeader记录: {stats['header_with_result']}")
    print(f"需要迁移的FileDetail记录: {stats['detail_with_result']}")
    print(f"需要清空的现有FileAnalysis记录: {stats['existing_analyses']}")