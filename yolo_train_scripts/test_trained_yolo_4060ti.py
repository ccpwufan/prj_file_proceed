#!/usr/bin/env python
"""
4060ti训练后的YOLO模型测试脚本
测试专门训练的条码检测模型性能
"""
import cv2
import json
import time
import os
from datetime import datetime
from ultralytics import YOLO
import glob

class TrainedYolo4060tiTester:
    def __init__(self, model_path):
        """加载训练好的4060ti模型"""
        self.model = YOLO(model_path)
        self.model_path = model_path
        
        # 寻找测试图像
        self.test_images = self.find_test_images()
        
        print(f"=== 4060ti训练模型测试器 ===")
        print(f"模型路径: {model_path}")
        print(f"找到测试图像: {len(self.test_images)} 张")
        
    def find_test_images(self):
        """自动查找测试图像"""
        test_images = []
        
        # 搜索可能的测试图像路径
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
                
        # 去重并限制数量
        test_images = list(set(test_images))[:10]  # 最多测试10张
        
        return test_images
    
    def test_single_image(self, image_path):
        """测试单张图像的检测效果"""
        start_time = time.time()
        
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            return {
                'error': f'无法加载图像: {image_path}',
                'image_path': image_path
            }
        
        # 运行检测
        results = self.model(image, conf=0.25)  # 使用训练时相同的置信度
        
        # 计算推理时间
        inference_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 解析检测结果
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    detections.append({
                        'class': class_name,
                        'class_id': class_id,
                        'confidence': confidence,
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'center': [(float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2],
                        'area': float((x2 - x1) * (y2 - y1))
                    })
        
        return {
            'image_path': image_path,
            'image_size': [image.shape[1], image.shape[0]],  # [width, height]
            'detections': detections,
            'detection_count': len(detections),
            'inference_time_ms': inference_time,
            'fps': 1000 / inference_time if inference_time > 0 else 0,
            'success': True
        }
    
    def analyze_results(self, results):
        """分析测试结果"""
        if not results:
            return {}
        
        total_images = len([r for r in results if r.get('success', False)])
        total_detections = sum(r.get('detection_count', 0) for r in results)
        total_inference_time = sum(r.get('inference_time_ms', 0) for r in results if r.get('success', False))
        
        # 统计各类别检测数量
        class_counts = {}
        confidence_scores = []
        
        for result in results:
            for detection in result.get('detections', []):
                class_name = detection['class']
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
                confidence_scores.append(detection['confidence'])
        
        analysis = {
            'total_images_tested': total_images,
            'total_detections': total_detections,
            'avg_detections_per_image': total_detections / total_images if total_images > 0 else 0,
            'avg_inference_time_ms': total_inference_time / total_images if total_images > 0 else 0,
            'avg_fps': 1000 / (total_inference_time / total_images) if total_images > 0 and total_inference_time > 0 else 0,
            'class_distribution': class_counts,
            'avg_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'min_confidence': min(confidence_scores) if confidence_scores else 0,
            'max_confidence': max(confidence_scores) if confidence_scores else 0
        }
        
        return analysis
    
    def run_all_tests(self):
        """运行所有测试图像"""
        print(f"\n=== 开始测试4060ti训练模型 ===")
        print(f"测试图像数量: {len(self.test_images)}")
        print("-" * 60)
        
        results = []
        
        for i, image_path in enumerate(self.test_images):
            print(f"测试 {i+1}/{len(self.test_images)}: {os.path.basename(image_path)}")
            
            result = self.test_single_image(image_path)
            results.append(result)
            
            if result.get('success', False):
                detections = result.get('detection_count', 0)
                inference_time = result.get('inference_time_ms', 0)
                fps = result.get('fps', 0)
                
                print(f"  ✓ 检测到 {detections} 个对象")
                print(f"  ⏱️ 推理时间: {inference_time:.1f}ms ({fps:.1f} FPS)")
                
                # 显示检测到的类别
                if detections > 0:
                    classes = [d['class'] for d in result['detections']]
                    print(f"  📦 类别: {', '.join(set(classes))}")
            else:
                print(f"  ✗ 测试失败: {result.get('error', '未知错误')}")
            
            print()
        
        # 分析结果
        print("=== 测试结果分析 ===")
        analysis = self.analyze_results(results)
        
        if analysis:
            print(f"✅ 成功测试图像: {analysis['total_images_tested']}")
            print(f"🔍 总检测数量: {analysis['total_detections']}")
            print(f"📊 平均每图检测: {analysis['avg_detections_per_image']:.1f} 个")
            print(f"⚡ 平均推理时间: {analysis['avg_inference_time_ms']:.1f}ms")
            print(f"🚀 平均FPS: {analysis['avg_fps']:.1f}")
            
            if analysis['class_distribution']:
                print(f"\n📈 类别分布:")
                for class_name, count in analysis['class_distribution'].items():
                    print(f"  {class_name}: {count} 个")
            
            print(f"\n🎯 置信度统计:")
            print(f"  平均置信度: {analysis['avg_confidence']:.3f}")
            print(f"  最高置信度: {analysis['max_confidence']:.3f}")
            print(f"  最低置信度: {analysis['min_confidence']:.3f}")
        
        # 保存详细结果
        output_file = f'yolo_4060ti_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        full_results = {
            'test_info': {
                'model_path': self.model_path,
                'test_time': datetime.now().isoformat(),
                'total_images': len(self.test_images)
            },
            'analysis': analysis,
            'detailed_results': results
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 详细结果已保存到: {output_file}")
        except Exception as e:
            print(f"\n⚠️  保存结果文件失败: {e}")
        
        return results, analysis
    
    def compare_with_baseline(self):
        """与原始YOLO模型对比"""
        print("\n=== 与原始YOLOv8n对比 ===")
        
        # 加载原始模型进行对比
        try:
            original_model = YOLO('yolov8n.pt')
            
            # 选择第一张测试图像进行对比
            if not self.test_images:
                print("❌ 没有测试图像可进行对比")
                return
            
            test_image = self.test_images[0]
            image = cv2.imread(test_image)
            
            if image is None:
                print(f"❌ 无法加载对比图像: {test_image}")
                return
            
            # 原始模型检测
            print(f"🔄 使用图像: {os.path.basename(test_image)}")
            
            start_time = time.time()
            original_results = original_model(image, conf=0.25)
            original_time = (time.time() - start_time) * 1000
            
            original_detections = len(original_results[0].boxes) if original_results[0].boxes else 0
            
            # 训练模型检测
            start_time = time.time()
            trained_results = self.model(image, conf=0.25)
            trained_time = (time.time() - start_time) * 1000
            
            trained_detections = len(trained_results[0].boxes) if trained_results[0].boxes else 0
            
            # 对比结果
            print(f"\n📊 对比结果:")
            print(f"原始YOLOv8n:")
            print(f"  检测数量: {original_detections}")
            print(f"  推理时间: {original_time:.1f}ms")
            print(f"  FPS: {1000/original_time:.1f}")
            
            print(f"\n4060ti训练模型:")
            print(f"  检测数量: {trained_detections}")
            print(f"  推理时间: {trained_time:.1f}ms") 
            print(f"  FPS: {1000/trained_time:.1f}")
            
            # 计算提升
            if original_detections > 0:
                detection_improvement = ((trained_detections - original_detections) / original_detections) * 100
                print(f"\n🚀 性能提升:")
                print(f"  检测数量: {detection_improvement:+.1f}%")
                print(f"  推理速度: {((original_time - trained_time) / original_time) * 100:+.1f}%")
            
        except Exception as e:
            print(f"❌ 对比测试失败: {e}")

def main():
    """主函数"""
    # 4060ti训练模型路径
    model_path = 'barcode_training/barcode_detector_4060ti/weights/best.pt'
    
    # 检查模型文件是否存在
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        print("请先运行训练脚本生成模型")
        return
    
    # 创建测试器
    tester = TrainedYolo4060tiTester(model_path)
    
    # 运行所有测试
    results, analysis = tester.run_all_tests()
    
    # 与原始模型对比
    tester.compare_with_baseline()
    
    # 总结
    print(f"\n{'='*60}")
    print(f"🎉 4060ti YOLO模型测试完成!")
    
    if analysis:
        avg_fps = analysis.get('avg_fps', 0)
        total_detections = analysis.get('total_detections', 0)
        
        print(f"📊 核心指标:")
        print(f"  ✅ 平均FPS: {avg_fps:.1f} ({'优秀' if avg_fps >= 30 else '良好' if avg_fps >= 20 else '需优化'})")
        print(f"  🔍 总检测数量: {total_detections} ({'充足' if total_detections >= 5 else '较少'})")
        print(f"  🎯 平均置信度: {analysis.get('avg_confidence', 0):.3f}")
        
        if avg_fps >= 30 and total_detections >= 5:
            print(f"\n🏆 模型性能优秀，可用于生产环境!")
        else:
            print(f"\n⚠️ 模型性能可进一步优化")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()