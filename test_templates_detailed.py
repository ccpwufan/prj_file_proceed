#!/usr/bin/env python
"""
详细测试模板渲染
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
from django.template import RequestContext

def test_templates_detailed():
    """详细测试模板渲染"""
    print("=== 详细测试模板渲染 ===")
    
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
        analysis = analyses.first()
        print(f"测试分析记录: {analysis}")
        print(f"analysis_type: {analysis.analysis_type}")
        print(f"get_analysis_type_display(): {analysis.get_analysis_type_display()}")
        
        # 简单测试模板片段
        template_content = """
        Analysis Type: {{ analysis.get_analysis_type_display }}
        Status: {{ analysis.get_status_display }}
        """
        
        from django.template import Template, Context
        template = Template(template_content)
        context = Context({'analysis': analysis})
        rendered = template.render(context)
        
        print(f"模板渲染结果: {rendered}")
        
        if 'get_analysis_type_display' in rendered:
            print("✅ 模板片段渲染成功")
        else:
            print("❌ 模板片段渲染失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 模板渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_templates_detailed()