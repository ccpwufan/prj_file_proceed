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

def manual_extract_for_special_cases(result_data, record_id):
    """
    针对特殊记录的手动提取逻辑
    """
    if not result_data or not isinstance(result_data, str):
        return []
    
    comments_parts = []
    
    # 处理think标签
    result_content = result_data
    if 'think' in result_content and '</think>' in result_content:
        start_idx = result_content.find('think') + len('think')
        end_idx = result_content.find('</think>', start_idx)
        if end_idx > start_idx:
            result_content = result_content[:result_content.find('think')].strip()
            if result_content.find('think') + len('think') < len(result_content):
                result_content += result_content[result_content.find('think') + len('think'):].strip()
    
    if record_id == 1:
        # ID 1: 发票记录，购买方是陈正华
        name_match = re.search(r'购买方是([A-Za-z\u4e00-\u9fa5]{2,10})（个人）', result_content)
        if name_match:
            name = name_match.group(1).strip()
            comments_parts.append(f"姓名：{name}")
        
        # 发票中没有明确的部门信息
        comments_parts.append("部门：未找到")
    
    elif record_id == 32:
        # ID 32: 去哪儿网酒店账单
        # 查找TO:格式的人名
        name_match = re.search(r'TO:\s*([A-Za-z\u4e00-\u9fa5]{2,10})', result_content)
        if name_match:
            name = name_match.group(1).strip()
            comments_parts.append(f"姓名：{name}")
        
        # 查找部门信息
        dept_match = re.search(r'部门\s*[:：]?\s*([^,\n\r]+)', result_content)
        if dept_match:
            dept = dept_match.group(1).strip()
            if dept and dept not in ['未找到', '无', '没有找到']:
                comments_parts.append(f"部门：{dept}")
            else:
                comments_parts.append("部门：未找到")
        else:
            comments_parts.append("部门：未找到")
    
    elif record_id == 33:
        # ID 33: 错误记录，没有有效信息
        comments_parts.append("部门：处理失败")
        comments_parts.append("姓名：处理失败")
    
    return comments_parts

def main():
    print("=== 手动更新剩余记录 ===")
    
    # 获取需要更新的记录：有result_data但comments为空的记录
    records_to_update = FileHeader.objects.exclude(
        result_data__isnull=True
    ).exclude(
        result_data=''
    ).filter(
        comments__isnull=True
    )
    
    print(f"找到 {records_to_update.count()} 条需要手动更新的记录")
    
    success_count = 0
    error_count = 0
    
    for header in records_to_update:
        try:
            # 提取信息
            extracted_info = manual_extract_for_special_cases(header.result_data, header.id)
            
            if extracted_info:
                # 更新comments字段
                new_comments = ", ".join(extracted_info)
                header.comments = new_comments
                
                # 添加日志
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] Manual batch update: extracted {new_comments}\n"
                
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
    
    # 最终验证
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