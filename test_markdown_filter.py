#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

try:
    from file_processor.templatetags.markdown_filters import markdown
    print('✅ markdown_filters 模块导入成功')
    
    # 测试markdown过滤器
    test_markdown = "# Test Header\n\nThis is a **bold** text."
    result = markdown(test_markdown)
    print(f'✅ markdown过滤器测试成功: {len(result)} 字符的HTML输出')
    
except Exception as e:
    print(f'❌ 错误: {e}')