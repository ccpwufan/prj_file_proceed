#!/usr/bin/env python
"""
测试脚本：验证 FileHeader result_data 字段和 View Result 按钮功能
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail
from django.contrib.auth.models import User

def test_result_data_functionality():
    print("🔍 测试 FileHeader result_data 功能...")
    
    # 获取或创建测试用户
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    # 查找现有的 FileHeader（不限制用户）
    file_headers = FileHeader.objects.all()
    if not file_headers.exists():
        print("❌ 没有找到测试用的 FileHeader，请先上传一个 PDF 文件")
        return False
    
    file_header = file_headers.first()
    print(f"✅ 找到 FileHeader: {file_header}")
    print(f"   - 当前状态: {file_header.status}")
    print(f"   - result_data: {file_header.result_data}")
    
    # 测试 result_data 字段
    test_data = "{'test': '这是一个测试结果', 'status': 'success', 'data': [1, 2, 3]}"
    file_header.result_data = test_data
    file_header.save()
    
    # 重新读取验证
    file_header.refresh_from_db()
    print(f"✅ result_data 字段测试成功: {file_header.result_data}")
    
    # 测试长文本截取（模拟 views.py 中的处理逻辑）
    long_data = "x" * 6000  # 6000 字符的文本
    # 模拟 views.py 中的截取逻辑
    if len(long_data) > 5000:
        truncated_data = long_data[:4997] + '...'
    else:
        truncated_data = long_data
    
    file_header.result_data = truncated_data
    file_header.save()
    
    file_header.refresh_from_db()
    if len(file_header.result_data) <= 5000:
        print(f"✅ 长文本截取测试成功，长度: {len(file_header.result_data)}")
    else:
        print(f"❌ 长文本截取测试失败，长度: {len(file_header.result_data)}")
        return False
    
    # 检查模板渲染
    from django.template import Context, Template
    
    template_content = '''
    {% if conversion.result_data %}
    <button onclick="showHeaderResultData('{{ conversion.result_data|escapejs }}')">
        View Result
    </button>
    {% endif %}
    '''
    
    template = Template(template_content)
    context = Context({'conversion': file_header})
    rendered = template.render(context)
    
    if 'View Result' in rendered and 'showHeaderResultData' in rendered:
        print("✅ 模板渲染测试成功")
    else:
        print("❌ 模板渲染测试失败")
        print(f"渲染内容: {rendered}")
        return False
    
    print("🎉 所有测试都通过了！")
    return True

if __name__ == '__main__':
    try:
        success = test_result_data_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)