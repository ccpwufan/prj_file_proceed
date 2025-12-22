#!/usr/bin/env python
"""
YOLO + QReader 条码解码测试脚本
测试使用QReader解码YOLO检测到的条码区域
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob

def test_qreader_availability():
    """测试QReader是否可用"""
    try:
        from qreader import QReader
        qreader = QReader()
        print("✅ QReader 可用")
        return True, qreader
    except ImportError as e:
        print(f"❌ QReader 不可用: {e}")
        print("请安装: pip install qreader")
        return False, None

class QReaderYoloTester:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.qreader_available, self.qreader = test_qreader_availability()
        self.test_images = self.find_test_images()
        
        print(f"\n=== YOLO + QReader 条码解码测试 ===")
        print(f"模型: {model_path}")
        print(f"图像: {len(self.test_images)} 张")
        print(f"QReader状态: {'✅ 可用' if self.qreader_available else '❌ 不可用'}")
    
    def find_test_images(self):
        """查找测试图像"""
        images = []
        # 查找不同路径下的测试图像
        patterns = [
            'barcode_dataset/images/val/*.jpg',
            'media/detection_frames/*.jpg',
            '*.jpg'
        ]
        
        for pattern in patterns:
            if glob.glob(pattern):
                images.extend(glob.glob(pattern))
                break
        
        # 如果还是没有图像，尝试一些常见的测试图像
        if not images:
            common_images = [
                'complex_test_barcode.jpg',
                'barcode_dataset/images/val/snapshot_71_1765980946.jpg'
            ]
            for img in common_images:
                if os.path.exists(img):
                    images.append(img)
        
        return images[:5]  # 最多测试5张
    
    def decode_with_qreader(self, image):
        """使用QReader解码图像"""
        if not self.qreader_available:
            return []
        
        try:
            # QReader可以直接处理numpy数组
            decoded_text = self.qreader.detect_and_decode(image=image)
            
            results = []
            for i, text in enumerate(decoded_text):
                if text:  # 只添加成功解码的结果
                    results.append({
                        'data': text,
                        'decoder': 'QReader',
                        'index': i
                    })
            
            return results
            
        except Exception as e:
            print(f"    ❌ QReader解码错误: {e}")
            return []
    
    def test_one_image(self, image_path):
        """测试单张图像"""
        print(f"\n📷 测试图像: {os.path.basename(image_path)}")
        print("-" * 60)
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 无法加载图像: {image_path}")
            return {'error': f'Cannot load {image_path}'}
        
        # YOLO检测
        start_time = time.time()
        results = self.model(image, conf=0.3)
        yolo_time = (time.time() - start_time) * 1000
        
        detections = []
        if results[0].boxes is not None:
            print(f"🎯 YOLO检测到 {len(results[0].boxes)} 个条码区域 ({yolo_time:.1f}ms)")
            
            for i, box in enumerate(results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                print(f"\n  区域 {i+1}:")
                print(f"    类别: {class_name}")
                print(f"    置信度: {conf:.3f}")
                print(f"    位置: [{int(x1)}, {int(y1)}, {int(x2)}, {int(y2)}]")
                
                # 提取条码区域
                roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # 使用QReader解码
                decode_start = time.time()
                decoded_results = self.decode_with_qreader(roi)
                decode_time = (time.time() - decode_start) * 1000
                
                print(f"    🔍 QReader解码 ({decode_time:.1f}ms):")
                
                if decoded_results:
                    for decoded in decoded_results:
                        print(f"      ✅ 解码成功:")
                        print(f"        📦 解码器: {decoded['decoder']}")
                        print(f"        📄 内容: {decoded['data']}")
                else:
                    print(f"      ❌ 未能解码该区域")
                
                detections.append({
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'class': class_name,
                    'yolo_confidence': conf,
                    'decoded_count': len(decoded_results),
                    'decoded_data': decoded_results,
                    'decode_time_ms': decode_time
                })
        else:
            print("❌ YOLO未检测到任何条码区域")
        
        # 对比测试：直接用QReader解码全图
        print(f"\n🔍 对比测试: 全图直接QReader解码")
        print("-" * 40)
        full_decode_start = time.time()
        full_decoded = self.decode_with_qreader(image)
        full_decode_time = (time.time() - full_decode_start) * 1000
        
        if full_decoded:
            print(f"  ✅ 全图直接解码成功 ({full_decode_time:.1f}ms):")
            for decoded in full_decoded:
                print(f"    📄 内容: {decoded['data']}")
        else:
            print(f"  ❌ 全图直接解码失败")
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            'image_path': image_path,
            'detections': detections,
            'yolo_time_ms': yolo_time,
            'total_time_ms': total_time,
            'full_direct_decode': {
                'results': full_decoded,
                'time_ms': full_decode_time
            },
            'successful_regions': sum(1 for d in detections if d['decoded_count'] > 0)
        }
    
    def run_tests(self):
        """运行所有测试"""
        if not self.qreader_available:
            print("❌ QReader不可用，无法进行测试")
            return
        
        if not self.test_images:
            print("❌ 没有找到测试图像")
            return
        
        print(f"\n🚀 开始测试...")
        results = []
        
        for image_path in self.test_images:
            result = self.test_one_image(image_path)
            results.append(result)
        
        # 统计汇总
        total_detections = sum(len(r.get('detections', [])) for r in results)
        successful_regions = sum(r.get('successful_regions', 0) for r in results)
        successful_full_decode = sum(1 for r in results if r.get('full_direct_decode', {}).get('results'))
        total_time = sum(r.get('total_time_ms', 0) for r in results)
        
        print(f"\n{'='*60}")
        print(f"📊 测试结果汇总")
        print(f"{'='*60}")
        print(f"📷 测试图像: {len(results)} 张")
        print(f"🎯 YOLO检测: {total_detections} 个条码区域")
        print(f"✅ 区域解码成功: {successful_regions} 个")
        print(f"🔍 全图直接解码成功: {successful_full_decode} 张")
        
        if total_detections > 0:
            print(f"📈 区域解码成功率: {successful_regions/total_detections:.1%}")
        
        if len(results) > 0:
            print(f"📈 全图解码成功率: {successful_full_decode/len(results):.1%}")
            print(f"⏱️ 平均处理时间: {total_time/len(results):.1f}ms/图")
        
        print(f"{'='*60}")
        
        # 保存详细结果
        output_file = f'qreader_yolo_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        report_data = {
            'test_info': {
                'model': 'YOLO + QReader',
                'timestamp': datetime.now().isoformat(),
                'images_tested': len(results),
                'qreader_available': self.qreader_available
            },
            'summary': {
                'total_detections': total_detections,
                'successful_region_decodes': successful_regions,
                'successful_full_decodes': successful_full_decode,
                'region_decode_success_rate': successful_regions/total_detections if total_detections > 0 else 0,
                'full_decode_success_rate': successful_full_decode/len(results) if results else 0,
                'avg_processing_time_ms': total_time/len(results) if results else 0
            },
            'detailed_results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 详细结果保存到: {output_file}")
        
        return report_data

def main():
    """主函数"""
    # 尝试不同的模型路径
    model_paths = [
        'barcode_training/barcode_detector_4060ti/weights/best.pt',
        'barcode_training/barcode_detector_v2/weights/best.pt',
        'yolov8n.pt'  # 最后使用通用模型
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        print("❌ 没有找到可用的YOLO模型")
        print("尝试的路径:")
        for path in model_paths:
            print(f"  - {path}")
        return
    
    print(f"🔄 使用模型: {model_path}")
    
    # 创建测试器并运行测试
    tester = QReaderYoloTester(model_path)
    tester.run_tests()

if __name__ == "__main__":
    main()