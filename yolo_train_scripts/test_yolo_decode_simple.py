#!/usr/bin/env python
"""
简化版YOLO + 条码解码测试脚本
专为Docker环境设计，最小依赖，快速测试
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob

# Simple fallback decoder if pyzbar/pyzxing not available
class SimpleBarcodeDecoder:
    def __init__(self):
        self.name = "simple_fallback"
    
    def decode(self, image):
        """Simple placeholder decoder - in real implementation would use pyzbar/pyzxing"""
        # This is just a placeholder to show the structure
        return []

def install_and_import_decoder():
    """Try to install and import decoders"""
    decoders = {}
    
    # Try pyzbar
    try:
        from pyzbar import pyzbar
        decoders['pyzbar'] = pyzbar
        print("✅ pyzbar available")
    except ImportError:
        print("⚠️ pyzbar not available - install with: pip install pyzbar")
    
    # Try pyzxing
    try:
        from pyzxing import BarCodeReader
        decoders['pyzxing'] = BarCodeReader()
        print("✅ pyzxing available")
    except ImportError:
        print("⚠️ pyzxing not available - install with: pip install pyzxing")
    
    return decoders

class SimpleYoloDecodeTester:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.decoders = install_and_import_decoder()
        self.test_images = self.find_test_images()
        
        print(f"=== 简化YOLO + 解码测试器 ===")
        print(f"模型: {model_path}")
        print(f"图像: {len(self.test_images)} 张")
        print(f"解码器: {list(self.decoders.keys())}")
    
    def find_test_images(self):
        """找测试图像"""
        images = []
        for pattern in ['*.jpg', 'barcode_dataset/images/val/*.jpg']:
            images.extend(glob.glob(pattern))
        return images[:5]  # 最多测试5张
    
    def decode_region(self, image, decoder_name):
        """使用指定解码器解码图像区域"""
        if decoder_name not in self.decoders:
            return []
        
        try:
            if decoder_name == 'pyzbar':
                decoded = self.decoders[decoder_name].decode(image)
                return [{
                    'type': obj.type,
                    'data': obj.data.decode('utf-8'),
                    'decoder': 'pyzbar'
                } for obj in decoded]
            
            elif decoder_name == 'pyzxing':
                decoded = self.decoders[decoder_name].decode(image)
                return [{
                    'type': obj.format,
                    'data': obj.parsed,
                    'decoder': 'pyzxing'
                } for obj in decoded if obj.parsed]
        
        except Exception as e:
            print(f"  ❌ {decoder_name} 解码错误: {e}")
        
        return []
    
    def test_one_image(self, image_path):
        """测试单张图像"""
        print(f"\n📷 测试: {os.path.basename(image_path)}")
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            return {'error': f'Cannot load {image_path}'}
        
        # YOLO检测
        start_time = time.time()
        results = self.model(image, conf=0.3)
        yolo_time = (time.time() - start_time) * 1000
        
        detections = []
        if results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                
                # 提取区域
                roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # 尝试所有可用解码器
                decoded_results = []
                for decoder_name in self.decoders:
                    decoded = self.decode_region(roi, decoder_name)
                    decoded_results.extend(decoded)
                
                detections.append({
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'yolo_confidence': conf,
                    'decoded_count': len(decoded_results),
                    'decoded_data': decoded_results
                })
        
        total_time = (time.time() - start_time) * 1000
        
        # 显示结果
        print(f"  🎯 YOLO检测: {len(detections)} 个区域 ({yolo_time:.1f}ms)")
        print(f"  ⏱️ 总耗时: {total_time:.1f}ms")
        
        success_count = 0
        for i, det in enumerate(detections):
            if det['decoded_count'] > 0:
                success_count += 1
                print(f"  ✅ 区域{i+1}: 解码成功 {det['decoded_count']} 个")
                for decoded in det['decoded_data']:
                    print(f"    {decoded['decoder']} | {decoded['type']} | {decoded['data']}")
            else:
                print(f"  ❌ 区域{i+1}: 解码失败")
        
        return {
            'image': image_path,
            'detections': detections,
            'yolo_time_ms': yolo_time,
            'total_time_ms': total_time,
            'successful_decodes': success_count
        }
    
    def run_tests(self):
        """运行所有测试"""
        if not self.test_images:
            print("❌ 没有找到测试图像")
            return
        
        results = []
        for image_path in self.test_images:
            result = self.test_one_image(image_path)
            results.append(result)
        
        # 汇总结果
        total_detections = sum(len(r.get('detections', [])) for r in results)
        total_decodes = sum(r.get('successful_decodes', 0) for r in results)
        total_time = sum(r.get('total_time_ms', 0) for r in results)
        
        print(f"\n{'='*50}")
        print(f"📊 测试汇总")
        print(f"测试图像: {len(results)} 张")
        print(f"YOLO检测: {total_detections} 个区域")
        print(f"成功解码: {total_decodes} 个")
        print(f"解码成功率: {total_decodes/total_detections:.1%}" if total_detections > 0 else "N/A")
        print(f"平均耗时: {total_time/len(results):.1f}ms/图")
        print(f"{'='*50}")
        
        # 保存结果
        output_file = f'simple_decode_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump({
                'summary': {
                    'images': len(results),
                    'detections': total_detections,
                    'decodes': total_decodes,
                    'success_rate': total_decodes/total_detections if total_detections > 0 else 0
                },
                'results': results
            }, f, indent=2)
        
        print(f"💾 结果保存到: {output_file}")

def main():
    """主函数"""
    model_path = 'barcode_training/barcode_detector_4060ti/weights/best.pt'
    
    if not os.path.exists(model_path):
        print(f"❌ 模型不存在: {model_path}")
        return
    
    tester = SimpleYoloDecodeTester(model_path)
    tester.run_tests()

if __name__ == "__main__":
    main()