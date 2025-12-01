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

def extract_dept_and_name_from_result_data(result_data):
    """
    从result_data中提取部门和姓名信息
    严格参考views.py中的逻辑
    """
    if not result_data or not isinstance(result_data, str):
        return []
    
    # 处理result_content，移除think标签
    result_content = result_data
    if 'think' in result_data and '</think>' in result_data:
        # Extract content between think tags
        start_idx = result_data.find('<think>') + len('<think>')
        end_idx = result_data.find('</think>', start_idx)
        think_content = result_data[start_idx:end_idx].strip()
        
        # Remove think section from result content
        result_content = result_data[:result_data.find('<think>')].strip()
        if result_data.find('</think>') + len('</think>') < len(result_data):
            result_content += result_data[result_data.find('</think>') + len('</think>'):].strip()
    
    # 从result_content中提取部门和姓名信息
    comments_parts = []
    
    # 更健壮的版本，处理关键词可能缺失的情况
    dept_match = re.search(r'(?:部门|dept)\s*[:：]?\s*([^,\n\r]+)', result_content, re.IGNORECASE)
    if dept_match:
        department = dept_match.group(1).strip()
        comments_parts.append(f"部门：{department}")

    name_match = re.search(r'(?:姓名|name)\s*[:：]?\s*([^,\n\r]+)', result_content, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
        comments_parts.append(f"姓名：{name}")
    
    return comments_parts

def preview_updates():
    """
    预览将要更新的记录
    """
    print("=== 预览更新内容 ===")
    print(f"{'ID':<5} {'文件名':<30} {'当前comments':<20} {'提取的信息':<30}")
    print("-" * 85)
    
    # 获取需要更新的记录：有result_data但comments为空的记录
    records_to_update = FileHeader.objects.exclude(
        result_data__isnull=True
    ).exclude(
        result_data=''
    ).filter(
        comments__isnull=True
    )
    
    update_count = 0
    for header in records_to_update:
        # 提取信息
        extracted_info = extract_dept_and_name_from_result_data(header.result_data)
        new_comments = ", ".join(extracted_info) if extracted_info else ""
        
        # 显示文件名（只显示basename）
        filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
        current_comments = header.comments or ""
        
        print(f"{header.id:<5} {filename[:28]:<30} {current_comments[:18]:<20} {new_comments[:28]:<30}")
        
        if extracted_info:
            update_count += 1
    
    print(f"\n需要更新的记录数：{update_count}")
    return records_to_update, update_count

def execute_batch_update(records_to_update):
    """
    执行批量更新
    """
    print("\n=== 开始执行批量更新 ===")
    
    success_count = 0
    error_count = 0
    
    for header in records_to_update:
        try:
            # 提取信息
            extracted_info = extract_dept_and_name_from_result_data(header.result_data)
            
            if extracted_info:
                # 更新comments字段
                new_comments = ", ".join(extracted_info)
                header.comments = new_comments
                
                # 添加日志
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] Batch update: extracted {new_comments}\n"
                
                # 更新log字段
                current_log = header.log or ""
                header.log = current_log + log_entry
                
                # 保存更改
                header.save()
                
                success_count += 1
                filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
                print(f"✓ 更新成功 - ID:{header.id} 文件:{filename} comments:{new_comments}")
            else:
                print(f"⚠ 未提取到信息 - ID:{header.id}")
                
        except Exception as e:
            error_count += 1
            print(f"✗ 更新失败 - ID:{header.id} 错误:{str(e)}")
    
    print(f"\n=== 更新完成 ===")
    print(f"成功更新：{success_count} 条记录")
    print(f"更新失败：{error_count} 条记录")
    
    return success_count, error_count

def verify_results():
    """
    验证更新结果
    """
    print("\n=== 验证更新结果 ===")
    
    # 统计更新后的状态
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
    
    # 显示部分更新后的记录
    print("\n=== 更新后的记录示例 ===")
    updated_records = FileHeader.objects.exclude(
        comments__isnull=True
    ).exclude(
        comments=''
    )[:5]  # 只显示前5条
    
    print(f"{'ID':<5} {'文件名':<30} {'comments':<40}")
    print("-" * 75)
    
    for header in updated_records:
        filename = os.path.basename(header.file_header_filename.name) if header.file_header_filename else "N/A"
        comments = header.comments or ""
        print(f"{header.id:<5} {filename[:28]:<30} {comments[:38]:<40}")

def main():
    """
    主函数
    """
    print("批量更新FileHeader.comments脚本")
    print("=" * 50)
    
    # 第一步：预览更新内容
    records_to_update, update_count = preview_updates()
    
    if update_count == 0:
        print("没有需要更新的记录。")
        return
    
    # 询问用户是否继续
    print(f"\n确认要执行批量更新吗？(y/n): ", end="")
    user_input = input().strip().lower()
    
    if user_input not in ['y', 'yes', '是']:
        print("用户取消操作。")
        return
    
    # 第二步：执行批量更新
    success_count, error_count = execute_batch_update(records_to_update)
    
    # 第三步：验证结果
    verify_results()
    
    print(f"\n批量更新脚本执行完成！")

if __name__ == "__main__":
    main()