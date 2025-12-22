#!/usr/bin/env python
"""
最终YOLO + 双解码器测试脚本
全面测试YOLO定位 + pyzbar + pyzxing的解码效果
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
    print("❌ ultralytics 未安装")
    YOLO_AVAILABLE = False

try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    PYZBAR_AVAILABLE = True
except ImportError:
    print("❌ pyzbar 未安装")
    PYZBAR_AVAILABLE = False

try:
    from pyzxing import BarCodeReader
    PYZXING_AVAILABLE = True
except ImportError:
    print("❌ pyzxing 未安装")
    PYZXING_AVAILABLE = False

class FinalBarcodeDecoder:
    """最终条码解码器，使用所有可用的解码器"""
    
    def __init__(self):
        self.pyzxing_reader = BarCodeReader() if PYZXING_AVAILABLE else None
        print(f"✅ 解码器状态: pyzbar={PYZBAR_AVAILABLE}, pyzxing={PYZXING_AVAILABLE}")
    
    def decode_with_all_methods(self, image, region_name="unknown"):
        """使用所有可用方法解码图像"""
        results = []
        
        # 方法1: pyzbar解码
        if PYZBAR_AVAILABLE:
            try:
                barcodes = pyzbar.decode(image, symbols=[
                    ZBarSymbol.CODE128, ZBarSymbol.QRCODE, 
                    ZBarSymbol.EAN13, ZBarSymbol.EAN8,
                    ZBarSymbol.UPCA, ZBarSymbol.UPCE,
                    ZBarSymbol.CODE39, ZBarSymbol.CODE93,
                    ZBarSymbol.DATABAR, ZBarSymbol.DATAMATRIX
                ])
                
                for barcode in barcodes:
                    data = barcode.data.decode('utf-8').strip()
                    if data:
                        results.append({
                            'decoder': 'pyzbar',
                            'type': barcode.type,
                            'data': data,
                            'quality': getattr(barcode, 'quality', 'unknown'),
                            'region': region_name,
                            'rect': {
                                'left': barcode.rect.left,
                                'top': barcode.rect.top,
                                'width': barcode.rect.width,
                                'height': barcode.rect.height
                            }
                        })
            except Exception as e:
                results.append({
                    'decoder': 'pyzbar',
                    'error': str(e),
                    'region': region_name
                })
        
        # 方法2: pyzxing解码
        if PYZXING_AVAILABLE and self.pyzxing_reader:
            try:
                zxing_results = self.pyzxing_reader.decode(image)
                for result in zxing_results:
                    if result.parsed and result.parsed.strip():
                        results.append({
                            'decoder': 'pyzxing',
                            'type': result.format,
                            'data': result.parsed.strip(),
                            'region': region_name,
                            'raw': str(result.raw) if hasattr(result, 'raw') else None
                        })
            except Exception as e:
                results.append({
                    'decoder': 'pyzxing',
                    'error': str(e),
                    'region': region_name
                })
        
        return results

class FinalYoloBarcodeTester:
    """最终YOLO条码检测和解码测试器"""
    
    def __init__(self, model_path='barcode_training/barcode_detector_4060ti/weights/best.pt'):
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics 未安装")
            
        self.model = YOLO(model_path)
        self.decoder = FinalBarcodeDecoder()
        
        print(f"\n=== 最终YOLO + 双解码器测试器 ===")
        print(f"🎯 模型路径: {model_path}")
        print(f"🔧 解码器: pyzbar={PYZBAR_AVAILABLE}, pyzxing={PYZXING_AVAILABLE}\n")
    
    def test_single_image_comprehensive(self, image_path):
        """综合测试单张图像"""
        print(f"📷 综合测试: {image_path.name}")
        
        # 读取图像
        image = cv2.imread(str(image_path))
        if image is None:
            return {'error': f'Cannot load image: {image_path}'}
        
        test_results = {
            'image_path': str(image_path),
            'image_size': [image.shape[1], image.shape[0]],
            'yolo_detections': [],
            'full_image_decodes': [],
            'performance': {}
        }
        
        # === 第1步: YOLO检测 + 区域解码 ===
        yolo_start = time.time()
        yolo_results = self.model(image)
        yolo_time = (time.time() - yolo_start) * 1000
        
        test_results['performance']['yolo_inference_ms'] = yolo_time
        
        if yolo_results[0].boxes is not None:
            print(f"  🎯 YOLO检测: {len(yolo_results[0].boxes)} 个区域 ({yolo_time:.1f}ms)")
            
            for i, box in enumerate(yolo_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                # 提取条码区域（稍微扩大边界）
                margin = 5
                x1, y1 = max(0, int(x1-margin)), max(0, int(y1-margin))
                x2, y2 = min(image.shape[1], int(x2+margin)), min(image.shape[0], int(y2+margin))
                
                barcode_region = image[y1:y2, x1:x2]
                region_name = f"region_{i+1}"
                
                # 使用所有解码器解码
                decode_start = time.time()
                decode_results = self.decoder.decode_with_all_methods(barcode_region, region_name)
                decode_time = (time.time() - decode_start) * 1000
                
                detection_info = {
                    'region_id': i+1,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'region_size': [barcode_region.shape[1], barcode_region.shape[0]],
                    'decode_results': decode_results,
                    'decode_time_ms': decode_time,
                    'successful_decodes': len([r for r in decode_results if 'data' in r and r['data']])
                }
                
                # 输出解码结果
                if detection_info['successful_decodes'] > 0:
                    print(f"    ✅ 区域{i+1} [{class_name}] - {detection_info['successful_decodes']}个解码:")
                    for result in decode_results:
                        if 'data' in result:
                            print(f"      {result['decoder']}: {result['type']} | {result['data']}")
                else:
                    print(f"    ❌ 区域{i+1} [{class_name}] - 所有解码器失败")
                    for result in decode_results:
                        if 'error' in result:
                            print(f"      {result['decoder']}: {result['error']}")
                
                test_results['yolo_detections'].append(detection_info)
        else:
            print(f"  🎯 YOLO检测: 0 个区域")
        
        # === 第2步: 全图直接解码对比 ===
        print(f"  🔍 全图直接解码测试...")
        full_decode_start = time.time()
        full_results = self.decoder.decode_with_all_methods(image, "full_image")
        full_decode_time = (time.time() - full_decode_start) * 1000
        
        test_results['performance']['full_image_decode_ms'] = full_decode_time
        test_results['full_image_decodes'] = full_results
        
        if full_results:
            print(f"    ✅ 全图解码成功: {len(full_results)}个")
            for result in full_results:
                if 'data' in result:
                    print(f"      {result['decoder']}: {result['type']} | {result['data']}")
        else:
            print(f"    ❌ 全图解码失败")
        
        # === 统计汇总 ===
        total_yolo_regions = len(test_results['yolo_detections'])
        total_yolo_decodes = sum(d['successful_decodes'] for d in test_results['yolo_detections'])
        full_decode_count = len([r for r in full_results if 'data' in r])
        
        test_results['summary'] = {
            'yolo_regions': total_yolo_regions,
            'yolo_successful_decodes': total_yolo_decodes,
            'full_image_decodes': full_decode_count,
            'yolo_success_rate': (total_yolo_decodes / total_yolo_regions * 100) if total_yolo_regions > 0 else 0,
            'total_processing_time_ms': yolo_time + full_decode_time
        }
        
        print(f"  📊 结果汇总: YOLO区域{total_yolo_regions}个→解码{total_yolo_decodes}个, 全图解码{full_decode_count}个")
        print()
        
        return test_results
    
    def run_comprehensive_test(self, test_images=None):
        """运行综合测试"""
        print("="*60)
        print("🚀 开始最终综合测试")
        print("="*60 + "\n")
        
        if test_images is None:
            # 默认测试图像
            frames_dir = Path('media/detection_frames')
            if frames_dir.exists():
                test_images = list(frames_dir.glob('*.jpg'))[:5]  # 测试前5张
            else:
                print("❌ 找不到测试图像")
                return []
        
        all_results = []
        start_time = time.time()
        
        for i, image_path in enumerate(test_images):
            print(f"=== 测试进度: {i+1}/{len(test_images)} ===")
            result = self.test_single_image_comprehensive(image_path)
            if 'error' not in result:
                all_results.append(result)
        
        total_test_time = time.time() - start_time
        
        # 汇总统计
        if all_results:
            total_images = len(all_results)
            total_yolo_regions = sum(r['summary']['yolo_regions'] for r in all_results)
            total_yolo_decodes = sum(r['summary']['yolo_successful_decodes'] for r in all_results)
            total_full_decodes = sum(r['summary']['full_image_decodes'] for r in all_results)
            
            overall_yolo_rate = (total_yolo_decodes / total_yolo_regions * 100) if total_yolo_regions > 0 else 0
            avg_processing_time = np.mean([r['summary']['total_processing_time_ms'] for r in all_results])
            
            print("="*60)
            print("📊 最终测试结果汇总")
            print("="*60)
            print(f"📷 测试图像: {total_images} 张")
            print(f"🎯 YOLO检测区域: {total_yolo_regions} 个")
            print(f"✅ YOLO区域解码成功: {total_yolo_decodes} 个 ({overall_yolo_rate:.1f}%)")
            print(f"🔍 全图直接解码成功: {total_full_decodes} 个")
            print(f"⚡ 平均处理时间: {avg_processing_time:.1f}ms")
            print(f"📈 估算FPS: {1000/avg_processing_time:.1f}")
            
            if overall_yolo_rate > 50:
                print("🎉 YOLO辅助解码效果优秀!")
            elif overall_yolo_rate > 20:
                print("👍 YOLO辅助解码效果良好")
            else:
                print("⚠️ 解码效果仍需改进")
        
        # 保存详细结果
        output_file = f'final_decode_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_summary': {
                    'total_test_time_seconds': total_test_time,
                    'total_images_tested': len(all_results),
                    'overall_statistics': {
                        'total_yolo_regions': total_yolo_regions if all_results else 0,
                        'total_yolo_decodes': total_yolo_decodes if all_results else 0,
                        'total_full_decodes': total_full_decodes if all_results else 0,
                        'yolo_success_rate_percent': overall_yolo_rate if all_results else 0,
                        'avg_processing_time_ms': avg_processing_time if all_results else 0
                    }
                },
                'detailed_results': all_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细结果已保存到: {output_file}")
        
        return all_results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='最终YOLO + 双解码器测试')
    parser.add_argument('--model', type=str, 
                       default='barcode_training/barcode_detector_4060ti/weights/best.pt',
                       help='YOLO模型路径')
    parser.add_argument('--images', type=str, nargs='*',
                       help='指定测试图像路径')
    
    args = parser.parse_args()
    
    try:
        tester = FinalYoloBarcodeTester(model_path=args.model)
        
        test_images = None
        if args.images:
            test_images = [Path(img) for img in args.images]
        
        tester.run_comprehensive_test(test_images)
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())