#!/usr/bin/env python
"""
本地版YOLO + 条码解码测试脚本
结合YOLO4060ti模型和pyzbar/pyzxing解码，实现完整的条码识别流程
专为本地环境设计，无需Docker
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob
import sys

# Import barcode decoding libraries with fallback
def check_and_import_decoders():
    """检查并导入可用的条码解码库"""
    decoders = {}
    
    # Try to import pyzbar
    try:
        from pyzbar import pyzbar
        decoders['pyzbar'] = pyzbar
        print("✅ pyzbar 可用")
    except ImportError:
        print("⚠️ pyzbar 不可用 - 安装命令: pip install pyzbar")
        print("   Windows可能需要额外安装: https://github.com/mhammond/pywin32/releases")
    
    # Try to import pyzxing
    try:
        from pyzxing import BarCodeReader
        decoders['pyzxing'] = BarCodeReader()
        print("✅ pyzxing 可用")
    except ImportError:
        print("⚠️ pyzxing 不可用 - 安装命令: pip install pyzxing")
        print("   需要Java环境支持")
    
    return decoders

class LocalYOLOBarcodeTester:
    def __init__(self, model_path=None):
        """
        初始化本地测试器
        Args:
            model_path: YOLO模型路径，如果为None则使用默认4060ti模型
        """
        # 设置模型路径
        if model_path is None:
            model_path = 'barcode_training/barcode_detector_4060ti/weights/best.pt'
        
        self.model_path = model_path
        
        # 检查模型文件
        if not os.path.exists(model_path):
            print(f"❌ 模型文件不存在: {model_path}")
            print("请确保模型文件存在，或指定正确的模型路径")
            sys.exit(1)
        
        # 加载YOLO模型
        try:
            self.model = YOLO(model_path)
            print(f"✅ 成功加载YOLO模型: {model_path}")
        except Exception as e:
            print(f"❌ 加载YOLO模型失败: {e}")
            sys.exit(1)
        
        # 初始化解码器
        self.decoders = check_and_import_decoders()
        
        if not self.decoders:
            print("❌ 没有可用的解码器，请安装至少一个解码库")
            print("推荐安装: pip install pyzbar")
            sys.exit(1)
        
        # 查找测试图像
        self.test_images = self.find_test_images()
        
        print(f"\n=== 本地YOLO + 条码解码测试器 ===")
        print(f"📂 工作目录: {os.getcwd()}")
        print(f"🎯 模型路径: {model_path}")
        print(f"🖼️ 测试图像: {len(self.test_images)} 张")
        print(f"🔧 可用解码器: {list(self.decoders.keys())}")
        
    def find_test_images(self):
        """查找本地测试图像"""
        images = []
        
        # 搜索路径（按优先级排序）
        search_paths = [
            'barcode_dataset/images/val/*.jpg',
            'barcode_dataset/images/test/*.jpg',
            'media/detection_frames/*.jpg',
            'runs/detect/predict/*.jpg',  # YOLO预测结果
            'barcode_dataset/images/train/*.jpg',  # 训练图像
            '*.jpg',
            '*.png'
        ]
        
        for pattern in search_paths:
            found = glob.glob(pattern)
            if found:
                images.extend(found)
                print(f"📁 从 {pattern} 找到 {len(found)} 张图像")
        
        # 去重并限制数量
        images = list(set(images))
        
        # 如果没有找到图像，创建一个示例列表
        if not images:
            print("⚠️ 没有找到测试图像，请确保有.jpg或.png文件")
            # 尝试创建一个测试图像
            self.create_test_image()
            images = glob.glob('test_barcode_*.jpg')
        
        return images[:10]  # 最多测试10张
    
    def create_test_image(self):
        """创建一个简单的测试图像"""
        import numpy as np
        
        # 创建一个包含简单条码的测试图像
        img = np.ones((200, 400, 3), dtype=np.uint8) * 255  # 白色背景
        
        # 绘制一些模拟条码的黑白条纹
        for i in range(0, 350, 20):
            if (i // 20) % 2 == 0:
                img[50:150, i:i+10] = 0  # 黑色条纹
        
        cv2.imwrite('test_barcode_sample.jpg', img)
        print("📝 创建了测试图像: test_barcode_sample.jpg")
    
    def preprocess_image(self, image):
        """图像预处理，提高解码成功率"""
        # 增强对比度
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # 降噪
        denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
        
        return denoised
    
    def decode_with_pyzbar(self, image):
        """使用pyzbar解码条码"""
        if 'pyzbar' not in self.decoders:
            return []
        
        try:
            # 图像预处理
            processed = self.preprocess_image(image)
            
            decoded_objects = self.decoders['pyzbar'].decode(processed)
            results = []
            
            for obj in decoded_objects:
                rect = obj.rect
                results.append({
                    'decoder': 'pyzbar',
                    'type': obj.type,
                    'data': obj.data.decode('utf-8'),
                    'quality': getattr(obj, 'quality', None),
                    'bbox': [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height],
                    'confidence': 1.0
                })
            
            return results
            
        except Exception as e:
            print(f"    ⚠️ pyzbar解码失败: {e}")
            return []
    
    def decode_with_pyzxing(self, image):
        """使用pyzxing解码条码"""
        if 'pyzxing' not in self.decoders:
            return []
        
        try:
            # 图像预处理
            processed = self.preprocess_image(image)
            
            results = []
            decoded_objects = self.decoders['pyzxing'].decode(processed)
            
            if decoded_objects:
                for obj in decoded_objects:
                    if obj.parsed:  # 只包含成功解码的
                        results.append({
                            'decoder': 'pyzxing',
                            'type': obj.format,
                            'data': str(obj.parsed),
                            'bbox': getattr(obj, 'rect', None),
                            'confidence': getattr(obj, 'confidence', None)
                        })
            
            return results
            
        except Exception as e:
            print(f"    ⚠️ pyzxing解码失败: {e}")
            return []
    
    def test_single_image(self, image_path):
        """测试单张图像的完整流程"""
        print(f"\n📷 测试图像: {os.path.basename(image_path)}")
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            return {
                'error': f'无法加载图像: {image_path}',
                'image_path': image_path
            }
        
        image_info = {
            'path': image_path,
            'size': [image.shape[1], image.shape[0]],  # [width, height]
            'channels': image.shape[2]
        }
        
        # Step 1: YOLO检测
        yolo_start = time.time()
        yolo_results = self.model(image, conf=0.25)  # 使用较低置信度以获得更多候选
        yolo_time = (time.time() - yolo_start) * 1000
        
        # 解析YOLO检测结果
        yolo_detections = []
        if yolo_results[0].boxes is not None:
            for i, box in enumerate(yolo_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                yolo_detections.append({
                    'id': i,
                    'class': class_name,
                    'class_id': class_id,
                    'confidence': confidence,
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'center': [(float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2],
                    'area': float((x2 - x1) * (y2 - y1))
                })
        
        # Step 2: 对每个检测区域进行解码
        decode_results = []
        decode_start = time.time()
        
        for detection in yolo_detections:
            bbox = detection['bbox']
            
            # 提取ROI
            x1, y1, x2, y2 = map(int, bbox)
            roi = image[y1:y2, x1:x2]
            
            if roi.size > 0:  # 确保ROI不为空
                # 尝试所有可用解码器
                all_decoded = []
                
                # 优先使用pyzbar（更快，适合常见条码）
                pyzbar_results = self.decode_with_pyzbar(roi)
                all_decoded.extend(pyzbar_results)
                
                # 如果pyzbar失败，尝试pyzxing
                if not pyzbar_results and 'pyzxing' in self.decoders:
                    pyzxing_results = self.decode_with_pyzxing(roi)
                    all_decoded.extend(pyzing_results)
                
                # 调整边界框坐标到原图
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
                    'detection_id': detection['id'],
                    'yolo_class': detection['class'],
                    'yolo_confidence': detection['confidence'],
                    'roi_bbox': bbox,
                    'decoded_results': all_decoded,
                    'decode_success': len(all_decoded) > 0
                })
        
        decode_time = (time.time() - decode_start) * 1000
        total_time = (time.time() - yolo_start) * 1000
        
        # Step 3: 全图解码对比
        full_image_results = {
            'pyzbar': self.decode_with_pyzbar(image),
            'pyzxing': self.decode_with_pyzxing(image) if 'pyzxing' in self.decoders else []
        }
        
        # 显示结果
        print(f"  🎯 YOLO检测: {len(yolo_detections)} 个区域 ({yolo_time:.1f}ms)")
        print(f"  🔓 成功解码: {len([r for r in decode_results if r['decode_success']])} 个区域")
        print(f"  ⏱️ 总耗时: {total_time:.1f}ms")
        
        # 显示解码详情
        successful_decodes = 0
        for i, decode_result in enumerate(decode_results):
            if decode_result['decode_success']:
                successful_decodes += 1
                print(f"    ✅ 区域{i+1} [{decode_result['yolo_class']}]:")
                for decoded in decode_result['decoded_results']:
                    print(f"      {decoded['decoder']} | {decoded['type']} | {decoded['data']}")
            else:
                print(f"    ❌ 区域{i+1} [{decode_result['yolo_class']}]: 解码失败")
        
        # 显示全图解码结果对比
        total_full_decodes = len(full_image_results['pyzbar']) + len(full_image_results['pyzxing'])
        if total_full_decodes > 0:
            print(f"  🔍 全图解码: pyzbar={len(full_image_results['pyzbar'])}, pyzxing={len(full_image_results['pyzxing'])}")
        
        return {
            'image_info': image_info,
            'yolo_results': {
                'detections': yolo_detections,
                'count': len(yolo_detections),
                'inference_time_ms': yolo_time
            },
            'decode_results': {
                'attempts': decode_results,
                'successful_attempts': len([r for r in decode_results if r['decode_success']]),
                'decode_time_ms': decode_time
            },
            'full_image_decodes': full_image_results,
            'performance': {
                'total_time_ms': total_time,
                'fps': 1000 / total_time if total_time > 0 else 0
            },
            'success': True
        }
    
    def run_all_tests(self):
        """运行所有测试"""
        print(f"\n{'='*60}")
        print(f"🚀 开始本地YOLO + 条码解码测试")
        print(f"{'='*60}")
        
        if not self.test_images:
            print("❌ 没有找到测试图像")
            return None, None
        
        results = []
        
        for i, image_path in enumerate(self.test_images):
            print(f"\n--- 测试进度: {i+1}/{len(self.test_images)} ---")
            result = self.test_single_image(image_path)
            results.append(result)
            
            # 简短的进度提示
            if result.get('success', False):
                yolo_count = result['yolo_results']['count']
                decode_count = result['decode_results']['successful_attempts']
                print(f"  📊 结果: 检测{yolo_count}个, 解码成功{decode_count}个")
        
        # 分析和汇总结果
        print(f"\n{'='*60}")
        print(f"📊 测试结果汇总")
        print(f"{'='*60}")
        
        successful_results = [r for r in results if r.get('success', False)]
        
        if successful_results:
            total_yolo_detections = sum(r['yolo_results']['count'] for r in successful_results)
            total_successful_decodes = sum(r['decode_results']['successful_attempts'] for r in successful_results)
            total_yolo_time = sum(r['yolo_results']['inference_time_ms'] for r in successful_results)
            total_decode_time = sum(r['decode_results']['decode_time_ms'] for r in successful_results)
            total_time = sum(r['performance']['total_time_ms'] for r in successful_results)
            
            print(f"✅ 成功测试: {len(successful_results)}/{len(results)} 张图像")
            print(f"🎯 YOLO检测总数: {total_yolo_detections} 个区域")
            print(f"🔓 成功解码总数: {total_successful_decodes} 个条码")
            
            if total_yolo_detections > 0:
                success_rate = total_successful_decodes / total_yolo_detections
                print(f"📈 解码成功率: {success_rate:.1%}")
            
            print(f"⚡ 平均性能:")
            print(f"  - YOLO推理: {total_yolo_time/len(successful_results):.1f}ms")
            print(f"  - 条码解码: {total_decode_time/len(successful_results):.1f}ms")
            print(f"  - 总耗时: {total_time/len(successful_results):.1f}ms")
            print(f"  - FPS: {len(successful_results)*1000/total_time:.1f}")
        
        # 保存详细结果
        output_file = f'local_yolo_decode_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        full_results = {
            'test_info': {
                'model_path': self.model_path,
                'test_time': datetime.now().isoformat(),
                'working_directory': os.getcwd(),
                'total_images': len(self.test_images),
                'successful_images': len(successful_results),
                'available_decoders': list(self.decoders.keys())
            },
            'summary': {
                'total_images_tested': len(successful_results),
                'total_yolo_detections': total_yolo_detections if successful_results else 0,
                'total_successful_decodes': total_successful_decodes if successful_results else 0,
                'decode_success_rate': total_successful_decodes/total_yolo_detections if successful_results and total_yolo_detections > 0 else 0,
                'avg_total_time_ms': total_time/len(successful_results) if successful_results else 0,
                'avg_fps': len(successful_results)*1000/total_time if successful_results and total_time > 0 else 0
            } if successful_results else {},
            'detailed_results': results
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 详细结果已保存到: {output_file}")
        except Exception as e:
            print(f"\n⚠️ 保存结果失败: {e}")
        
        return results, full_results.get('summary', {})

def main():
    """主函数"""
    print("🔍 本地YOLO + 条码解码测试工具")
    
    # 检查命令行参数
    model_path = None
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        print(f"📂 使用指定模型: {model_path}")
    
    # 创建测试器
    tester = LocalYOLOBarcodeTester(model_path)
    
    # 运行测试
    results, summary = tester.run_all_tests()
    
    # 最终总结
    print(f"\n{'='*60}")
    print(f"🎉 测试完成!")
    
    if summary:
        success_rate = summary.get('decode_success_rate', 0)
        avg_fps = summary.get('avg_fps', 0)
        
        print(f"📊 核心指标:")
        print(f"  ✅ 平均FPS: {avg_fps:.1f}")
        print(f"  🔓 解码成功率: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            print(f"  🏆 解码效果优秀！")
        elif success_rate >= 0.6:
            print(f"  👍 解码效果良好")
        elif success_rate >= 0.4:
            print(f"  ⚠️ 解码效果一般，建议优化")
        else:
            print(f"  ❌ 解码效果需要改进")
        
        # 优化建议
        print(f"\n💡 优化建议:")
        if success_rate < 0.7:
            print(f"  - 调整YOLO置信度阈值")
            print(f"  - 增强图像预处理")
            print(f"  - 尝试不同的解码器组合")
        
        if not tester.decoders.get('pyzbar'):
            print(f"  - 安装pyzbar提高解码速度: pip install pyzbar")
        
        if avg_fps < 10:
            print(f"  - 考虑使用更小的YOLO模型或GPU加速")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()