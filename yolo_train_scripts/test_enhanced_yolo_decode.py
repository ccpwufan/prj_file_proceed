#!/usr/bin/env python
"""
增强版YOLO + 条码解码测试脚本
包含更好的图像预处理和解码策略
"""
import os
import cv2
import json
import time
import numpy as np
from datetime import datetime
from pathlib import Path

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("❌ ultralytics 未安装 - 安装命令: pip install ultralytics")
    YOLO_AVAILABLE = False

# Check for available barcode decoders
PYZBAR_AVAILABLE = False
PYZXING_AVAILABLE = False

try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    PYZBAR_AVAILABLE = True
    print("✅ pyzbar 可用")
except ImportError:
    print("⚠️ pyzbar 不可用 - 安装命令: pip install pyzbar")
    print("   Windows可能需要额外安装: https://github.com/mhammond/pywin32/releases")

try:
    from pyzxing import BarCodeReader
    PYZXING_AVAILABLE = True
    print("✅ pyzxing 可用")
except ImportError:
    print("⚠️ pyzxing 不可用 - 安装命令: pip install pyzxing")
    print("   需要Java环境支持")

class EnhancedBarcodeDecoder:
    """增强的条码解码器，包含多种预处理策略"""
    
    def __init__(self):
        self.decoders = []
        if PYZBAR_AVAILABLE:
            self.decoders.append('pyzbar')
        if PYZXING_AVAILABLE:
            self.decoders.append('pyzxing')
    
    def enhance_image(self, image):
        """增强图像质量以提高解码成功率"""
        enhanced_images = []
        
        # 1. 原始图像
        enhanced_images.append(('original', image))
        
        # 2. 灰度转换 + 对比度增强
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # CLAHE对比度增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        enhanced_images.append(('clahe', enhanced))
        
        # 3. 自适应阈值处理
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        enhanced_images.append(('adaptive', adaptive))
        
        # 4. 降噪 + 锐化
        denoised = cv2.fastNlMeansDenoising(gray)
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        enhanced_images.append(('sharpened', sharpened))
        
        # 5. 膨胀 + 腐蚀（去除噪点）
        kernel = np.ones((2,2), np.uint8)
        processed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        enhanced_images.append(('morphology', processed))
        
        # 6. 调整尺寸放大
        height, width = gray.shape
        if max(height, width) < 400:  # 如果图像太小，放大它
            scale = 400 / max(height, width)
            enlarged = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            enhanced_images.append(('enlarged', enlarged))
        
        return enhanced_images
    
    def decode_with_pyzbar(self, image, enhanced_name='original'):
        """使用pyzbar解码，支持多种条码类型"""
        try:
            # 尝试所有条码类型
            barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.CODE128, ZBarSymbol.QRCODE, 
                                                   ZBarSymbol.EAN13, ZBarSymbol.EAN8,
                                                   ZBarSymbol.UPCA, ZBarSymbol.UPCE,
                                                   ZBarSymbol.CODE39, ZBarSymbol.CODE93,
                                                   ZBarSymbol.DATABAR, ZBarSymbol.DATAMATRIX])
            
            results = []
            for barcode in barcodes:
                data = barcode.data.decode('utf-8').strip()
                if data:  # 只返回非空数据
                    results.append({
                        'decoder': 'pyzbar',
                        'type': barcode.type,
                        'data': data,
                        'quality': barcode.quality if hasattr(barcode, 'quality') else 'unknown',
                        'enhanced': enhanced_name
                    })
            return results
        except Exception as e:
            return []
    
    def decode_with_pyzxing(self, image, enhanced_name='original'):
        """使用pyzxing解码"""
        try:
            reader = BarCodeReader()
            results = reader.decode(image)
            
            decoded_results = []
            for result in results:
                if result.parsed and result.parsed.strip():
                    decoded_results.append({
                        'decoder': 'pyzxing',
                        'type': result.format,
                        'data': result.parsed.strip(),
                        'enhanced': enhanced_name
                    })
            return decoded_results
        except Exception as e:
            return []
    
    def decode_barcode_region(self, image):
        """使用多种增强策略解码条码区域"""
        all_results = []
        
        # 获取增强版本的图像
        enhanced_images = self.enhance_image(image)
        
        # 对每个增强图像尝试解码
        for enhanced_name, enhanced_image in enhanced_images:
            for decoder in self.decoders:
                if decoder == 'pyzbar':
                    results = self.decode_with_pyzbar(enhanced_image, enhanced_name)
                elif decoder == 'pyzxing':
                    results = self.decode_with_pyzxing(enhanced_image, enhanced_name)
                
                all_results.extend(results)
        
        # 去重并选择最佳结果
        return self.deduplicate_results(all_results)
    
    def deduplicate_results(self, results):
        """去重并选择最佳解码结果"""
        if not results:
            return []
        
        # 按数据内容分组
        data_groups = {}
        for result in results:
            data = result['data']
            if data not in data_groups:
                data_groups[data] = []
            data_groups[data].append(result)
        
        # 为每个数据选择最佳结果
        best_results = []
        for data, group in data_groups.items():
            # 优先选择原始图像的结果，其次选择增强图像
            original_result = next((r for r in group if r['enhanced'] == 'original'), None)
            if original_result:
                best_results.append(original_result)
            else:
                # 选择第一个结果
                best_results.append(group[0])
        
        return best_results

