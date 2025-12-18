#!/usr/bin/env python3
"""
简化的YOLO训练启动脚本
"""
import os
import sys

# 设置环境变量
os.environ['PYTHONPATH'] = '/app:' + os.environ.get('PYTHONPATH', '')

try:
    # 导入并运行训练脚本
    sys.path.append('/app/yolo_train_scripts')
    from train_barcode_yolo import train_barcode_model
    
    print("开始YOLO条码检测模型训练...")
    results = train_barcode_model()
    print("训练完成!")
    print(results)
    
except Exception as e:
    print(f"训练过程中出现错误: {e}")
    import traceback
    traceback.print_exc()