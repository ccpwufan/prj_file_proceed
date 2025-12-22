#!/usr/bin/env python
"""
解码器对比测试脚本
对比YOLO+pyzbar和QReader的性能（如果QReader可用）
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob

def test_pyzbar_available():
    """测试pyzbar是否可用"""
    try:
        from pyzbar import pyzbar
        print("✅ pyzbar 可用")
        return True, pyzbar
    except ImportError:
        print("❌ pyzbar 不可用 - 安装: pip install pyzbar")
        return False, None

def test_qreader_available():
    """测试QReader是否可用（不下载模型）"""
    try:
        # 尝试导入，但不实例化（避免下载）
        import qreader
        print("✅ QReader 已安装")
        return True, "installed"
    except ImportError:
        print("❌ QReader 未安装 - 安装: pip install qreader")
        return False, None

def decode_with_pyzbar(pyzbar, image):
    """使用pyzbar解码图像"""
    try:
        decoded = pyzbar.decode(image)
        results = []
        for obj in decoded:
            results.append({
                'type': obj.type,
                'data': obj.data.decode('utf-8'),
                'decoder': 'pyzbar',
                'quality': getattr(obj, 'quality', None)
            })
        return results
    except Exception as e:
        print(f"    ❌ pyzbar解码错误: {e}")
        return []

def decode_with_qreader(qreader, image):
    """使用QReader解码图像"""
    try:
        decoded_text = qreader.detect_and_decode(image=image)
        results = []
        for i, text in enumerate(decoded_text):
            if text:
                results.append({
                    'data': text,
                    'decoder': 'QReader',
                    'index': i
                })
        return results
    except Exception as e:
        print(f"    ❌ QReader解码错误: {e}")
        return []

class DecodeComparisonTester:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.pyzbar_available, self.pyzbar = test_pyzbar_available()
        self.qreader_installed, self.qreader_status = test_qreader_available()
        
        # 尝试创建QReader实例（如果网络允许）
        self.qreader_available = False
        self.qreader = None
        if self.qreader_installed:
            try:
                from qreader import QReader
                # 设置较短的超时时间
                self.qreader = QReader()
                self.qreader_available = True
                print("✅ QReader 实例创建成功")
            except Exception as e:
                print(f"⚠️ QReader 实例创建失败: {e}")
                print("   可能是网络问题导致模型下载失败")
        
        self.test_images = self.find_test_images()
        
        print(f"\n=== 解码器对比测试 ===")
        print(f"YOLO模型: {model_path}")
        print(f"测试图像: {len(self.test_images)} 张")
        print(f"pyzbar: {'✅ 可用' if self.pyzbar_available else '❌ 不可用'}")
        print(f"QReader: {'✅ 可用' if self.qreader_available else '⚠️ 已安装但不可用' if self.qreader_installed else '❌ 未安装'}")
    
    def find_test_images(self):
        """查找测试图像"""
        images = []
        patterns = [
            'barcode_dataset/images/val/*.jpg',
            'media/detection_frames/*.jpg',
            'visual_test_output/*.jpg'
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            if found:
                images.extend(found[:3])  # 每个路径最多取3张
                if len(images) >= 5:
                    break
        
        # 如果没有找到图像，尝试特定的测试图像
        if not images:
            specific_images = [
                'complex_test_barcode.jpg',
                'local_annotation/raw_images/complex_test_barcode.jpg'
            ]
            for img in specific_images:
                if os.path.exists(img):
                    images.append(img)
                    break
        
        return images[:5]  # 最多5张
    
    def test_decoders_on_roi(self, roi, decoder_name):
        """测试指定解码器在ROI上的表现"""
        if decoder_name == 'pyzbar' and self.pyzbar_available:
            return decode_with_pyzbar(self.pyzbar, roi)
        elif decoder_name == 'qreader' and self.qreader_available:
            return decode_with_qreader(self.qreader, roi)
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
                
                # 提取ROI
                roi = image[int(y1):int(y2), int(x1):int(x2)]
                
                # 测试各解码器
                decoder_results = {}
                for decoder in ['pyzbar', 'qreader']:
                    if (decoder == 'pyzbar' and self.pyzbar_available) or \
                       (decoder == 'qreader' and self.qreader_available):
                        decode_start = time.time()
                        results_list = self.test_decoders_on_roi(roi, decoder)
                        decode_time = (time.time() - decode_start) * 1000
                        
                        decoder_results[decoder] = {
                            'results': results_list,
                            'time_ms': decode_time,
                            'count': len(results_list)
                        }
                        
                        print(f"    🔍 {decoder.capitalize()} ({decode_time:.1f}ms):")
                        if results_list:
                            for j, result in enumerate(results_list):
                                print(f"      ✅ {result['type'] if 'type' in result else 'CODE'}: {result['data']}")
                        else:
                            print(f"      ❌ 未能解码")
                
                detections.append({
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'class': class_name,
                    'confidence': conf,
                    'decoder_results': decoder_results
                })
        else:
            print("❌ YOLO未检测到条码区域")
        
        # 对比测试：直接解码全图
        print(f"\n🔍 对比测试: 全图直接解码")
        print("-" * 40)
        
        direct_results = {}
        for decoder in ['pyzbar', 'qreader']:
            if (decoder == 'pyzbar' and self.pyzbar_available) or \
               (decoder == 'qreader' and self.qreader_available):
                decode_start = time.time()
                results_list = self.test_decoders_on_roi(image, decoder)
                decode_time = (time.time() - decode_start) * 1000
                
                direct_results[decoder] = {
                    'results': results_list,
                    'time_ms': decode_time,
                    'count': len(results_list)
                }
                
                print(f"  {decoder.capitalize()}: {len(results_list)} 个条码 ({decode_time:.1f}ms)")
                for result in results_list:
                    print(f"    📄 {result['type'] if 'type' in result else 'CODE'}: {result['data']}")
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            'image_path': image_path,
            'detections': detections,
            'yolo_time_ms': yolo_time,
            'total_time_ms': total_time,
            'direct_decode_results': direct_results
        }
    
    def run_tests(self):
        """运行所有测试"""
        if not self.test_images:
            print("❌ 没有找到测试图像")
            return
        
        print(f"\n🚀 开始对比测试...")
        results = []
        
        for image_path in self.test_images:
            result = self.test_one_image(image_path)
            results.append(result)
        
        # 统计汇总
        total_detections = sum(len(r.get('detections', [])) for r in results)
        
        # 计算各解码器的成功率
        decoder_stats = {
            'pyzbar': {'region_success': 0, 'direct_count': 0},
            'qreader': {'region_success': 0, 'direct_count': 0}
        }
        
        for result in results:
            # 统计区域解码成功数
            for detection in result.get('detections', []):
                for decoder, decoder_result in detection.get('decoder_results', {}).items():
                    if decoder_result.get('count', 0) > 0:
                        decoder_stats[decoder]['region_success'] += 1
            
            # 统计直接解码数
            for decoder, direct_result in result.get('direct_decode_results', {}).items():
                decoder_stats[decoder]['direct_count'] += direct_result.get('count', 0)
        
        print(f"\n{'='*60}")
        print(f"📊 对比测试结果汇总")
        print(f"{'='*60}")
        print(f"📷 测试图像: {len(results)} 张")
        print(f"🎯 YOLO检测区域: {total_detections} 个")
        
        for decoder in ['pyzbar', 'qreader']:
            available = (decoder == 'pyzbar' and self.pyzbar_available) or \
                       (decoder == 'qreader' and self.qreader_available)
            
            if available:
                region_success = decoder_stats[decoder]['region_success']
                direct_count = decoder_stats[decoder]['direct_count']
                
                print(f"\n🔍 {decoder.capitalize()}:")
                print(f"  区域解码成功: {region_success}/{total_detections} ({region_success/total_detections:.1%})" if total_detections > 0 else "  区域解码成功: N/A")
                print(f"  全图解码总数: {direct_count} 个")
            else:
                print(f"\n❌ {decoder.capitalize()}: 不可用")
        
        print(f"{'='*60}")
        
        # 保存详细报告
        report = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'model': 'YOLO + 解码器对比',
                'images_tested': len(results),
                'decoders': {
                    'pyzbar': self.pyzbar_available,
                    'qreader': self.qreader_available
                }
            },
            'summary': {
                'total_detections': total_detections,
                'decoder_stats': decoder_stats
            },
            'detailed_results': results
        }
        
        output_file = f'decode_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"💾 详细报告保存到: {output_file}")
        
        return report

def main():
    """主函数"""
    print("🔄 查找YOLO模型...")
    
    # 查找可用的YOLO模型
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
    
    print(f"✅ 使用模型: {model_path}")
    
    # 创建测试器并运行
    tester = DecodeComparisonTester(model_path)
    tester.run_tests()

if __name__ == "__main__":
    main()