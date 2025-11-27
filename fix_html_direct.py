#!/usr/bin/env python3

# 直接修复HTML文件中的JavaScript语法错误
import re

# 修复 file_list.html
with open('file_processor/templates/file_processor/file_list.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 viewOriginalFile 函数调用 - 添加缺少的逗号
content = re.sub(
    r'viewOriginalFile\(\{\{ conversion\.pk \}\} \'([^\']+)\'\)',
    r'viewOriginalFile({{ conversion.pk }}, \'\1\')',
    content
)

with open('file_processor/templates/file_processor/file_list.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed file_list.html")

# 修复 file_detail_partial.html
with open('file_processor/templates/file_processor/file_detail_partial.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 showResultData 函数调用 - 添加缺少的逗号
content = re.sub(
    r'showResultData\(\{\{ image\.id \}\} \'([^\']+)\'\)',
    r'showResultData({{ image.id }}, \'\1\')',
    content
)

with open('file_processor/templates/file_processor/file_detail_partial.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed file_detail_partial.html")