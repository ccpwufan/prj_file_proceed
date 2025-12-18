#!/usr/bin/env python
"""
训练后的YOLO模型测试脚本
"""
import cv2
import json
from ultralytics import YOLO
from datetime import datetime

class TrainedYoloTester:
    def __init__(self, model_path):
        """加载训练好的模型"""
        self.model = YOLO(model_path)
        self.test_images = [
            '/app/media/detection_frames/snapshot_71_1765980946.jpg',
            '/app/media/detection_frames/complex_test_barcode.jpg'
        ]
    
    def test_single_image(self, image_path):
        """测试单张图像"""
        image = cv2.imread(image_path)
        if image is None:
            return {'error': f'Cannot load image: {image_path}'}
        
        # 运行检测
        results = self.model(image)
        
        # 解析结果
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    detections.append({
                        'class': class_name,
                        'confidence': float(confidence),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                    })
        
        return {
            'image_path': image_path,
            'detections': detections,
            'detection_count': len(detections)
        }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始测试训练后的YOLO模型...")
        results = []
        
        for image_path in self.test_images:
            result = self.test_single_image(image_path)
            results.append(result)
            print(f"测试完成: {image_path}")
            print(f"检测结果: {len(result.get('detections', []))} 个对象")
        
        # 保存测试结果
        output_file = f'trained_yolo_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"测试结果已保存到: {output_file}")
        return results

if __name__ == "__main__":
    # 使用训练好的模型路径
    tester = TrainedYoloTester('barcode_training/barcode_detector_v1/weights/best.pt')
    tester.run_all_tests()