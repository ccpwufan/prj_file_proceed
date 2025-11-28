#!/usr/bin/env python
"""
测试模板渲染
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileAnalysis
from django.template.loader import render_to_string
from django.contrib.auth.models import User

def test_templates():
    """测试模板渲染"""
    print("=== 测试模板渲染 ===")
    
    # 获取测试数据
    analyses = FileAnalysis.objects.all()[:5]
    user = User.objects.first()
    
    if not analyses.exists():
        print("❌ 没有找到FileAnalysis数据")
        return False
    
    print(f"找到 {analyses.count()} 条FileAnalysis记录")
    
    try:
        # 测试analysis_list模板
        print("\n测试analysis_list模板...")
        html = render_to_string('file_processor/analysis_list.html', {
            'analyses': analyses,
            'user': user
        })
        
        if 'get_analysis_type_display' in html:
            print("✅ analysis_list模板渲染成功，包含analysis_type")
        else:
            print("❌ analysis_list模板可能有问题")
        
        # 测试analysis_detail模板
        print("\n测试analysis_detail模板...")
        analysis = analyses.first()
        html = render_to_string('file_processor/analysis_detail.html', {
            'analysis': analysis,
            'user': user
        })
        
        if 'get_analysis_type_display' in html:
            print("✅ analysis_detail模板渲染成功，包含analysis_type")
        else:
            print("❌ analysis_detail模板可能有问题")
        
        return True
        
    except Exception as e:
        print(f"❌ 模板渲染失败: {e}")
        return False

if __name__ == "__main__":
    test_templates()