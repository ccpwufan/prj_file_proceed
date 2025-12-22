#!/usr/bin/env python
"""
4060ti训练模型性能基准测试
排除初始化影响，测量纯推理性能
"""
import cv2
import time
import torch
from ultralytics import YOLO

def benchmark_model(model_path, test_image_path=None, warmup_runs=5, test_runs=50):
    """
    基准测试模型性能
    
    Args:
        model_path: 模型路径
        test_image_path: 测试图像路径
        warmup_runs: 预热运行次数
        test_runs: 测试运行次数
    """
    print("=== 4060ti训练模型基准测试 ===")
    
    # 加载模型
    print(f"加载模型: {model_path}")
    model = YOLO(model_path)
    
    # 准备测试图像
    if test_image_path is None:
        # 使用第一张找到的测试图像
        import glob
        test_images = glob.glob('media/detection_frames/*.jpg')[:1]
        if not test_images:
            print("❌ 找不到测试图像")
            return
        test_image_path = test_images[0]
    
    print(f"使用测试图像: {test_image_path}")
    image = cv2.imread(test_image_path)
    
    if image is None:
        print(f"❌ 无法加载图像: {test_image_path}")
        return
    
    print(f"图像尺寸: {image.shape}")
    
    # GPU信息
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    print(f"\n预热运行 {warmup_runs} 次...")
    
    # 预热运行
    for i in range(warmup_runs):
        _ = model(image, conf=0.25)
        print(f"  预热 {i+1}/{warmup_runs} 完成")
    
    print(f"\n开始性能测试 {test_runs} 次...")
    
    # 性能测试
    inference_times = []
    detection_counts = []
    
    for i in range(test_runs):
        start_time = time.time()
        results = model(image, conf=0.25)
        end_time = time.time()
        
        inference_time = (end_time - start_time) * 1000  # ms
        inference_times.append(inference_time)
        
        detection_count = len(results[0].boxes) if results[0].boxes else 0
        detection_counts.append(detection_count)
        
        if (i + 1) % 10 == 0:
            print(f"  完成 {i+1}/{test_runs} 次")
    
    # 统计分析
    avg_time = sum(inference_times) / len(inference_times)
    min_time = min(inference_times)
    max_time = max(inference_times)
    median_time = sorted(inference_times)[len(inference_times)//2]
    
    avg_fps = 1000 / avg_time
    max_fps = 1000 / min_time
    
    # 检测稳定性
    consistent_detections = len(set(detection_counts)) == 1
    
    print(f"\n📊 性能基准测试结果:")
    print(f"🚀 推理性能:")
    print(f"  平均时间: {avg_time:.2f}ms")
    print(f"  最快时间: {min_time:.2f}ms ({max_fps:.1f} FPS)")
    print(f"  最慢时间: {max_time:.2f}ms ({1000/max_time:.1f} FPS)")
    print(f"  中位数时间: {median_time:.2f}ms ({1000/median_time:.1f} FPS)")
    print(f"  平均FPS: {avg_fps:.1f}")
    
    print(f"\n🎯 检测稳定性:")
    print(f"  检测数量范围: {min(detection_counts)} - {max(detection_counts)}")
    print(f"  检测一致性: {'✅ 稳定' if consistent_detections else '⚠️ 不稳定'}")
    print(f"  平均检测数: {sum(detection_counts)/len(detection_counts):.1f}")
    
    # 性能评级
    if avg_fps >= 60:
        grade = "A+ (优秀)"
        comment = "适用于实时高帧率应用"
    elif avg_fps >= 30:
        grade = "A (良好)"
        comment = "适用于实时应用"
    elif avg_fps >= 20:
        grade = "B (一般)"
        comment = "适用于非实时应用"
    else:
        grade = "C (需优化)"
        comment = "建议优化模型或使用更强硬件"
    
    print(f"\n🏆 性能评级: {grade}")
    print(f"💡 建议: {comment}")
    
    # GPU内存使用
    if torch.cuda.is_available():
        memory_used = torch.cuda.memory_allocated() / 1024**3
        memory_cached = torch.cuda.memory_reserved() / 1024**3
        print(f"\n💾 GPU内存使用:")
        print(f"  已分配: {memory_used:.2f} GB")
        print(f"  已缓存: {memory_cached:.2f} GB")
    
    return {
        'avg_time_ms': avg_time,
        'min_time_ms': min_time,
        'max_time_ms': max_time,
        'median_time_ms': median_time,
        'avg_fps': avg_fps,
        'max_fps': max_fps,
        'detection_stats': {
            'min': min(detection_counts),
            'max': max(detection_counts),
            'avg': sum(detection_counts)/len(detection_counts),
            'consistent': consistent_detections
        }
    }

def compare_with_original(model_path):
    """与原始YOLOv8n对比"""
    print(f"\n=== 与原始YOLOv8n对比测试 ===")
    
    # 准备测试图像
    import glob
    test_images = glob.glob('media/detection_frames/*.jpg')[:3]  # 测试3张图像
    
    if not test_images:
        print("❌ 找不到测试图像")
        return
    
    print(f"测试图像数量: {len(test_images)}")
    
    # 加载模型
    original_model = YOLO('yolov8n.pt')
    trained_model = YOLO(model_path)
    
    original_stats = []
    trained_stats = []
    
    for i, image_path in enumerate(test_images):
        print(f"\n测试图像 {i+1}: {image_path}")
        image = cv2.imread(image_path)
        
        # 预热
        _ = original_model(image, conf=0.25)
        _ = trained_model(image, conf=0.25)
        
        # 测试原始模型
        times = []
        for _ in range(10):
            start = time.time()
            results = original_model(image, conf=0.25)
            end = time.time()
            times.append((end - start) * 1000)
        
        original_avg = sum(times) / len(times)
        original_detections = len(results[0].boxes) if results[0].boxes else 0
        original_stats.append((original_avg, original_detections))
        
        # 测试训练模型
        times = []
        for _ in range(10):
            start = time.time()
            results = trained_model(image, conf=0.25)
            end = time.time()
            times.append((end - start) * 1000)
        
        trained_avg = sum(times) / len(times)
        trained_detections = len(results[0].boxes) if results[0].boxes else 0
        trained_stats.append((trained_avg, trained_detections))
        
        print(f"  原始模型: {original_avg:.1f}ms, {original_detections}个检测")
        print(f"  训练模型: {trained_avg:.1f}ms, {trained_detections}个检测")
    
    # 计算平均提升
    original_time_avg = sum(s[0] for s in original_stats) / len(original_stats)
    trained_time_avg = sum(s[0] for s in trained_stats) / len(trained_stats)
    original_det_avg = sum(s[1] for s in original_stats) / len(original_stats)
    trained_det_avg = sum(s[1] for s in trained_stats) / len(trained_stats)
    
    time_improvement = ((original_time_avg - trained_time_avg) / original_time_avg) * 100
    detection_improvement = ((trained_det_avg - original_det_avg) / max(original_det_avg, 1)) * 100
    
    print(f"\n📊 对比总结:")
    print(f"原始YOLOv8n:")
    print(f"  平均推理时间: {original_time_avg:.1f}ms")
    print(f"  平均检测数量: {original_det_avg:.1f}")
    
    print(f"\n4060ti训练模型:")
    print(f"  平均推理时间: {trained_time_avg:.1f}ms")
    print(f"  平均检测数量: {trained_det_avg:.1f}")
    
    print(f"\n🚀 性能提升:")
    print(f"  推理速度: {time_improvement:+.1f}%")
    print(f"  检测精度: {detection_improvement:+.1f}%")

def main():
    """主函数"""
    model_path = 'barcode_training/barcode_detector_4060ti/weights/best.pt'
    
    # 检查模型是否存在
    import os
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return
    
    # 基准测试
    results = benchmark_model(model_path)
    
    # 对比测试
    compare_with_original(model_path)
    
    # 总结建议
    print(f"\n{'='*60}")
    if results and results['avg_fps'] >= 30:
        print("🎉 4060ti训练模型性能优秀，适合生产环境!")
        print("✅ 建议: 可以直接集成到现有系统")
    elif results and results['avg_fps'] >= 20:
        print("⚠️ 4060ti训练模型性能良好，可用于生产环境")
        print("💡 建议: 考虑进一步优化或使用更强硬件")
    else:
        print("⚠️ 4060ti训练模型性能需要优化")
        print("🔧 建议: 减小输入尺寸、量化模型或使用更强硬件")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()