#!/usr/bin/env python3
"""
使用pyzxing进行条码解码的测试脚本
将YOLO识别出来的条码区域交给pyzxing解码
显示解码器包名和解码内容
"""
import cv2
import numpy as np
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import YOLO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from ultralytics import YOLO
except ImportError:
    print("❌ 请先安装ultralytics: pip install ultralytics")
    exit(1)

try:
    from pyzxing import BarCodeReader
    PYZXING_AVAILABLE = True
    print("✅ pyzxing 可用")
except ImportError:
    PYZXING_AVAILABLE = False
    print("❌ pyzxing 不可用，请安装: pip install pyzxing")

def decode_with_py zxing_decoder(image):
    """使用pyzxing解码图像"""
    if not PYZXING_AVAILABLE:
        return []
    
    try:
        decoder = BarCodeReader()
        results = decoder.decode(image)
        
        decoded_results = []
        for result in results:
            decoded_info = {
                'decoder': 'pyzxing',
                'package': 'pyzxing (Google ZXing)',
                'type': result.format,
                'data': result.parsed,
                'raw_data': result.raw
            }
            decoded_results.append(decoded_info)
            print(f"      📦 包名: pyzxing (Google ZXing)")
            print(f"      📋 类型: {result.format}")
            print(f"      📄 内容: {result.parsed}")
        
        return decoded_results
        
    except Exception as e:
        print(f"      ❌ pyzxing解码失败: {e}")
        return []

def test_single_image(model_path, image_path):
    """测试单张图像"""
    print(f"\n📷 测试图像: {os.path.basename(image_path)}")
    print("-" * 60)
    
    # 加载YOLO模型
    model = YOLO(model_path)
    
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法读取图像: {image_path}")
        return
    
    # YOLO检测
    try:
        yolo_results = model(image, conf=0.5)
        
        if yolo_results[0].boxes is not None:
            print(f"🎯 YOLO检测到 {len(yolo_results[0].boxes)} 个条码区域")
            
            for i, box in enumerate(yolo_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = model.names[class_id]
                
                print(f"\n  区域 {i+1}:")
                print(f"    类别: {class_name}")
                print(f"    置信度: {confidence:.3f}")
                print(f"    位置: [{int(x1)}, {int(y1)}, {int(x2)}, {int(y2)}]")
                
                # 提取条码区域
                region = image[int(y1):int(y2), int(x1):int(x2)]
                
                if region.size > 0:
                    print(f"    🔍 使用pyzxing解码:")
                    decoded_results = decode_with_py zxing_decoder(region)
                    
                    if not decoded_results:
                        print(f"      ❌ 未能解码该区域")
                else:
                    print(f"      ❌ 区域提取失败")
        else:
            print(f"🎯 YOLO未检测到条码区域")
        
        # 对比全图pyzxing解码
        print(f"\n🔍 对比测试: 全图直接pyzxing解码")
        print("-" * 30)
        full_image_results = decode_with_py zxing_decoder(image)
        
        if not full_image_results:
            print(f"❌ 全图未解码到条码")
            
    except Exception as e:
        print(f"❌ 检测失败: {e}")

def main():
    """主函数"""
    print("🔍 YOLO + pyzxing 条码解码测试")
    print("=" * 60)
    
    if not PYZXING_AVAILABLE:
        print("❌ pyzxing 不可用，请先安装: pip install pyzxing")
        return
    
    # 模型路径
    model_path = "barcode_training/barcode_detector_4060ti/weights/best.pt"
    
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return
    
    # 查找测试图像
    test_dirs = [
        "media/detection_frames",
        "barcode_dataset/images/val", 
        "barcode_dataset/images/test"
    ]
    
    images = []
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                images.extend(Path(test_dir).glob(ext))
    
    if not images:
        print("❌ 未找到测试图像")
        return
    
    # 限制测试图像数量
    test_images = sorted(images)[:3]
    print(f"📁 找到 {len(test_images)} 张测试图像")
    
    # 运行测试
    for image_path in test_images:
        test_single_image(model_path, str(image_path))
    
    print("\n" + "=" * 60)
    print("🎯 测试完成!")

if __name__ == "__main__":
    main()