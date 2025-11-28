#!/usr/bin/env python
"""
测试修改后的FileAnalysis功能
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

def test_fileanalysis_model():
    """测试FileAnalysis模型的新字段"""
    print("=== 测试FileAnalysis模型 ===")
    
    # 检查模型字段是否存在
    try:
        # 测试字段访问
        analysis_type_choices = FileAnalysis._meta.get_field('analysis_type').choices
        status_choices = FileAnalysis._meta.get_field('status').choices
        
        print(f"✅ analysis_type字段存在，选项: {analysis_type_choices}")
        print(f"✅ status字段存在，选项: {status_choices}")
        
        # 检查外键字段
        file_header_field = FileAnalysis._meta.get_field('file_header')
        file_detail_field = FileAnalysis._meta.get_field('file_detail')
        api_key_field = FileAnalysis._meta.get_field('api_key_used')
        
        print(f"✅ file_header字段存在: {file_header_field}")
        print(f"✅ file_detail字段存在: {file_detail_field}")
        print(f"✅ api_key_used字段存在: {api_key_field}")
        
        # 检查旧的files字段是否已删除
        try:
            files_field = FileAnalysis._meta.get_field('files')
            print(f"❌ files字段仍然存在，应该被删除: {files_field}")
        except:
            print("✅ files字段已成功删除")
            
        return True
        
    except Exception as e:
        print(f"❌ 模型字段检查失败: {e}")
        return False

def test_create_analysis():
    """测试创建FileAnalysis记录"""
    print("\n=== 测试创建FileAnalysis记录 ===")
    
    try:
        # 获取测试用户
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return False
        
        # 获取一个FileHeader和FileDetail
        file_header = FileHeader.objects.first()
        file_detail = FileDetail.objects.first()
        
        if not file_header:
            print("❌ 没有找到FileHeader记录")
            return False
            
        # 测试创建header类型的分析记录
        header_analysis = FileAnalysis.objects.create(
            user=user,
            file_header=file_header,
            analysis_type='header',
            status='processing',
            api_key_used='test_api_key_header'
        )
        print(f"✅ 创建header类型分析记录成功: {header_analysis}")
        
        if file_detail:
            # 测试创建single类型的分析记录
            single_analysis = FileAnalysis.objects.create(
                user=user,
                file_detail=file_detail,
                analysis_type='single',
                status='completed',
                api_key_used='test_api_key_single',
                result_data='{"test": "result"}'
            )
            print(f"✅ 创建single类型分析记录成功: {single_analysis}")
        
        # 测试查询
        header_analyses = FileAnalysis.objects.filter(analysis_type='header')
        single_analyses = FileAnalysis.objects.filter(analysis_type='single')
        
        print(f"✅ 查询到{header_analyses.count()}条header类型记录")
        print(f"✅ 查询到{single_analyses.count()}条single类型记录")
        
        # 清理测试数据
        header_analysis.delete()
        if 'single_analysis' in locals():
            single_analysis.delete()
            
        print("✅ 测试数据清理完成")
        return True
        
    except Exception as e:
        print(f"❌ 创建分析记录失败: {e}")
        return False

def test_model_methods():
    """测试模型方法"""
    print("\n=== 测试模型方法 ===")
    
    try:
        user = User.objects.first()
        file_header = FileHeader.objects.first()
        
        if not user or not file_header:
            print("❌ 缺少测试数据")
            return False
        
        # 创建测试记录
        analysis = FileAnalysis.objects.create(
            user=user,
            file_header=file_header,
            analysis_type='header',
            status='processing'
        )
        
        # 测试__str__方法
        str_repr = str(analysis)
        print(f"✅ __str__方法输出: {str_repr}")
        
        # 测试choices
        expected_types = ['single', 'header']
        actual_types = [choice[0] for choice in FileAnalysis._meta.get_field('analysis_type').choices]
        
        if set(expected_types) == set(actual_types):
            print(f"✅ analysis_type选项正确: {actual_types}")
        else:
            print(f"❌ analysis_type选项不匹配，期望: {expected_types}, 实际: {actual_types}")
        
        expected_statuses = ['processing', 'completed', 'failed']
        actual_statuses = [choice[0] for choice in FileAnalysis._meta.get_field('status').choices]
        
        if set(expected_statuses) == set(actual_statuses):
            print(f"✅ status选项正确: {actual_statuses}")
        else:
            print(f"❌ status选项不匹配，期望: {expected_statuses}, 实际: {actual_statuses}")
        
        # 清理
        analysis.delete()
        return True
        
    except Exception as e:
        print(f"❌ 模型方法测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试修改后的FileAnalysis功能...\n")
    
    tests = [
        test_fileanalysis_model,
        test_create_analysis,
        test_model_methods
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！FileAnalysis模型修改成功。")
    else:
        print("❌ 部分测试失败，请检查修改。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)