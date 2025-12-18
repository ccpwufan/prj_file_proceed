#!/usr/bin/env python
"""
训练后的YOLO模型测试脚本 - 增强版
支持v2模型测试、可视化、性能对比
"""
import cv2
import json
import os
import time
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import glob

class TrainedYoloTester:
    def __init__(self, model_path, compare_with_original=True):
        """加载训练好的模型"""
        self.model = YOLO(model_path)
        self.model_path = model_path
        
        # 获取所有测试图像
        self.test_images = self.get_test_images()
        
        # 是否与原始模型对比
        self.compare_with_original = compare_with_original
        if compare_with_original:
            self.original_model = YOLO('yolov8n.pt')
        
        # 创建输出目录
        self.output_dir = f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'visualizations'), exist_ok=True)
        
        print(f"测试输出目录: {self.output_dir}")
        print(f"找到 {len(self.test_images)} 张测试图像")
    
    def get_test_images(self):
        """获取所有测试图像"""
        test_dir = '/app/media/detection_frames'
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        
        test_images = []
        for ext in image_extensions:
            test_images.extend(glob.glob(os.path.join(test_dir, ext)))
            test_images.extend(glob.glob(os.path.join(test_dir, ext.upper())))
        
        return sorted(test_images)
    
    def draw_detections(self, image, detections, model_name="Trained"):
        """在图像上绘制检测结果"""
        result_img = image.copy()
        
        # Define colors for different classes
        colors = {
            'barcode': (0, 255, 0),      # Green
            'datamatrix': (255, 0, 0),   # Red  
            'qrcode': (0, 0, 255)        # Blue
        }
        
        for detection in detections:
            class_name = detection['class']
            confidence = detection['confidence']
            x1, y1, x2, y2 = detection['bbox']
            
            color = colors.get(class_name, (128, 128, 128))
            
            # Draw bounding box
            cv2.rectangle(result_img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_img, (int(x1), int(y1) - label_size[1] - 10), 
                         (int(x1) + label_size[0], int(y1)), color, -1)
            cv2.putText(result_img, label, (int(x1), int(y1) - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Add model info
        cv2.putText(result_img, f"Model: {model_name}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return result_img
    
    def test_single_image(self, image_path, model=None, save_visualization=False):
        """测试单张图像"""
        if model is None:
            model = self.model
            model_name = "Trained"
        else:
            model_name = "Original"
            
        image = cv2.imread(image_path)
        if image is None:
            return {'error': f'Cannot load image: {image_path}'}
        
        # 记录推理时间
        start_time = time.time()
        results = model(image)
        inference_time = time.time() - start_time
        
        # 解析结果
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = model.names[class_id]
                    
                    detections.append({
                        'class': class_name,
                        'confidence': float(confidence),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                    })
        
        result = {
            'image_path': image_path,
            'model_name': model_name,
            'detections': detections,
            'detection_count': len(detections),
            'inference_time': inference_time,
            'class_distribution': self.get_class_distribution(detections)
        }
        
        # 保存可视化结果
        if save_visualization:
            result_img = self.draw_detections(image, detections, model_name)
            vis_path = os.path.join(self.output_dir, 'visualizations', 
                                   f"{os.path.basename(image_path).split('.')[0]}_{model_name}.jpg")
            cv2.imwrite(vis_path, result_img)
            result['visualization_path'] = vis_path
        
        return result
    
    def get_class_distribution(self, detections):
        """获取类别分布统计"""
        distribution = {}
        for detection in detections:
            class_name = detection['class']
            if class_name not in distribution:
                distribution[class_name] = 0
            distribution[class_name] += 1
        return distribution
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始测试训练后的YOLO模型...")
        results = []
        
        for image_path in self.test_images:
            result = self.test_single_image(image_path, save_visualization=True)
            results.append(result)
            print(f"测试完成: {image_path}")
            print(f"检测结果: {len(result.get('detections', []))} 个对象")
        
        # 保存测试结果
        output_file = os.path.join(self.output_dir, f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"测试结果已保存到: {output_file}")
        
        # 生成统计报告
        self.generate_summary_report(results, output_file)
        
        return results
    
    def run_comparison_test(self):
        """运行对比测试（训练模型 vs 原始模型）"""
        if not self.compare_with_original:
            print("对比测试未启用")
            return None
            
        print("开始对比测试（训练模型 vs 原始模型）...")
        comparison_results = []
        
        for image_path in self.test_images[:5]:  # 测试前5张图像
            # 测试训练模型
            trained_result = self.test_single_image(image_path, self.model, "Trained", save_visualization=True)
            
            # 测试原始模型
            original_result = self.test_single_image(image_path, self.original_model, "Original", save_visualization=True)
            
            comparison = {
                'image_path': image_path,
                'trained_model': {
                    'detections': trained_result['detection_count'],
                    'inference_time': trained_result['inference_time'],
                    'classes': trained_result['class_distribution']
                },
                'original_model': {
                    'detections': original_result['detection_count'],
                    'inference_time': original_result['inference_time'],
                    'classes': original_result['class_distribution']
                },
                'improvement': {
                    'detection_improvement': trained_result['detection_count'] - original_result['detection_count'],
                    'speed_comparison': original_result['inference_time'] - trained_result['inference_time']
                }
            }
            
            comparison_results.append(comparison)
            
            print(f"对比测试: {os.path.basename(image_path)}")
            print(f"  训练模型: {trained_result['detection_count']} 检测, {trained_result['inference_time']:.3f}s")
            print(f"  原始模型: {original_result['detection_count']} 检测, {original_result['inference_time']:.3f}s")
            print(f"  改进: {comparison['improvement']['detection_improvement']} 检测, {comparison['improvement']['speed_comparison']:.3f}s")
        
        # 保存对比结果
        comparison_file = os.path.join(self.output_dir, f'comparison_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, indent=2, ensure_ascii=False)
        
        print(f"对比结果已保存到: {comparison_file}")
        return comparison_results
    
    def generate_summary_report(self, results, output_file):
        """生成统计报告"""
        total_images = len(results)
        total_detections = sum(r['detection_count'] for r in results)
        avg_inference_time = sum(r['inference_time'] for r in results) / total_images
        
        # 统计各类别检测数量
        class_stats = {}
        for result in results:
            for class_name, count in result['class_distribution'].items():
                if class_name not in class_stats:
                    class_stats[class_name] = 0
                class_stats[class_name] += count
        
        print("\n=== 测试统计报告 ===")
        print(f"测试图像数量: {total_images}")
        print(f"总检测数量: {total_detections}")
        print(f"平均每张图像检测数: {total_detections/total_images:.2f}")
        print(f"平均推理时间: {avg_inference_time:.3f}s")
        print(f"FPS: {1/avg_inference_time:.1f}")
        print("\n各类别检测统计:")
        for class_name, count in class_stats.items():
            print(f"  {class_name}: {count} 个")
        
        # 保存统计报告
        summary = {
            'test_date': datetime.now().isoformat(),
            'model_path': self.model_path,
            'statistics': {
                'total_images': total_images,
                'total_detections': total_detections,
                'avg_detections_per_image': total_detections/total_images,
                'avg_inference_time': avg_inference_time,
                'fps': 1/avg_inference_time,
                'class_distribution': class_stats
            }
        }
        
        summary_file = os.path.join(self.output_dir, 'summary_report.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存到: {summary_file}")

if __name__ == "__main__":
    # 使用训练好的v2模型路径
    tester = TrainedYoloTester('barcode_training/barcode_detector_v2/weights/best.pt', compare_with_original=True)
    
    print("=== YOLO v2 模型测试开始 ===")
    
    # 1. 基础测试
    print("\n1. 执行基础测试...")
    basic_results = tester.run_all_tests()
    
    # 2. 对比测试
    print("\n2. 执行对比测试...")
    comparison_results = tester.run_comparison_test()
    
    print("\n=== 测试完成 ===")
    print(f"所有结果保存在: {tester.output_dir}")
    print("包含文件:")
    print("  - 基础测试结果 JSON")
    print("  - 对比测试结果 JSON") 
    print("  - 统计摘要报告 JSON")
    print("  - 可视化图像文件夹")