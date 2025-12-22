#!/usr/bin/env python3
"""
使用pyzxing进行条码解码的测试脚本
将YOLO识别出来的条码区域交给pyzxing解码
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

class YOLOPyzxingDecoder:
    def __init__(self, model_path):
        """初始化YOLO模型和pyzxing解码器"""
        try:
            self.model = YOLO(model_path)
            self.decoder = BarCodeReader() if PYZXING_AVAILABLE else None
            print(f"🎯 YOLO模型加载成功: {model_path}")
            if self.decoder:
                print("🔓 pyzxing解码器初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise

    def preprocess_barcode_region(self, image):
        """预处理条码区域以提高解码成功率"""
        # 增强对比度
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # 降噪
        denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
        
        # 锐化
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        return sharpened

    def decode_with_py zxing(self, region_image):
        """使用pyzxing解码条码区域"""
        if not self.decoder:
            return []
        
        try:
            # 尝试多种预处理
            variants = [
                region_image,  # 原始图像
                self.preprocess_barcode_region(region_image),  # 预处理图像
                cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY),  # 灰度图
            ]
            
            all_results = []
            for i, variant in enumerate(variants):
                try:
                    results = self.decoder.decode(variant)
                    if results:
                        for result in results:
                            decoded_info = {
                                'decoder': 'pyzxing',
                                'package': 'pyzxing (Google ZXing)',
                                'type': result.format,
                                'data': result.parsed,
                                'raw_data': result.raw,
                                'quality': result.quality if hasattr(result, 'quality') else None,
                                'variant': i  # 0:原始, 1:预处理, 2:灰度
                            }
                            all_results.append(decoded_info)
                            print(f"    ✅ pyzxing解码成功: {result.format} | {result.parsed}")
                except Exception as e:
                    continue
            
            return all_results
            
        except Exception as e:
            print(f"    ❌ pyzxing解码失败: {e}")
            return []

    def test_single_image(self, image_path):
        """测试单张图像"""
        print(f"\n📷 测试图像: {os.path.basename(image_path)}")
        
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            return {
                'error': f'无法读取图像: {image_path}',
                'image_path': image_path
            }
        
        # YOLO检测
        try:
            yolo_results = self.model(image, conf=0.5)
            yolo_time = 0.0  # YOLO不提供时间信息
            
            detections = []
            total_decode_time = 0
            
            if yolo_results[0].boxes is not None:
                print(f"  🎯 YOLO检测到 {len(yolo_results[0].boxes)} 个条码区域")
                
                for i, box in enumerate(yolo_results[0].boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    print(f"    区域{i+1} [{class_name}]: 置信度 {confidence:.3f}, 位置 [{int(x1)},{int(y1)},{int(x2)},{int(y2)}]")
                    
                    # 提取条码区域
                    region = image[int(y1):int(y2), int(x1):int(x2)]
                    
                    if region.size > 0:
                        # 使用pyzxing解码
                        start_time = cv2.getTickCount()
                        decoded_results = self.decode_with_py zxing(region)
                        decode_time = (cv2.getTickCount() - start_time) * 1000 / cv2.getTickFrequency()
                        total_decode_time += decode_time
                        
                        detection = {
                            'region_id': i + 1,
                            'class': class_name,
                            'confidence': confidence,
                            'bbox': [float(x1), float(y1), float(x2), float(y2)],
                            'decode_results': decoded_results,
                            'decode_time_ms': decode_time,
                            'decoded_count': len(decoded_results)
                        }
                        
                        # 显示解码结果
                        if decoded_results:
                            for j, result in enumerate(decoded_results):
                                print(f"      📦 解码{j+1}: {result['package']} | {result['type']} | {result['data']}")
                        else:
                            print(f"      ❌ 未能解码该区域")
                        
                        detections.append(detection)
                    else:
                        print(f"      ❌ 区域提取失败")
            else:
                print(f"  🎯 YOLO未检测到条码区域")
            
            # 对比全图pyzxing解码
            print(f"  🔍 对比测试: 全图直接pyzxing解码")
            start_time = cv2.getTickCount()
            full_image_results = self.decode_with_py zxing(image)
            full_image_time = (cv2.getTickCount() - start_time) * 1000 / cv2.getTickFrequency()
            
            if full_image_results:
                print(f"    📦 全图解码结果: {len(full_image_results)} 个条码")
                for result in full_image_results:
                    print(f"      📦 {result['package']} | {result['type']} | {result['data']}")
            else:
                print(f"    ❌ 全图未解码到条码")
            
            return {
                'image_path': image_path,
                'yolo_detections': len(detections),
                'successful_decodes': sum(d['decoded_count'] for d in detections),
                'detections': detections,
                'full_image_results': full_image_results,
                'total_decode_time_ms': total_decode_time,
                'full_image_decode_time_ms': full_image_time,
                'performance': {
                    'avg_decode_time_ms': total_decode_time / max(len(detections), 1),
                    'decode_fps': 1000 / total_decode_time if total_decode_time > 0 else 0
                }
            }
            
        except Exception as e:
            print(f"    ❌ 检测失败: {e}")
            return {
                'error': str(e),
                'image_path': image_path
            }

    def find_test_images(self):
        """查找测试图像"""
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
        
        return sorted(images)[:10]  # 限制测试图像数量

def main():
    """主函数"""
    print("🔍 YOLO + pyzxing 条码解码测试")
    print("=" * 50)
    
    if not PYZXING_AVAILABLE:
        print("❌ pyzxing 不可用，请先安装: pip install pyzxing")
        return
    
    # 模型路径
    model_path = "barcode_training/barcode_detector_4060ti/weights/best.pt"
    
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return
    
    # 初始化解码器
    try:
        decoder = YOLOPyzxingDecoder(model_path)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    # 查找测试图像
    test_images = decoder.find_test_images()
    
    if not test_images:
        print("❌ 未找到测试图像")
        return
    
    print(f"📁 找到 {len(test_images)} 张测试图像")
    
    # 运行测试
    all_results = []
    total_images = 0
    total_yolo_detections = 0
    total_successful_decodes = 0
    
    for image_path in test_images:
        result = decoder.test_single_image(str(image_path))
        all_results.append(result)
        
        if 'error' not in result:
            total_images += 1
            total_yolo_detections += result.get('yolo_detections', 0)
            total_successful_decodes += result.get('successful_decodes', 0)
    
    # 保存结果
    output_file = f'pyzxing_decode_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    summary = {
        'test_time': datetime.now().isoformat(),
        'decoder_info': {
            'name': 'pyzxing',
            'package': 'pyzxing (Google ZXing Python Wrapper)',
            'backend': 'Google ZXing Java Library'
        },
        'summary': {
            'total_images_tested': total_images,
            'total_yolo_detections': total_yolo_detections,
            'total_successful_decodes': total_successful_decodes,
            'decode_success_rate': total_successful_decodes / max(total_yolo_detections, 1),
            'avg_decode_time_per_region': np.mean([r.get('performance', {}).get('avg_decode_time_ms', 0) for r in all_results if 'performance' in r])
        },
        'detailed_results': all_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 50)
    print("📊 测试总结")
    print("=" * 50)
    print(f"🎯 测试图像数: {total_images}")
    print(f"🔍 YOLO检测总数: {total_yolo_detections}")
    print(f"✅ 成功解码数: {total_successful_decodes}")
    print(f"📈 解码成功率: {total_successful_decodes / max(total_yolo_detections, 1) * 100:.1f}%")
    print(f"💾 详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()