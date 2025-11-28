#!/usr/bin/env python
"""
验证迁移结果
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

def verify_migration():
    """详细验证迁移结果"""
    print("=== 验证迁移结果 ===")
    
    # 统计FileAnalysis
    total_analyses = FileAnalysis.objects.count()
    header_analyses = FileAnalysis.objects.filter(analysis_type='header').count()
    detail_analyses = FileAnalysis.objects.filter(analysis_type='single').count()
    
    print(f"FileAnalysis总记录: {total_analyses}")
    print(f"  - header类型: {header_analyses}")
    print(f"  - single类型: {detail_analyses}")
    
    # 按状态统计
    print(f"\n按状态统计:")
    for status in ['processing', 'completed', 'failed']:
        count = FileAnalysis.objects.filter(status=status).count()
        print(f"  - {status}: {count}")
    
    # 按用户统计
    print(f"\n按用户统计:")
    for user in User.objects.all():
        count = FileAnalysis.objects.filter(user=user).count()
        print(f"  - {user.username}: {count}")
    
    # 验证数据完整性
    print(f"\n=== 数据完整性验证 ===")
    
    # 检查header类型的记录都有对应的file_header
    header_without_fileheader = FileAnalysis.objects.filter(
        analysis_type='header',
        file_header__isnull=True
    ).count()
    print(f"header类型缺少file_header的记录: {header_without_fileheader}")
    
    # 检查single类型的记录都有对应的file_detail
    single_without_filedetail = FileAnalysis.objects.filter(
        analysis_type='single',
        file_detail__isnull=True
    ).count()
    print(f"single类型缺少file_detail的记录: {single_without_filedetail}")
    
    # 检查是否有重复的关联
    print(f"\n=== 检查关联关系 ===")
    
    # 每个FileHeader对应的FileAnalysis数量
    print("FileHeader -> FileAnalysis 关联:")
    for header in FileHeader.objects.all()[:5]:
        analyses = FileAnalysis.objects.filter(file_header=header).count()
        print(f"  FileHeader {header.id}: {analyses} analyses")
    
    # 每个FileDetail对应的FileAnalysis数量
    print("\nFileDetail -> FileAnalysis 关联:")
    details_with_analysis = FileDetail.objects.filter(
        id__in=FileAnalysis.objects.filter(
            file_detail__isnull=False
        ).values_list('file_detail_id', flat=True)
    )
    
    for detail in details_with_analysis[:5]:
        analyses = FileAnalysis.objects.filter(file_detail=detail).count()
        print(f"  FileDetail {detail.id} (Page {detail.page_number}): {analyses} analyses")
    
    # 显示样本数据
    print(f"\n=== 样本数据 ===")
    
    print("header类型样本:")
    for analysis in FileAnalysis.objects.filter(analysis_type='header')[:3]:
        print(f"  {analysis}")
        print(f"    -> FileHeader: {analysis.file_header.id}")
        print(f"    -> Status: {analysis.status}")
        print(f"    -> Result Data Length: {len(analysis.result_data or '')}")
        print(f"    -> Log Length: {len(analysis.log or '')}")
        print("  ---")
    
    print("single类型样本:")
    for analysis in FileAnalysis.objects.filter(analysis_type='single')[:3]:
        print(f"  {analysis}")
        print(f"    -> FileDetail: {analysis.file_detail.id} (Page {analysis.file_detail.page_number})")
        print(f"    -> FileHeader: {analysis.file_detail.file_header.id}")
        print(f"    -> Status: {analysis.status}")
        print(f"    -> Result Data Length: {len(analysis.result_data or '')}")
        print("  ---")
    
    # 检查是否有数据丢失
    print(f"\n=== 数据丢失检查 ===")
    
    original_headers_with_data = FileHeader.objects.filter(
        models.Q(result_data__isnull=False) & ~models.Q(result_data='') |
        models.Q(log__isnull=False) & ~models.Q(log='')
    ).distinct().count()
    
    migrated_headers = FileAnalysis.objects.filter(analysis_type='header').count()
    
    print(f"原始有数据的FileHeader: {original_headers_with_data}")
    print(f"迁移的header类型记录: {migrated_headers}")
    
    if original_headers_with_data == migrated_headers:
        print("✅ FileHeader数据迁移完整")
    else:
        print("❌ FileHeader数据可能丢失")
    
    original_details_with_data = FileDetail.objects.exclude(
        models.Q(result_data__isnull=True) | 
        models.Q(result_data='') | 
        models.Q(result_data={})
    ).count()
    
    migrated_details = FileAnalysis.objects.filter(analysis_type='single').count()
    
    print(f"原始有数据的FileDetail: {original_details_with_data}")
    print(f"迁移的single类型记录: {migrated_details}")
    
    if original_details_with_data == migrated_details:
        print("✅ FileDetail数据迁移完整")
    else:
        print("❌ FileDetail数据可能丢失")

if __name__ == "__main__":
    from django.db import models
    verify_migration()