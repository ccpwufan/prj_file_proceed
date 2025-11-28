#!/usr/bin/env python
"""
测试URL配置
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from django.urls import reverse

def test_urls():
    """测试URL反向解析"""
    print("=== 测试URL反向解析 ===")
    
    try:
        url1 = reverse('analyze_single_file')
        print(f"✅ analyze_single_file URL: {url1}")
    except Exception as e:
        print(f"❌ analyze_single_file URL错误: {e}")
        return False
    
    try:
        url2 = reverse('analyze_all_files', kwargs={'pk': 1})
        print(f"✅ analyze_all_files URL: {url2}")
    except Exception as e:
        print(f"❌ analyze_all_files URL错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_urls():
        print("🎉 URL配置测试通过！")
    else:
        print("❌ URL配置测试失败！")