#!/usr/bin/env python
"""
可视化YOLO检测和解码测试脚本
显示检测框和解码结果，帮助分析图像质量问题
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

try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    PYZBAR_AVAILABLE = True
except ImportError:
    print("❌ pyzbar 未安装 - 安装命令: pip install pyzbar")
    PYZBAR_AVAILABLE = False

class VisualYoloBarcodeTester:
    """可视化YOLO条码检测和解码测试器"""
    
    def __init__(self, model_path='barcode_training/barcode_detector_4060ti/weights/best.pt'):
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics 未安装")
        if not PYZBAR_AVAILABLE:
            raise ImportError("pyzbar 未安装")
            
        self.model = YOLO(model_path)
        self.output_dir = Path('visual_test_output')
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"\n=== 可视化YOLO + 条码解码测试器 ===")
        print(f"🎯 模型路径: {model_path}")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🖼️ 可视化模式: 显示检测框和解码结果\n")
    
    def analyze_image_quality(self, image):
        """分析图像质量指标"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 计算各种质量指标
        height, width = gray.shape
        
        # 分辨率
        resolution = width * height
        
        # 模糊度（Laplacian方差）
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 对比度（标准差）
        contrast = gray.std()
        
        # 亮度（均值）
        brightness = gray.mean()
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        return {
            'resolution': resolution,
            'width': width,
            'height': height,
            'blur_score': blur_score,
            'contrast': contrast,
            'brightness': brightness,
            'edge_density': edge_density
        }
    
    def decode_barcode_simple(self, image):
        """简单条码解码，返回详细错误信息"""
        try:
            # 尝试解码
            barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.CODE128, ZBarSymbol.QRCODE, 
                                                   ZBarSymbol.EAN13, ZBarSymbol.EAN8,
                                                   ZBarSymbol.UPCA, ZBarSymbol.UPCE,
                                                   ZBarSymbol.CODE39, ZBarSymbol.CODE93,
                                                   ZBarSymbol.DATABAR, ZBarSymbol.DATAMATRIX])
            
            results = []
            for barcode in barcodes:
                data = barcode.data.decode('utf-8').strip()
                if data:
                    results.append({
                        'type': barcode.type,
                        'data': data,
                        'quality': barcode.quality if hasattr(barcode, 'quality') else 'unknown',
                        'rect': {
                            'left': barcode.rect.left,
                            'top': barcode.rect.top,
                            'width': barcode.rect.width,
                            'height': barcode.rect.height
                        }
                    })
            
            return {'success': True, 'results': results, 'count': len(results)}
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'results': [], 'count': 0}
    
    def test_single_image_visual(self, image_path):
        """可视化测试单张图像"""
        print(f"📷 分析图像: {image_path.name}")
        
        # 读取图像
        image = cv2.imread(str(image_path))
        if image is None:
            return {'error': f'Cannot load image: {image_path}'}
        
        # 分析图像质量
        quality = self.analyze_image_quality(image)
        print(f"  📊 图像质量: {quality['width']}x{quality['height']}, 模糊度:{quality['blur_score']:.1f}, 对比度:{quality['contrast']:.1f}")
        
        # 创建可视化图像副本
        vis_image = image.copy()
        
        # YOLO检测
        start_time = time.time()
        yolo_results = self.model(image)
        yolo_time = (time.time() - start_time) * 1000
        
        analysis_results = {
            'image_path': str(image_path),
            'image_quality': quality,
            'yolo_inference_time_ms': yolo_time,
            'detections': []
        }
        
        # 处理检测结果
        if yolo_results[0].boxes is not None:
            print(f"  🎯 YOLO检测: {len(yolo_results[0].boxes)} 个区域 ({yolo_time:.1f}ms)")
            
            for i, box in enumerate(yolo_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                # 绘制YOLO检测框（蓝色）
                cv2.rectangle(vis_image, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                cv2.putText(vis_image, f'YOLO: {class_name} {confidence:.2f}', 
                           (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                # 提取条码区域
                barcode_region = image[int(y1):int(y2), int(x1):int(x2)]
                
                # 解码条码区域
                decode_result = self.decode_barcode_simple(barcode_region)
                decode_time = 0  # 简化版本，不计时间
                
                detection_info = {
                    'detection_id': i+1,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'region_size': [barcode_region.shape[1], barcode_region.shape[0]],
                    'decode_result': decode_result,
                    'decode_time_ms': decode_time
                }
                
                # 可视化解码结果
                if decode_result['success'] and decode_result['count'] > 0:
                    # 成功解码 - 绿色框
                    cv2.rectangle(vis_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                    
                    for j, barcode in enumerate(decode_result['results']):
                        print(f"    ✅ 区域{i+1}: {barcode['type']} | {barcode['data']}")
                        cv2.putText(vis_image, f"✅ {barcode['data']}", 
                                   (int(x1), int(y2) + 25 + j*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    # 解码失败 - 红色框
                    cv2.rectangle(vis_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                    cv2.putText(vis_image, '❌ Decode Failed', 
                               (int(x1), int(y2) + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    print(f"    ❌ 区域{i+1}: 解码失败 - {decode_result.get('error', 'Unknown error')}")
                
                analysis_results['detections'].append(detection_info)
        else:
            print(f"  🎯 YOLO检测: 0 个区域")
        
        # 测试全图解码
        full_decode_result = self.decode_barcode_simple(image)
        if full_decode_result['success'] and full_decode_result['count'] > 0:
            for barcode in full_decode_result['results']:
                rect = barcode['rect']
                x, y, w, h = rect['left'], rect['top'], rect['width'], rect['height']
                # 绘制全图检测结果（黄色）
                cv2.rectangle(vis_image, (x, y), (x+w, y+h), (0, 255, 255), 2)
                cv2.putText(vis_image, f"Full: {barcode['data']}", 
                           (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        analysis_results['full_image_decode'] = full_decode_result
        
        # 保存可视化结果
        output_path = self.output_dir / f"visual_{image_path.stem}.jpg"
        cv2.imwrite(str(output_path), vis_image)
        print(f"  💾 可视化结果: {output_path}")
        
        return analysis_results
    
    def run_visual_test(self, test_image_path=None):
        """运行可视化测试"""
        print("="*60)
        print("🚀 开始可视化YOLO + 条码解码测试")
        print("="*60 + "\n")
        
        if test_image_path:
            # 测试指定图像
            test_images = [Path(test_image_path)]
        else:
            # 测试media/detection_frames中的图像
            frames_dir = Path('media/detection_frames')
            if frames_dir.exists():
                test_images = list(frames_dir.glob('*.jpg'))[:3]  # 只测试前3张
            else:
                print("❌ 找不到测试图像目录")
                return []
        
        all_results = []
        
        for image_path in test_images:
            if image_path.exists():
                result = self.test_single_image_visual(image_path)
                if 'error' not in result:
                    all_results.append(result)
                print()
        
        # 保存详细结果
        output_file = self.output_dir / f'visual_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_summary': {
                    'total_images_tested': len(all_results),
                    'output_directory': str(self.output_dir)
                },
                'detailed_results': all_results
            }, f, indent=2, ensure_ascii=False)
        
        print("="*60)
        print("📊 可视化测试完成")
        print("="*60)
        print(f"📁 可视化图像: {self.output_dir}")
        print(f"📄 详细结果: {output_file}")
        print(f"\n💡 检查可视化图像来分析:")
        print(f"  - 🔵 蓝色框: YOLO检测")
        print(f"  - 🟢 绿色框: 解码成功")
        print(f"  - 🔴 红色框: 解码失败")
        print(f"  - 🟡 黄色框: 全图检测")
        
        return all_results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='可视化YOLO + 条码解码测试')
    parser.add_argument('--image', type=str, help='测试特定图像路径')
    parser.add_argument('--model', type=str, 
                       default='barcode_training/barcode_detector_4060ti/weights/best.pt',
                       help='YOLO模型路径')
    
    args = parser.parse_args()
    
    try:
        tester = VisualYoloBarcodeTester(model_path=args.model)
        tester.run_visual_test(test_image_path=args.image)
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())