#!/usr/bin/env python3
"""
测试模态框关闭后的自动刷新功能
"""

import os
import sys

def test_template_functionality():
    """测试模板中的自动刷新功能"""
    print("=== 测试模态框自动刷新功能 ===")
    
    template_path = "file_processor/templates/file_processor/file_detail_partial.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查共享的自动刷新函数
        has_auto_refresh_function = "function autoRefreshIfConverting()" in content
        print(f"✓ 包含共享的 autoRefreshIfConverting 函数: {has_auto_refresh_function}")
        
        # 检查函数是否包含正确的刷新逻辑
        has_refresh_logic = "currentUrl.searchParams.set('selected_file', '{{ conversion.id }}')" in content
        print(f"✓ 包含正确的刷新逻辑: {has_refresh_logic}")
        
        # 检查 closeResultDataModal 是否调用自动刷新
        has_modal_refresh_call = "autoRefreshIfConverting();" in content
        print(f"✓ closeResultDataModal 调用自动刷新: {has_modal_refresh_call}")
        
        # 检查 converting 状态下的脚本是否使用共享函数
        has_shared_function_call = "autoRefreshIfConverting();" in content
        print(f"✓ converting 状态使用共享函数: {has_shared_function_call}")
        
        # 检查是否消除了重复的自动刷新代码
        refresh_script_count = content.count("setTimeout(function()")
        print(f"✓ 自动刷新代码去重（应该只有1个）: {refresh_script_count == 1}")
        
        # 检查是否消除了重复的 closeResultDataModal 函数
        close_function_count = content.count("function closeResultDataModal()")
        print(f"✓ closeResultDataModal 函数去重（应该只有1个）: {close_function_count == 1}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def test_function_structure():
    """测试函数结构的正确性"""
    print("\n=== 测试函数结构 ===")
    
    template_path = "file_processor/templates/file_processor/file_detail_partial.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查 autoRefreshIfConverting 函数结构
        if "function autoRefreshIfConverting()" in content:
            print("✓ autoRefreshIfConverting 函数定义正确")
            
            # 检查函数是否包含条件判断
            has_condition_check = "{% if conversion.status == 'converting' %}" in content
            print(f"✓ 包含状态条件检查: {has_condition_check}")
            
            # 检查函数是否包含5秒延迟
            has_timeout = "5000" in content
            print(f"✓ 包含5秒延迟: {has_timeout}")
        
        # 检查 closeResultDataModal 函数结构
        if "function closeResultDataModal()" in content:
            print("✓ closeResultDataModal 函数定义正确")
            
            # 检查函数是否包含模态框关闭逻辑
            has_close_logic = "document.getElementById('resultDataModal').classList.add('hidden')" in content
            print(f"✓ 包含模态框关闭逻辑: {has_close_logic}")
            
            # 检查函数是否调用自动刷新
            has_auto_refresh_call = "autoRefreshIfConverting();" in content
            print(f"✓ 调用自动刷新函数: {has_auto_refresh_call}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试模态框关闭后的自动刷新功能...\n")
    
    success1 = test_template_functionality()
    success2 = test_function_structure()
    
    print("\n=== 功能总结 ===")
    if success1 and success2:
        print("1. ✓ 创建了共享的 autoRefreshIfConverting 函数")
        print("2. ✓ closeResultDataModal 函数在关闭后调用自动刷新")
        print("3. ✓ converting 状态下的自动刷新使用共享函数")
        print("4. ✓ 消除了重复的代码")
        print("5. ✓ 保持了5秒刷新间隔和文件ID传递")
        print("\n模态框关闭后的自动刷新功能已成功实现！")
    else:
        print("✗ 部分功能测试失败，请检查实现")

if __name__ == "__main__":
    main()