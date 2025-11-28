#!/usr/bin/env python
"""
将FileHeader和FileDetail的result_data和log迁移到FileAnalysis表
"""
import os
import sys
import django
from datetime import datetime

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail, FileAnalysis
from django.contrib.auth.models import User
from django.db import transaction

def clear_fileanalysis_table():
    """清空FileAnalysis表"""
    print("=== 清空FileAnalysis表 ===")
    
    count = FileAnalysis.objects.count()
    print(f"当前FileAnalysis记录数: {count}")
    
    if count > 0:
        FileAnalysis.objects.all().delete()
        print(f"✅ 已删除 {count} 条FileAnalysis记录")
    else:
        print("✅ FileAnalysis表已经是空的")
    
    return count

def migrate_header_data():
    """迁移FileHeader数据到FileAnalysis"""
    print("\n=== 迁移FileHeader数据 ===")
    
    # 获取有result_data或log的FileHeader
    headers_to_migrate = FileHeader.objects.filter(
        models.Q(result_data__isnull=False) & ~models.Q(result_data='') |
        models.Q(log__isnull=False) & ~models.Q(log='')
    ).distinct()
    
    print(f"需要迁移的FileHeader记录: {headers_to_migrate.count()}")
    
    migrated_count = 0
    failed_count = 0
    
    for header in headers_to_migrate:
        try:
            # 确定状态
            if header.status in ['processing', 'completed', 'failed']:
                status = header.status
            else:
                # 根据result_data是否存在来判断状态
                if header.result_data:
                    status = 'completed'
                else:
                    status = 'failed'
            
            # 创建FileAnalysis记录
            analysis = FileAnalysis.objects.create(
                user=header.user,
                file_header=header,
                analysis_type='header',
                status=status,
                result_data=header.result_data,
                log=header.log,
                created_at=header.created_at,  # 保持原创建时间
                api_key_used='DIFY_API_KEY_INVICE_FILES'  # 假设使用这个API key
            )
            
            migrated_count += 1
            print(f"✅ 迁移FileHeader {header.id} -> FileAnalysis {analysis.id}")
            
        except Exception as e:
            failed_count += 1
            print(f"❌ 迁移FileHeader {header.id} 失败: {e}")
    
    print(f"\nFileHeader迁移完成: 成功 {migrated_count}, 失败 {failed_count}")
    return migrated_count, failed_count

def migrate_detail_data():
    """迁移FileDetail数据到FileAnalysis"""
    print("\n=== 迁移FileDetail数据 ===")
    
    # 获取有非空result_data的FileDetail（排除null、空字符串、空字典）
    details_to_migrate = FileDetail.objects.exclude(
        models.Q(result_data__isnull=True) | 
        models.Q(result_data='') | 
        models.Q(result_data={})
    )
    
    print(f"需要迁移的FileDetail记录: {details_to_migrate.count()}")
    
    migrated_count = 0
    failed_count = 0
    
    for detail in details_to_migrate:
        try:
            # 确定状态
            if detail.status in ['processing', 'completed', 'failed']:
                status = detail.status
            else:
                # 根据result_data内容来判断状态
                if isinstance(detail.result_data, dict):
                    if detail.result_data.get('status') == 'success':
                        status = 'completed'
                    elif detail.result_data.get('status') == 'failed':
                        status = 'failed'
                    else:
                        status = 'completed'  # 默认认为有数据就是成功的
                else:
                    status = 'completed' if detail.result_data else 'failed'
            
            # 处理result_data
            if isinstance(detail.result_data, dict):
                result_data_str = str(detail.result_data)
            else:
                result_data_str = str(detail.result_data) if detail.result_data else ''
            
            # 创建FileAnalysis记录
            analysis = FileAnalysis.objects.create(
                user=detail.file_header.user,
                file_detail=detail,
                analysis_type='single',
                status=status,
                result_data=result_data_str,
                created_at=detail.created_at,  # 保持原创建时间
                api_key_used='DIFY_API_KEY'  # 假设使用这个API key
            )
            
            migrated_count += 1
            print(f"✅ 迁移FileDetail {detail.id} -> FileAnalysis {analysis.id}")
            
        except Exception as e:
            failed_count += 1
            print(f"❌ 迁移FileDetail {detail.id} 失败: {e}")
    
    print(f"\nFileDetail迁移完成: 成功 {migrated_count}, 失败 {failed_count}")
    return migrated_count, failed_count

def verify_migration():
    """验证迁移结果"""
    print("\n=== 验证迁移结果 ===")
    
    total_analyses = FileAnalysis.objects.count()
    header_analyses = FileAnalysis.objects.filter(analysis_type='header').count()
    detail_analyses = FileAnalysis.objects.filter(analysis_type='single').count()
    
    print(f"总FileAnalysis记录: {total_analyses}")
    print(f"header类型记录: {header_analyses}")
    print(f"single类型记录: {detail_analyses}")
    
    # 显示样本数据
    print("\n样本数据:")
    for analysis in FileAnalysis.objects.all()[:5]:
        print(f"  {analysis} - {analysis.analysis_type} - {analysis.status}")
        if analysis.file_header:
            print(f"    -> FileHeader: {analysis.file_header.id}")
        if analysis.file_detail:
            print(f"    -> FileDetail: {analysis.file_detail.id} (Page {analysis.file_detail.page_number})")
    
    return total_analyses, header_analyses, detail_analyses

def main():
    """主迁移函数"""
    print("开始数据迁移...")
    print("注意: 此操作将清空FileAnalysis表并重新填充数据")
    
    # 询问确认
    # response = input("确认继续? (y/N): ")
    # if response.lower() != 'y':
    #     print("操作已取消")
    #     return
    
    try:
        with transaction.atomic():
            # 1. 清空FileAnalysis表
            clear_fileanalysis_table()
            
            # 2. 迁移FileHeader数据
            header_success, header_failed = migrate_header_data()
            
            # 3. 迁移FileDetail数据
            detail_success, detail_failed = migrate_detail_data()
            
            # 4. 验证迁移结果
            total, header_count, detail_count = verify_migration()
            
            print(f"\n=== 迁移完成 ===")
            print(f"FileHeader: 成功 {header_success}, 失败 {header_failed}")
            print(f"FileDetail: 成功 {detail_success}, 失败 {detail_failed}")
            print(f"总FileAnalysis记录: {total}")
            
            if header_failed == 0 and detail_failed == 0:
                print("🎉 数据迁移完全成功！")
            else:
                print("⚠️ 部分迁移失败，请检查错误信息")
                
    except Exception as e:
        print(f"❌ 迁移过程中发生错误: {e}")
        # 事务会自动回滚

if __name__ == "__main__":
    # 导入Q对象
    from django.db import models
    main()