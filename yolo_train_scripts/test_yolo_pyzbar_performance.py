#!/usr/bin/env python
"""
YOLO + pyzbar 性能测试脚本
专注于测试当前环境下pyzbar与YOLO的组合效果
为将来QReader测试提供基准
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob

class YoloPyzbarTester:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.pyzbar_available = self.test_pyzbar()
        self.test_images = self.find_test_images()
        
        print(f"\n=== YOLO + pyzbar 性能测试 ===")
        print(f"YOLO模型: {model_path}")
        print(f"pyzbar状态: {'✅ 可用' if self.pyzbar_available else '❌ 不可用'}")
        print(f"测试图像: {len(self.test_images)} 张")
    
    def test_pyzbar(self):
        """测试pyzbar可用性"""
        try:
            from pyzbar import pyzbar
            self.pyzbar = pyzbar
            print("✅ pyzbar 可用")
            return True
        except ImportError:
            print("❌ pyzbar 不可用")
            self.pyzbar = None
            return False
    
    def find_test_images(self):
        """查找测试图像"""
        images = []
        patterns = [
            'barcode_dataset/images/val/*.jpg',
            'media/detection_frames/*.jpg',
            'visual_test_output/*.jpg',
            '*.jpg'
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            if found:
                images.extend(found[:3])  # 每个路径最多3张
                if len(images) >= 5:
                    break
        
        return images[:5]  # 最多5张图像
    
    def decode_with_pyzbar(self, image):
        """使用pyzbar解码图像"""
        if not self.pyzbar_available:
            return []
        
        try:
            decoded = self.pyzbar.decode(image)
            results = []
            for obj in decoded:
                results.append({
                    'type': obj.type,
                    'data': obj.data.decode('utf-8'),
                    'quality': getattr(obj, 'quality', None),
                    'confidence': getattr(obj, 'confidence', None),
                    'rect': {
                        'left': obj.rect.left,
                        'top': obj.rect.top,
                        'width': obj.rect.width,
                        'height': obj.rect.height
                    }
                })
            return results
        except Exception as e:
            print(f"      ❌ pyzbar解码错误: {e}")
            return []
    
    def test_one_image(self, image_path):
        """测试单张图像"""
        print(f"\n📷 测试: {os.path.basename(image_path)}")
        print("-" * 50)
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            return {'error': f'Cannot load {image_path}'}
        
        image_size = image.shape[:2]
        print(f"🖼️ 图像尺寸: {image_size[1]}x{image_size[0]}")
        
        # YOLO检测
        start_time = time.time()
        results = self.model(image, conf=0.3)
        yolo_time = (time.time() - start_time) * 1000
        
        detections = []
        if results[0].boxes is not None:
            print(f"🎯 YOLO检测: {len(results[0].boxes)} 个区域 ({yolo_time:.1f}ms)")
            
            for i, box in enumerate(results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                print(f"\n  区域 {i+1}:")
                print(f"    类别: {class_name}")
                print(f"    置信度: {conf:.3f}")
                print(f"    位置: [{int(x1)}, {int(y1)}, {int(x2)}, {int(y2)}]")
                print(f"    尺寸: {int(x2-x1)}x{int(y2-y1)}")
                
                # 提取ROI
                roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # pyzbar解码
                decode_start = time.time()
                decoded_results = self.decode_with_pyzbar(roi)
                decode_time = (time.time() - decode_start) * 1000
                
                print(f"    🔍 pyzbar解码 ({decode_time:.1f}ms):")
                
                if decoded_results:
                    for j, result in enumerate(decoded_results):
                        print(f"      ✅ 解码 {j+1}:")
                        print(f"        类型: {result['type']}")
                        print(f"        内容: {result['data']}")
                        if result['quality']:
                            print(f"        质量: {result['quality']}")
                else:
                    print(f"      ❌ 未能解码")
                
                detections.append({
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'class': class_name,
                    'confidence': conf,
                    'roi_size': [int(x2-x1), int(y2-y1)],
                    'decoded_count': len(decoded_results),
                    'decoded_data': decoded_results,
                    'decode_time_ms': decode_time
                })
        else:
            print("❌ YOLO未检测到条码区域")
        
        # 对比：直接解码全图
        print(f"\n🔍 对比: 全图直接pyzbar解码")
        print("-" * 40)
        full_decode_start = time.time()
        full_decoded = self.decode_with_pyzbar(image)
        full_decode_time = (time.time() - full_decode_start) * 1000
        
        if full_decoded:
            print(f"  ✅ 全图解码成功 ({full_decode_time:.1f}ms):")
            for j, result in enumerate(full_decoded):
                print(f"    {j+1}. {result['type']}: {result['data']}")
        else:
            print(f"  ❌ 全图解码失败")
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            'image_path': image_path,
            'image_size': list(image_size),
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
        if not self.pyzbar_available:
            print("❌ pyzbar不可用，无法进行测试")
            return
        
        if not self.test_images:
            print("❌ 没有找到测试图像")
            return
        
        print(f"\n🚀 开始性能测试...")
        results = []
        
        for image_path in self.test_images:
            result = self.test_one_image(image_path)
            results.append(result)
        
        # 性能统计
        total_detections = sum(len(r.get('detections', [])) for r in results)
        successful_regions = sum(r.get('successful_regions', 0) for r in results)
        successful_full_decode = sum(1 for r in results if r.get('full_direct_decode', {}).get('results'))
        
        # 时间统计
        yolo_times = [r.get('yolo_time_ms', 0) for r in results]
        decode_times = [d.get('decode_time_ms', 0) for r in results for d in r.get('detections', [])]
        total_times = [r.get('total_time_ms', 0) for r in results]
        
        print(f"\n{'='*60}")
        print(f"📊 性能测试结果")
        print(f"{'='*60}")
        print(f"📷 测试图像: {len(results)} 张")
        print(f"🎯 YOLO检测: {total_detections} 个条码区域")
        print(f"✅ 区域解码成功: {successful_regions} 个")
        print(f"🔍 全图直接解码成功: {successful_full_decode} 张")
        
        if total_detections > 0:
            print(f"📈 区域解码成功率: {successful_regions/total_detections:.1%}")
        
        if len(results) > 0:
            print(f"📈 全图解码成功率: {successful_full_decode/len(results):.1%}")
        
        # 时间性能
        if yolo_times:
            print(f"\n⏱️ 时间性能分析:")
            print(f"   YOLO检测 - 平均: {sum(yolo_times)/len(yolo_times):.1f}ms, 最大: {max(yolo_times):.1f}ms")
        if decode_times:
            print(f"   pyzbar解码 - 平均: {sum(decode_times)/len(decode_times):.1f}ms, 最大: {max(decode_times):.1f}ms")
        if total_times:
            print(f"   总处理时间 - 平均: {sum(total_times)/len(total_times):.1f}ms/图")
        
        print(f"{'='*60}")
        
        # 保存性能报告
        performance_report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'model': 'YOLO + pyzbar',
                'images_tested': len(results),
                'pyzbar_available': self.pyzbar_available
            },
            'performance_summary': {
                'total_detections': total_detections,
                'successful_region_decodes': successful_regions,
                'successful_full_decodes': successful_full_decode,
                'region_decode_success_rate': successful_regions/total_detections if total_detections > 0 else 0,
                'full_decode_success_rate': successful_full_decode/len(results) if results else 0,
                'timing': {
                    'avg_yolo_time_ms': sum(yolo_times)/len(yolo_times) if yolo_times else 0,
                    'avg_decode_time_ms': sum(decode_times)/len(decode_times) if decode_times else 0,
                    'avg_total_time_ms': sum(total_times)/len(total_times) if total_times else 0
                }
            },
            'detailed_results': results
        }
        
        output_file = f'yolo_pyzbar_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(performance_report, f, indent=2, ensure_ascii=False)
        
        print(f"💾 性能报告保存到: {output_file}")
        
        # QReader测试建议
        print(f"\n💡 QReader测试建议:")
        print(f"   - 当前pyzbar区域解码成功率: {successful_regions/total_detections:.1%}" if total_detections > 0 else "   - 当前pyzbar区域解码成功率: N/A")
        print(f"   - 当网络条件良好时，可测试QReader是否能提升解码率")
        print(f"   - QReader特别针对QR码优化，可能在QR码场景表现更好")
        
        return performance_report

def main():
    """主函数"""
    # 查找YOLO模型
    model_paths = [
        'barcode_training/barcode_detector_4060ti/weights/best.pt',
        'barcode_training/barcode_detector_v2/weights/best.pt',
        'yolov8n.pt'
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        print("❌ 没有找到可用的YOLO模型")
        return
    
    tester = YoloPyzbarTester(model_path)
    tester.run_tests()

if __name__ == "__main__":
    main()