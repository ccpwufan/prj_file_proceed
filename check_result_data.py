#!/usr/bin/env python
"""
检查result_data格式
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader

# 获取一个有result_data的样本
header = FileHeader.objects.filter(result_data__isnull=False).exclude(result_data='').first()
if header:
    print('FileHeader ID:', header.id)
    print('Current comments:', header.comments)
    print('result_data (first 800 chars):')
    print(header.result_data[:800])
    print('...')
else:
    print('No FileHeader with result_data found')