#!/usr/bin/env python
"""
简化版QReader + YOLO测试脚本
直接测试指定图像，避免长时间等待下载
"""
import cv2
import json
import time
import os
from datetime import datetime

def test_qreader_basic():
    """基础QReader测试"""
    try:
        from qreader import QReader
        print("✅ QReader导入成功")
        
        # 创建QReader实例
        qreader = QReader()
        print("✅ QReader实例创建成功")
        
        return True, qreader
    except Exception as e:
        print(f"❌ QReader测试失败: {e}")
        return False, None

def test_qreader_with_image(qreader, image_path):
    """使用QReader测试单张图像"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 无法加载图像: {image_path}")
            return []
        
        print(f"🔍 使用QReader解码: {os.path.basename(image_path)}")
        start_time = time.time()
        
        # 直接解码整个图像
        decoded_text = qreader.detect_and_decode(image=image)
        decode_time = (time.time() - start_time) * 1000
        
        results = []
        for i, text in enumerate(decoded_text):
            if text:
                results.append({
                    'data': text,
                    'decoder': 'QReader',
                    'index': i
                })
        
        print(f"  ⏱️ 解码耗时: {decode_time:.1f}ms")
        
        if results:
            print(f"  ✅ 解码成功，找到 {len(results)} 个条码:")
            for result in results:
                print(f"    📄 {result['data']}")
        else:
            print(f"  ❌ 未解码到条码")
        
        return results
        
    except Exception as e:
        print(f"  ❌ QReader解码错误: {e}")
        return []

def test_yolo_with_qreader(yolo_path, image_path, qreader):
    """测试YOLO + QReader组合"""
    try:
        from ultralytics import YOLO
        
        print(f"\n🎯 YOLO + QReader 组合测试")
        print(f"图像: {os.path.basename(image_path)}")
        print("-" * 50)
        
        # 加载YOLO模型
        model = YOLO(yolo_path)
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 无法加载图像: {image_path}")
            return {}
        
        # YOLO检测
        start_time = time.time()
        results = model(image, conf=0.3)
        yolo_time = (time.time() - start_time) * 1000
        
        detections = []
        if results[0].boxes is not None:
            print(f"🎯 YOLO检测到 {len(results[0].boxes)} 个区域 ({yolo_time:.1f}ms)")
            
            for i, box in enumerate(results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = model.names[class_id]
                
                print(f"\n  区域 {i+1}:")
                print(f"    类别: {class_name}")
                print(f"    置信度: {conf:.3f}")
                print(f"    位置: [{int(x1)}, {int(y1)}, {int(x2)}, {int(y2)}]")
                
                # 提取区域
                roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # QReader解码
                decode_start = time.time()
                decoded_results = []
                try:
                    decoded_text = qreader.detect_and_decode(image=roi)
                    for j, text in enumerate(decoded_text):
                        if text:
                            decoded_results.append({
                                'data': text,
                                'decoder': 'QReader',
                                'index': j
                            })
                except Exception as e:
                    print(f"    ❌ QReader解码错误: {e}")
                
                decode_time = (time.time() - decode_start) * 1000
                
                print(f"    🔍 QReader解码 ({decode_time:.1f}ms):")
                if decoded_results:
                    for decoded in decoded_results:
                        print(f"      ✅ {decoded['data']}")
                else:
                    print(f"      ❌ 未能解码")
                
                detections.append({
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'class': class_name,
                    'confidence': conf,
                    'decoded_count': len(decoded_results),
                    'decoded_data': decoded_results
                })
        else:
            print("❌ YOLO未检测到条码区域")
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            'image_path': image_path,
            'detections': detections,
            'yolo_time_ms': yolo_time,
            'total_time_ms': total_time
        }
        
    except Exception as e:
        print(f"❌ YOLO + QReader测试错误: {e}")
        return {}

def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 QReader + YOLO 条码解码测试")
    print("=" * 60)
    
    # 测试QReader基础功能
    print("\n1️⃣ 测试QReader基础功能")
    print("-" * 30)
    qreader_available, qreader = test_qreader_basic()
    
    if not qreader_available:
        print("❌ QReader不可用，测试终止")
        return
    
    # 查找测试图像
    test_images = []
    possible_paths = [
        'complex_test_barcode.jpg',
        'barcode_dataset/images/val/complex_test_barcode.jpg',
        'media/detection_frames/complex_test_barcode.jpg'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            test_images.append(path)
            break
    
    if not test_images:
        print("❌ 没有找到测试图像")
        return
    
    image_path = test_images[0]
    print(f"\n📷 使用测试图像: {image_path}")
    
    # 2️⃣ QReader直接解码测试
    print(f"\n2️⃣ QReader直接解码测试")
    print("-" * 30)
    direct_results = test_qreader_with_image(qreader, image_path)
    
    # 3️⃣ YOLO + QReader组合测试
    print(f"\n3️⃣ YOLO + QReader组合测试")
    print("-" * 30)
    
    # 查找YOLO模型
    yolo_models = [
        'barcode_training/barcode_detector_4060ti/weights/best.pt',
        'barcode_training/barcode_detector_v2/weights/best.pt',
        'yolov8n.pt'
    ]
    
    yolo_model = None
    for model_path in yolo_models:
        if os.path.exists(model_path):
            yolo_model = model_path
            break
    
    if not yolo_model:
        print("❌ 没有找到YOLO模型")
    else:
        print(f"🔄 使用YOLO模型: {yolo_model}")
        combined_results = test_yolo_with_qreader(yolo_model, image_path, qreader)
    
    # 4️⃣ 保存测试结果
    print(f"\n4️⃣ 保存测试结果")
    print("-" * 30)
    
    test_report = {
        'test_info': {
            'timestamp': datetime.now().isoformat(),
            'qreader_available': qreader_available,
            'test_image': image_path,
            'yolo_model': yolo_model
        },
        'direct_qreader_results': {
            'success_count': len(direct_results),
            'results': direct_results
        },
        'combined_results': combined_results if 'combined_results' in locals() else None
    }
    
    output_file = f'qreader_simple_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_report, f, indent=2, ensure_ascii=False)
    
    print(f"💾 测试报告保存到: {output_file}")
    
    # 5️⃣ 总结
    print(f"\n5️⃣ 测试总结")
    print("-" * 30)
    print(f"QReader直接解码: {len(direct_results)} 个条码")
    
    if 'combined_results' in locals() and combined_results:
        total_detections = len(combined_results.get('detections', []))
        successful_decodes = sum(1 for d in combined_results.get('detections', []) if d.get('decoded_count', 0) > 0)
        print(f"YOLO检测区域: {total_detections} 个")
        print(f"QReader区域解码: {successful_decodes} 个成功")
        if total_detections > 0:
            print(f"区域解码成功率: {successful_decodes/total_detections:.1%}")
    
    print("\n✅ 测试完成!")

if __name__ == "__main__":
    main()