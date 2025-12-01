#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader

def main():
    print("=== 调试未更新记录的result_data ===")
    
    # 检查有result_data但comments为空的记录
    not_updated_with_data = FileHeader.objects.filter(
        comments__isnull=True
    ).exclude(
        result_data__isnull=True
    ).exclude(
        result_data=''
    )
    
    for header in not_updated_with_data:
        filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
        print(f"\n=== ID: {header.id} - {filename} ===")
        print(f"result_data长度: {len(header.result_data)}")
        print(f"result_data内容:")
        print("-" * 50)
        print(header.result_data[:500])  # 只显示前500字符
        if len(header.result_data) > 500:
            print("...(内容被截断)")
        print("-" * 50)
        
        # 测试提取逻辑
        import re
        result_content = header.result_data
        
        # 处理think标签
        if 'think' in result_content and '</think>' in result_content:
            start_idx = result_content.find('think') + len('think')
            end_idx = result_content.find('</think>', start_idx)
            think_content = result_content[start_idx:end_idx].strip()
            result_content = result_content[:result_content.find('think')].strip()
            if result_content.find('think') + len('think') < len(result_content):
                result_content += result_content[result_content.find('think') + len('think'):].strip()
        
        print(f"\n处理后的result_content:")
        print("-" * 30)
        print(result_content[:300])
        print("-" * 30)
        
        # 测试正则表达式
        dept_match = re.search(r'(?:部门|dept)\s*[:：]?\s*([^,\n\r]+)', result_content, re.IGNORECASE)
        name_match = re.search(r'(?:姓名|name)\s*[:：]?\s*([^,\n\r]+)', result_content, re.IGNORECASE)
        
        print(f"部门匹配: {dept_match.group(1) if dept_match else 'None'}")
        print(f"姓名匹配: {name_match.group(1) if name_match else 'None'}")

if __name__ == "__main__":
    main()