class EnhancedYoloBarcodeTester:
    """增强版YOLO条码检测和解码测试器"""
    
    def __init__(self, model_path='barcode_training/barcode_detector_4060ti/weights/best.pt', 
                 test_dir='media/detection_frames', max_tests=5):
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics 未安装")
            
        self.model = YOLO(model_path)
        self.test_dir = Path(test_dir)
        self.max_tests = max_tests
        self.decoder = EnhancedBarcodeDecoder()
        
        # 查找测试图像
        self.test_images = []
        potential_dirs = [
            'barcode_dataset/images/val',
            'barcode_dataset/images/test', 
            'media/detection_frames',
            'barcode_dataset/images/train'
        ]
        
        for dir_path in potential_dirs:
            path = Path(dir_path)
            if path.exists():
                jpg_files = list(path.glob('*.jpg'))
                self.test_images.extend(jpg_files)
        
        # 限制测试数量
        if len(self.test_images) > self.max_tests:
            self.test_images = self.test_images[:self.max_tests]
        
        print(f"\n=== 增强版YOLO + 条码解码测试器 ===")
        print(f"📂 工作目录: {Path.cwd()}")
        print(f"🎯 模型路径: {model_path}")
        print(f"🖼️ 测试图像: {len(self.test_images)} 张")
        print(f"🔧 可用解码器: {self.decoder.decoders}")
        print(f"🚀 增强策略: CLAHE对比度、自适应阈值、降噪锐化、形态学处理\n")
    
    def test_single_image(self, image_path):
        """测试单张图像，使用增强解码"""
        print(f"📷 测试图像: {image_path.name}")
        
        # 读取图像
        image = cv2.imread(str(image_path))
        if image is None:
            return {'error': f'Cannot load image: {image_path}'}
        
        # YOLO检测
        start_time = time.time()
        yolo_results = self.model(image)
        yolo_time = (time.time() - start_time) * 1000
        
        detections = []
        successful_decodes = 0
        total_decode_time = 0
        
        # 处理检测结果
        if yolo_results[0].boxes is not None:
            print(f"  🎯 YOLO检测: {len(yolo_results[0].boxes)} 个区域 ({yolo_time:.1f}ms)")
            
            for i, box in enumerate(yolo_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                # 提取条码区域（扩大边界框以确保完整）
                margin = 10
                x1, y1 = max(0, int(x1-margin)), max(0, int(y1-margin))
                x2, y2 = min(image.shape[1], int(x2+margin)), min(image.shape[0], int(y2+margin))
                
                barcode_region = image[y1:y2, x1:x2]
                
                # 增强解码
                decode_start = time.time()
                decoded_results = self.decoder.decode_barcode_region(barcode_region)
                decode_time = (time.time() - decode_start) * 1000
                total_decode_time += decode_time
                
                detection_info = {
                    'detection_id': i+1,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'decoded_results': decoded_results,
                    'decode_time_ms': decode_time
                }
                
                if decoded_results:
                    successful_decodes += 1
                    print(f"    ✅ 区域{i+1} [{class_name}]:")
                    for result in decoded_results:
                        print(f"      {result['decoder']} ({result['enhanced']}) | {result['type']} | {result['data']}")
                else:
                    print(f"    ❌ 区域{i+1} [{class_name}]: 所有增强策略解码失败")
                
                detections.append(detection_info)
        else:
            print(f"  🎯 YOLO检测: 0 个区域 ({yolo_time:.1f}ms)")
        
        # 对比测试：全图解码
        full_decode_start = time.time()
        full_image_results = self.decoder.decode_barcode_region(image)
        full_decode_time = (time.time() - full_decode_start) * 1000
        
        if full_image_results:
            pyzbar_count = sum(1 for r in full_image_results if r['decoder'] == 'pyzbar')
            pyzxing_count = sum(1 for r in full_image_results if r['decoder'] == 'pyzxing')
            print(f"  🔍 全图解码: pyzbar={pyzbar_count}, pyzxing={pyzxing_count}")
        
        total_time = yolo_time + total_decode_time
        
        return {
            'image_path': str(image_path),
            'yolo_inference_time_ms': yolo_time,
            'total_decode_time_ms': total_decode_time,
            'total_time_ms': total_time,
            'detections': detections,
            'detection_count': len(detections),
            'successful_decodes': successful_decodes,
            'full_image_decode_results': full_image_results,
            'full_image_decode_time_ms': full_decode_time
        }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("🚀 开始增强版YOLO + 条码解码测试")
        print("="*60 + "\n")
        
        start_time = time.time()
        all_results = []
        
        for i, image_path in enumerate(self.test_images):
            print(f"--- 测试进度: {i+1}/{len(self.test_images)} ---\n")
            result = self.test_single_image(image_path)
            if 'error' not in result:
                all_results.append(result)
                print(f"  📊 结果: 检测{result['detection_count']}个, 解码成功{result['successful_decodes']}个")
            print()
        
        total_test_time = time.time() - start_time
        
        # 统计结果
        total_detections = sum(r['detection_count'] for r in all_results)
        total_decodes = sum(r['successful_decodes'] for r in all_results)
        avg_yolo_time = np.mean([r['yolo_inference_time_ms'] for r in all_results]) if all_results else 0
        avg_decode_time = np.mean([r['total_decode_time_ms'] for r in all_results]) if all_results else 0
        avg_total_time = np.mean([r['total_time_ms'] for r in all_results]) if all_results else 0
        success_rate = (total_decodes / total_detections * 100) if total_detections > 0 else 0
        
        # 保存结果
        output_file = f'enhanced_yolo_decode_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_summary': {
                    'total_images_tested': len(all_results),
                    'total_yolo_detections': total_detections,
                    'total_successful_decodes': total_decodes,
                    'decode_success_rate_percent': success_rate,
                    'avg_yolo_inference_time_ms': avg_yolo_time,
                    'avg_decode_time_ms': avg_decode_time,
                    'avg_total_time_ms': avg_total_time,
                    'total_test_time_seconds': total_test_time,
                    'estimated_fps': 1000 / avg_total_time if avg_total_time > 0 else 0
                },
                'detailed_results': all_results
            }, f, indent=2, ensure_ascii=False)
        
        print("="*60)
        print("📊 增强版测试结果汇总")
        print("="*60)
        print(f"✅ 成功测试: {len(all_results)}/{len(self.test_images)} 张图像")
        print(f"🎯 YOLO检测总数: {total_detections} 个区域")
        print(f"🔓 成功解码总数: {total_decodes} 个条码")
        print(f"📈 解码成功率: {success_rate:.1f}%")
        print(f"⚡ 平均性能:")
        print(f"  - YOLO推理: {avg_yolo_time:.1f}ms")
        print(f"  - 条码解码: {avg_decode_time:.1f}ms")
        print(f"  - 总耗时: {avg_total_time:.1f}ms")
        print(f"  - FPS: {1000/avg_total_time:.1f}")
        print(f"\n💾 详细结果已保存到: {output_file}")
        
        if success_rate > 50:
            print(f"\n🎉 测试效果优秀！")
        elif success_rate > 30:
            print(f"\n👍 测试效果良好，有改进空间")
        else:
            print(f"\n⚠️ 解码效果仍需优化")
        
        return all_results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版YOLO + 条码解码测试')
    parser.add_argument('--model', type=str, 
                       default='barcode_training/barcode_detector_4060ti/weights/best.pt',
                       help='YOLO模型路径')
    parser.add_argument('--test-dir', type=str, 
                       default='media/detection_frames',
                       help='测试图像目录')
    parser.add_argument('--max-tests', type=int, default=5,
                       help='最大测试图像数量')
    
    args = parser.parse_args()
    
    try:
        tester = EnhancedYoloBarcodeTester(
            model_path=args.model,
            test_dir=args.test_dir,
            max_tests=args.max_tests
        )
        tester.run_all_tests()
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())