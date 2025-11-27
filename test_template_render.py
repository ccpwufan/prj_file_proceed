#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader, FileDetail
from django.template import Template, Context

def test_template_condition():
    print("=== 模板条件测试 ===")
    
    # 获取最新的 FileHeader
    latest_header = FileHeader.objects.last()
    if not latest_header:
        print("没有找到 FileHeader 数据")
        return
    
    images = latest_header.images.all()
    
    # 测试模板条件
    template_content = """
    conversion.status: '{{ conversion.status }}'
    condition check: {% if conversion.status == 'completed' or conversion.status == 'converted' %}PASS{% else %}FAIL{% endif %}
    images count: {{ images|length }}
    """
    
    template = Template(template_content)
    context = Context({
        'conversion': latest_header,
        'images': images
    })
    
    rendered = template.render(context)
    print(rendered)

if __name__ == "__main__":
    test_template_condition()