#!/usr/bin/env python
import os
import sys
import django
import re
from datetime import datetime

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader

def enhanced_extract_dept_and_name(result_data):
    """
    增强的提取函数，处理更多特殊情况
    """
    if not result_data or not isinstance(result_data, str):
        return []
    
    # 处理result_content，移除think标签
    result_content = result_data
    
    # 处理think标签 - 更健壮的版本
    if 'think' in result_content and '</think>' in result_content:
        # Extract content between think tags
        start_idx = result_content.find('think') + len('think')
        end_idx = result_content.find('</think>', start_idx)
        if end_idx > start_idx:
            think_content = result_content[start_idx:end_idx].strip()
            
            # Remove think section from result content
            result_content = result_content[:result_content.find('think')].strip()
            if result_content.find('think') + len('think') < len(result_content):
                result_content += result_content[result_content.find('think') + len('think'):].strip()
    
    # 从result_content中提取部门和姓名信息
    comments_parts = []
    
    # 更健壮的部门匹配
    dept_patterns = [
        r'(?:部门|dept)\s*[:：]?\s*([^,\n\r]+)',
        r'部门\s*[:：]?\s*([^,\n\r]+)',
        r'费用归属部门\s*[:：]?\s*([^,\n\r]+)',
        r'所属部门\s*[:：]?\s*([^,\n\r]+)',
    ]
    
    for pattern in dept_patterns:
        dept_match = re.search(pattern, result_content, re.IGNORECASE)
        if dept_match:
            department = dept_match.group(1).strip()
            # 清理提取的内容
            department = re.sub(r'[:：,，\s]+$', '', department)
            if department and department not in ['未找到', '无', '没有找到']:
                comments_parts.append(f"部门：{department}")
                break
    
    # 更健壮的姓名匹配
    name_patterns = [
        r'(?:姓名|name)\s*[:：]?\s*([^,\n\r]+)',
        r'报销人\s*[:：]?\s*([^,\n\r]+)',
        r'购买方\s*[:：]?\s*([^,\n\r（]+)',
        r'([A-Za-z\u4e00-\u9fa5]{2,10})\s*（个人）',  # 匹配"XXX（个人）"格式
        r'TO:\s*([A-Za-z\u4e00-\u9fa5]{2,10})',  # 匹配"TO: XXX"格式
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, result_content, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            # 清理提取的内容
            name = re.sub(r'[:：,，（\s]+$', '', name)
            if name and name not in ['未找到', '无', '没有找到', '个人']:
                comments_parts.append(f"姓名：{name}")
                break
    
    return comments_parts

def main():
    print("=== 增强版批量更新脚本 ===")
    
    # 获取需要更新的记录：有result_data但comments为空的记录
    records_to_update = FileHeader.objects.exclude(
        result_data__isnull=True
    ).exclude(
        result_data=''
    ).filter(
        comments__isnull=True
    )
    
    print(f"找到 {records_to_update.count()} 条需要更新的记录")
    
    success_count = 0
    error_count = 0
    
    for header in records_to_update:
        try:
            # 提取信息
            extracted_info = enhanced_extract_dept_and_name(header.result_data)
            
            if extracted_info:
                # 更新comments字段
                new_comments = ", ".join(extracted_info)
                header.comments = new_comments
                
                # 添加日志
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] Enhanced batch update: extracted {new_comments}\n"
                
                # 更新log字段
                current_log = header.log or ""
                header.log = current_log + log_entry
                
                # 保存更改
                header.save()
                
                success_count += 1
                filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
                print(f"✓ 更新成功 - ID:{header.id} 文件:{filename} comments:{new_comments}")
            else:
                filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
                print(f"⚠ 未提取到信息 - ID:{header.id} 文件:{filename}")
                
        except Exception as e:
            error_count += 1
            print(f"✗ 更新失败 - ID:{header.id} 错误:{str(e)}")
    
    print(f"\n=== 更新完成 ===")
    print(f"成功更新：{success_count} 条记录")
    print(f"更新失败：{error_count} 条记录")
    
    # 验证结果
    print("\n=== 最终统计 ===")
    total_records = FileHeader.objects.count()
    records_with_result_data = FileHeader.objects.exclude(
        result_data__isnull=True
    ).exclude(
        result_data=''
    ).count()
    records_with_comments = FileHeader.objects.exclude(
        comments__isnull=True
    ).exclude(
        comments=''
    ).count()
    records_empty_comments = FileHeader.objects.filter(
        comments__isnull=True
    ).count()
    
    print(f"总记录数：{total_records}")
    print(f"有result_data的记录：{records_with_result_data}")
    print(f"有comments的记录：{records_with_comments}")
    print(f"comments为空的记录：{records_empty_comments}")

if __name__ == "__main__":
    main()