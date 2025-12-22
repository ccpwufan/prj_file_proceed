#!/usr/bin/env python
"""
4060ti训练后的YOLO模型 + 条码解码测试脚本
结合YOLO定位和pyzbar/pyzxing解码，实现完整的条码识别流程
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob

# Import barcode decoding libraries
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
    print("✅ pyzbar available")
except ImportError:
    PYZBAR_AVAILABLE = False
    print("⚠️ pyzbar not available")

try:
    from pyzxing import BarCodeReader
    PYZXING_AVAILABLE = True
    print("✅ pyzxing available")
except ImportError:
    PYZXING_AVAILABLE = False
    print("⚠️ pyzxing not available")

class YOLOBarcodeDecoder:
    def __init__(self, model_path):
        """加载训练好的4060ti模型和初始化解码器"""
        self.model = YOLO(model_path)
        self.model_path = model_path
        
        # Initialize decoders
        self.pyzbar_available = PYZBAR_AVAILABLE
        self.pyzxing_available = PYZXING_AVAILABLE
        
        if self.pyzxing_available:
            self.zxing_reader = BarCodeReader()
        
        # Find test images
        self.test_images = self.find_test_images()
        
        print(f"=== YOLO + 条码解码测试器 ===")
        print(f"模型路径: {model_path}")
        print(f"找到测试图像: {len(self.test_images)} 张")
        print(f"可用解码器: pyzbar={self.pyzbar_available}, pyzxing={self.pyzxing_available}")
        
    def find_test_images(self):
        """自动查找测试图像"""
        test_images = []
        
        # Search for test images in various directories
        search_paths = [
            'barcode_dataset/images/val/*.jpg',
            'barcode_dataset/images/test/*.jpg', 
            'media/detection_frames/*.jpg',
            '*.jpg'
        ]
        
        for path_pattern in search_paths:
            images = glob.glob(path_pattern)
            if images:
                test_images.extend(images)
                print(f"从 {path_pattern} 找到 {len(images)} 张图像")
                
        # Remove duplicates and limit quantity
        test_images = list(set(test_images))[:10]  # Test maximum 10 images
        
        return test_images
    
    def decode_with_pyzbar(self, image):
        """使用pyzbar解码条码"""
        if not self.pyzbar_available:
            return []
        
        try:
            decoded_objects = pyzbar.decode(image)
            results = []
            
            for obj in decoded_objects:
                rect = obj.rect
                results.append({
                    'decoder': 'pyzbar',
                    'type': obj.type,
                    'data': obj.data.decode('utf-8'),
                    'quality': getattr(obj, 'quality', None),
                    'bbox': [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height],
                    'confidence': 1.0  # pyzbar doesn't provide confidence scores
                })
            
            return results
            
        except Exception as e:
            print(f"  ⚠️ pyzbar解码失败: {e}")
            return []
    
    def decode_with_pyzxing(self, image):
        """使用pyzxing解码条码"""
        if not self.pyzxing_available:
            return []
        
        try:
            # Convert image to format expected by pyzxing
            results = []
            decoded_objects = self.zxing_reader.decode(image)
            
            if decoded_objects:
                for obj in decoded_objects:
                    if obj.parsed:  # Only include successfully decoded barcodes
                        results.append({
                            'decoder': 'pyzxing',
                            'type': obj.format,
                            'data': obj.parsed,
                            'bbox': getattr(obj, 'rect', None),
                            'confidence': getattr(obj, 'confidence', None),
                            'raw': str(obj.raw) if hasattr(obj, 'raw') else None
                        })
            
            return results
            
        except Exception as e:
            print(f"  ⚠️ pyzxing解码失败: {e}")
            return []
    
    def extract_roi_from_bbox(self, image, bbox):
        """根据边界框提取感兴趣区域"""
        x1, y1, x2, y2 = map(int, bbox)
        
        # Ensure coordinates are within image boundaries
        h, w = image.shape[:2]
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))
        
        # Extract region of interest
        if x2 > x1 and y2 > y1:
            roi = image[y1:y2, x1:x2]
            return roi
        else:
            return None
    
    def test_single_image(self, image_path):
        """测试单张图像的完整流程：YOLO检测 + 条码解码"""
        start_time = time.time()
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return {
                'error': f'无法加载图像: {image_path}',
                'image_path': image_path
            }
        
        image_size = [image.shape[1], image.shape[0]]  # [width, height]
        
        # Step 1: YOLO detection
        yolo_start = time.time()
        yolo_results = self.model(image, conf=0.25)
        yolo_time = (time.time() - yolo_start) * 1000
        
        # Parse YOLO detection results
        yolo_detections = []
        for result in yolo_results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    yolo_detections.append({
                        'detection_id': i,
                        'class': class_name,
                        'class_id': class_id,
                        'confidence': confidence,
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'center': [(float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2],
                        'area': float((x2 - x1) * (y2 - y1))
                    })
        
        # Step 2: Decode each detected region
        decode_results = []
        decode_start = time.time()
        
        if yolo_detections:
            for detection in yolo_detections:
                bbox = detection['bbox']
                roi = self.extract_roi_from_bbox(image, bbox)
                
                if roi is not None:
                    # Try pyzbar first (faster and more reliable for common barcodes)
                    pyzbar_results = self.decode_with_pyzbar(roi)
                    
                    # If pyzbar fails or not available, try pyzxing
                    pyzxing_results = self.decode_with_pyzxing(roi) if not pyzbar_results else []
                    
                    # Combine results, preferring pyzbar
                    all_decoded = pyzbar_results if pyzbar_results else pyzxing_results
                    
                    # Adjust bbox coordinates to original image
                    for result in all_decoded:
                        if result['bbox']:
                            local_bbox = result['bbox']
                            result['original_bbox'] = [
                                bbox[0] + local_bbox[0],
                                bbox[1] + local_bbox[1],
                                bbox[0] + local_bbox[2],
                                bbox[1] + local_bbox[3]
                            ]
                    
                    decode_results.append({
                        'detection_id': detection['detection_id'],
                        'yolo_confidence': detection['confidence'],
                        'yolo_class': detection['class'],
                        'roi_bbox': bbox,
                        'decoded_results': all_decoded,
                        'decode_success': len(all_decoded) > 0
                    })
        
        decode_time = (time.time() - decode_start) * 1000
        total_time = (time.time() - start_time) * 1000
        
        # Step 3: Also try full image decoding for comparison
        full_image_decodes = {
            'pyzbar': self.decode_with_pyzbar(image),
            'pyzxing': self.decode_with_pyzxing(image)
        }
        
        return {
            'image_path': image_path,
            'image_size': image_size,
            'yolo_results': {
                'detections': yolo_detections,
                'count': len(yolo_detections),
                'inference_time_ms': yolo_time
            },
            'decode_results': {
                'attempts': decode_results,
                'successful_decodes': len([r for r in decode_results if r['decode_success']]),
                'decode_time_ms': decode_time
            },
            'full_image_decodes': full_image_decodes,
            'performance': {
                'total_time_ms': total_time,
                'yolo_time_ms': yolo_time,
                'decode_time_ms': decode_time,
                'fps': 1000 / total_time if total_time > 0 else 0
            },
            'success': True
        }
    
    def analyze_results(self, results):
        """分析测试结果"""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.get('success', False)]
        
        # YOLO detection statistics
        total_yolo_detections = sum(r['yolo_results']['count'] for r in successful_results)
        total_decode_attempts = len([d for r in successful_results for d in r['decode_results']['attempts']])
        total_successful_decodes = sum(r['decode_results']['successful_decodes'] for r in successful_results)
        
        # Performance statistics
        total_yolo_time = sum(r['yolo_results']['inference_time_ms'] for r in successful_results)
        total_decode_time = sum(r['decode_results']['decode_time_ms'] for r in successful_results)
        total_time = sum(r['performance']['total_time_ms'] for r in successful_results)
        
        # Decoder usage statistics
        decoder_stats = {'pyzbar': 0, 'pyzxing': 0}
        barcode_types = {}
        decoded_data = []
        
        for result in successful_results:
            # YOLO decoder success
            for decode_attempt in result['decode_results']['attempts']:
                if decode_attempt['decode_success']:
                    for decoded in decode_attempt['decoded_results']:
                        decoder = decoded['decoder']
                        decoder_stats[decoder] = decoder_stats.get(decoder, 0) + 1
                        
                        barcode_type = decoded['type']
                        barcode_types[barcode_type] = barcode_types.get(barcode_type, 0) + 1
                        
                        decoded_data.append({
                            'decoder': decoder,
                            'type': barcode_type,
                            'data': decoded['data']
                        })
            
            # Full image decoder success
            for decoder, decodes in result['full_image_decodes'].items():
                if decodes:
                    decoder_stats[decoder] = decoder_stats.get(decoder, 0) + len(decodes)
                    for decoded in decodes:
                        barcode_type = decoded['type']
                        barcode_types[barcode_type] = barcode_types.get(barcode_type, 0) + 1
                        decoded_data.append({
                            'decoder': decoder,
                            'type': barcode_type,
                            'data': decoded['data']
                        })
        
        analysis = {
            'test_summary': {
                'total_images': len(successful_results),
                'images_with_detections': len([r for r in successful_results if r['yolo_results']['count'] > 0]),
                'images_with_decodes': len([r for r in successful_results if r['decode_results']['successful_decodes'] > 0])
            },
            'yolo_performance': {
                'total_detections': total_yolo_detections,
                'avg_detections_per_image': total_yolo_detections / len(successful_results) if successful_results else 0,
                'avg_yolo_time_ms': total_yolo_time / len(successful_results) if successful_results else 0
            },
            'decode_performance': {
                'total_decode_attempts': total_decode_attempts,
                'successful_decodes': total_successful_decodes,
                'decode_success_rate': total_successful_decodes / total_decode_attempts if total_decode_attempts > 0 else 0,
                'avg_decode_time_ms': total_decode_time / len(successful_results) if successful_results else 0
            },
            'overall_performance': {
                'total_time_ms': total_time,
                'avg_total_time_ms': total_time / len(successful_results) if successful_results else 0,
                'avg_fps': 1000 / (total_time / len(successful_results)) if successful_results and total_time > 0 else 0
            },
            'decoder_statistics': decoder_stats,
            'barcode_types': barcode_types,
            'decoded_samples': decoded_data[:10]  # Show first 10 decoded samples
        }
        
        return analysis
    
    def run_all_tests(self):
        """运行所有测试图像"""
        print(f"\n=== 开始YOLO + 条码解码测试 ===")
        print(f"测试图像数量: {len(self.test_images)}")
        print("-" * 70)
        
        results = []
        
        for i, image_path in enumerate(self.test_images):
            print(f"测试 {i+1}/{len(self.test_images)}: {os.path.basename(image_path)}")
            
            result = self.test_single_image(image_path)
            results.append(result)
            
            if result.get('success', False):
                yolo_count = result['yolo_results']['count']
                decode_count = result['decode_results']['successful_decodes']
                total_time = result['performance']['total_time_ms']
                fps = result['performance']['fps']
                
                print(f"  🎯 YOLO检测: {yolo_count} 个区域")
                print(f"  🔓 成功解码: {decode_count} 个条码")
                print(f"  ⏱️ 总耗时: {total_time:.1f}ms ({fps:.1f} FPS)")
                
                # Show decoded barcode data
                if decode_count > 0:
                    print(f"  📊 解码详情:")
                    for decode_attempt in result['decode_results']['attempts']:
                        if decode_attempt['decode_success']:
                            for decoded in decode_attempt['decoded_results']:
                                print(f"    {decoded['decoder']} | {decoded['type']} | {decoded['data']}")
                
                # Show full image decodes for comparison
                full_decodes = result['full_image_decodes']
                total_full_decodes = len(full_decodes.get('pyzbar', [])) + len(full_decodes.get('pyzxing', []))
                if total_full_decodes > 0:
                    print(f"  🔍 全图解码: pyzbar={len(full_decodes.get('pyzbar', []))}, pyzxing={len(full_decodes.get('pyzxing', []))}")
            else:
                print(f"  ✗ 测试失败: {result.get('error', '未知错误')}")
            
            print()
        
        # Analyze results
        print("=== 测试结果分析 ===")
        analysis = self.analyze_results(results)
        
        if analysis:
            summary = analysis['test_summary']
            yolo_perf = analysis['yolo_performance']
            decode_perf = analysis['decode_performance']
            overall_perf = analysis['overall_performance']
            
            print(f"📈 测试总结:")
            print(f"  ✅ 成功测试: {summary['total_images']} 张图像")
            print(f"  🎯 有检测: {summary['images_with_detections']} 张")
            print(f"  🔓 有解码: {summary['images_with_decodes']} 张")
            
            print(f"\n🚀 YOLO性能:")
            print(f"  总检测数: {yolo_perf['total_detections']} 个")
            print(f"  平均检测: {yolo_perf['avg_detections_per_image']:.1f} 个/图")
            print(f"  平均推理时间: {yolo_perf['avg_yolo_time_ms']:.1f}ms")
            
            print(f"\n🔓 解码性能:")
            print(f"  解码尝试: {decode_perf['total_decode_attempts']} 次")
            print(f"  成功解码: {decode_perf['successful_decodes']} 次")
            print(f"  解码成功率: {decode_perf['decode_success_rate']:.1%}")
            print(f"  平均解码时间: {decode_perf['avg_decode_time_ms']:.1f}ms")
            
            print(f"\n⚡ 整体性能:")
            print(f"  平均处理时间: {overall_perf['avg_total_time_ms']:.1f}ms")
            print(f"  平均FPS: {overall_perf['avg_fps']:.1f}")
            
            # Decoder usage statistics
            if analysis['decoder_statistics']:
                print(f"\n🔧 解码器使用统计:")
                for decoder, count in analysis['decoder_statistics'].items():
                    print(f"  {decoder}: {count} 次成功解码")
            
            # Barcode types
            if analysis['barcode_types']:
                print(f"\n📋 条码类型统计:")
                for barcode_type, count in analysis['barcode_types'].items():
                    print(f"  {barcode_type}: {count} 个")
            
            # Sample decoded data
            if analysis['decoded_samples']:
                print(f"\n📝 解码数据样本 (前5个):")
                for i, sample in enumerate(analysis['decoded_samples'][:5]):
                    print(f"  {i+1}. {sample['decoder']} | {sample['type']} | {sample['data']}")
        
        # Save detailed results
        output_file = f'yolo_decode_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        full_results = {
            'test_info': {
                'model_path': self.model_path,
                'test_time': datetime.now().isoformat(),
                'total_images': len(self.test_images),
                'available_decoders': {
                    'pyzbar': self.pyzbar_available,
                    'pyzxing': self.pyzxing_available
                }
            },
            'analysis': analysis,
            'detailed_results': results
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 详细结果已保存到: {output_file}")
        except Exception as e:
            print(f"\n⚠️ 保存结果文件失败: {e}")
        
        return results, analysis

def main():
    """主函数"""
    # 4060ti训练模型路径
    model_path = 'barcode_training/barcode_detector_4060ti/weights/best.pt'
    
    # Check if model file exists
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        print("请先运行训练脚本生成模型")
        return
    
    # Check if any decoder is available
    if not PYZBAR_AVAILABLE and not PYZXING_AVAILABLE:
        print("❌ 没有可用的条码解码器")
        print("请安装 pyzbar 或 pyzxing:")
        print("  pip install pyzbar")
        print("  pip install pyzxing")
        return
    
    # Create tester and run tests
    tester = YOLOBarcodeDecoder(model_path)
    results, analysis = tester.run_all_tests()
    
    # Summary
    print(f"\n{'='*70}")
    print(f"🎉 YOLO + 条码解码测试完成!")
    
    if analysis:
        decode_success_rate = analysis['decode_performance']['decode_success_rate']
        avg_fps = analysis['overall_performance']['avg_fps']
        
        print(f"📊 核心指标:")
        print(f"  ✅ 平均FPS: {avg_fps:.1f}")
        print(f"  🔓 解码成功率: {decode_success_rate:.1%}")
        
        if decode_success_rate >= 0.7:
            print(f"  🏆 解码效果优秀!")
        elif decode_success_rate >= 0.5:
            print(f"  👍 解码效果良好")
        else:
            print(f"  ⚠️ 解码效果需要优化")
        
        # Recommendations
        print(f"\n💡 优化建议:")
        if not tester.pyzbar_available:
            print(f"  - 安装 pyzbar 提高解码速度: pip install pyzbar")
        if decode_success_rate < 0.7:
            print(f"  - 调整YOLO置信度阈值")
            print(f"  - 增加图像预处理步骤")
            print(f"  - 尝试不同的解码器组合")
    
    print(f"{'='*70}")

if __name__ == "__main__":
    main()