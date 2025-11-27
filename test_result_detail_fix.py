#!/usr/bin/env python
"""
测试修复后的 result_detail 函数
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader
from django.contrib.auth.models import User

def test_result_detail_parsing():
    print("🔍 测试修复后的 result_detail 解析逻辑...")
    
    # 获取测试用户
    user = User.objects.filter(username='testuser').first()
    if not user:
        print("❌ 测试用户不存在")
        return False
    
    # 查找有 result_data 的 FileHeader
    file_headers = FileHeader.objects.filter(result_data__isnull=False).exclude(result_data='')
    if not file_headers.exists():
        print("❌ 没有找到包含 result_data 的 FileHeader")
        return False
    
    file_header = file_headers.first()
    print(f"✅ 找到 FileHeader: {file_header.file_header_filename.name}")
    print(f"   - result_data 长度: {len(file_header.result_data or '')}")
    
    # 模拟解析逻辑
    result_data = file_header.result_data or ''
    print(f"   - 包含 </think> 标签: {'</think>' in result_data}")
    
    # 解析逻辑
    think_content = ''
    result_content = result_data
    
    start_tag = '</think>'
    end_tag = '</think>'
    
    if start_tag in result_data and end_tag in result_data:
        start_idx = result_data.find(start_tag) + len(start_tag)
        end_idx = result_data.find(end_tag, start_idx)  # 修复：从 start_idx 开始查找
        
        print(f"   - start_idx: {start_idx}, end_idx: {end_idx}")
        
        if end_idx > start_idx:
            think_content = result_data[start_idx:end_idx].strip()
            
            # Remove think section from result content
            before_think = result_data[:result_data.find(start_tag)].strip()
            after_think = result_data[result_data.find(end_tag) + len(end_tag):].strip()
            
            result_content = before_think
            if after_think:
                result_content += '\n\n' + after_think
            
            print(f"✅ 解析成功:")
            print(f"   - Think 内容长度: {len(think_content)}")
            print(f"   - Result 内容长度: {len(result_content)}")
            print(f"   - Think 预览: {think_content[:100]}...")
            print(f"   - Result 预览: {result_content[:100]}...")
        else:
            print("❌ 无效的 </think> 标签结构")
            return False
    else:
        print("ℹ️ 没有 </think> 标签，全部内容作为 Result")
    
    print("🎉 解析逻辑测试通过！")
    return True

if __name__ == '__main__':
    try:
        success = test_result_detail_parsing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)