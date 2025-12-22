#!/usr/bin/env python
"""
YOLO条码检测模型GPU训练脚本 - 针对4060ti显卡优化
充分利用4060ti的8GB显存和CUDA加速能力
"""
from ultralytics import YOLO
import os
import torch
import time
import psutil
from datetime import datetime

def check_gpu_environment():
    """检查GPU环境和系统资源"""
    print("=== 系统环境检查 ===")
    
    # 检查CUDA可用性
    if torch.cuda.is_available():
        print(f"✓ CUDA可用: {torch.cuda.is_available()}")
        print(f"✓ GPU设备: {torch.cuda.get_device_name(0)}")
        print(f"✓ 显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        print(f"✓ CUDA版本: {torch.version.cuda}")
        print(f"✓ PyTorch版本: {torch.__version__}")
        return True
    else:
        print("✗ CUDA不可用，将使用CPU训练")
        return False

def get_optimal_batch_size():
    """根据4060ti显存动态计算最优批次大小"""
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        # 4060ti有8GB显存，保守估计使用70%显存用于训练
        usable_memory = gpu_memory * 0.7
        
        # 根据经验公式：每GB显存可以处理约2-3个样本（1024x1024）
        if usable_memory >= 5.6:
            return 16
        elif usable_memory >= 4.0:
            return 12
        elif usable_memory >= 3.0:
            return 8
        else:
            return 4
    else:
        return 4  # CPU训练使用小批次

def train_barcode_model_gpu():
    """使用GPU训练条码检测模型 - 4060ti优化版"""
    
    # 环境检查
    gpu_available = check_gpu_environment()
    device = '0' if gpu_available else 'cpu'
    
    # 计算最优批次大小
    optimal_batch_size = get_optimal_batch_size()
    
    print(f"\n=== 训练配置 ===")
    print(f"使用设备: {device}")
    print(f"最优批次大小: {optimal_batch_size}")
    
    # 训练配置 - 针对4060ti优化
    config = {
        'model': 'yolov8n.pt',                    # 使用nano版本，平衡速度和精度
        'data': 'barcode_dataset/dataset.yaml',   # 本地相对路径
        'epochs': 50,                              # 减少轮次以降低内存压力
        'batch_size': 4,                           # 固定小批次避免内存问题
        'img_size': 640,                           # 减小图像尺寸降低内存使用
        'device': device,                          # 使用GPU
        'name': 'barcode_detector_4060ti',        # 新名称避免冲突
        'project': 'barcode_training',            # 项目名称
        'save_period': 10,                        # 每10轮保存一次
        'patience': 30,                           # 早停耐心值
        'verbose': True,
        'plots': True,                           # 生成训练图表
        'save_json': True,                       # 保存JSON结果
        'exist_ok': True,                        # 允许覆盖现有项目
        'workers': 2,                            # 减少线程数降低内存使用
        'cache': False,                          # 禁用缓存减少内存压力
        'optimizer': 'AdamW',                    # 使用AdamW优化器
        'lr0': 0.001,                            # 初始学习率
        'conf': 0.25,                           # 验证置信度阈值
        'rect': False,                           # 禁用矩形训练
        'cos_lr': True,                          # 使用余弦学习率调度
        'close_mosaic': 10,                      # 最后10轮关闭mosaic增强
        'amp': False,                            # 禁用混合精度减少内存问题
        'multi_scale': False,                     # 禁用多尺度训练降低内存
        'fraction': 1.0,                        # 使用全部数据
        'profile': True,                         # 分析训练性能
        'freeze': None,                          # 不冻结层
        'warmup_epochs': 3.0,                    # 预热轮次
        'warmup_momentum': 0.8,                  # 预热动量
        'warmup_bias_lr': 0.1,                   # 预热偏置学习率
        'box': 7.5,                              # 框损失权重
        'cls': 0.5,                              # 类别损失权重
        'dfl': 1.5,                              # 分布焦点损失权重
        # 数据增强参数
        'hsv_h': 0.015,                          # 色调增强
        'hsv_s': 0.7,                            # 饱和度增强
        'hsv_v': 0.4,                            # 明度增强
        'degrees': 0.0,                          # 旋转角度（条码通常不需要旋转）
        'translate': 0.1,                         # 平移
        'scale': 0.5,                            # 缩放
        'shear': 0.0,                            # 剪切
        'perspective': 0.0,                      # 透视
        'flipud': 0.0,                           # 上下翻转概率
        'fliplr': 0.5,                           # 左右翻转概率
        'mosaic': 1.0,                           # Mosaic增强
        'mixup': 0.0,                            # MixUp增强
        'copy_paste': 0.0,                       # 复制粘贴增强
    }
    
    print(f"训练配置参数: {config}")
    
    # 检查数据集文件是否存在
    if not os.path.exists(config['data']):
        print(f"错误: 数据集配置文件不存在: {config['data']}")
        print("请确保barcode_dataset/dataset.yaml文件存在且配置正确")
        return None
    
    # 检查预训练模型文件
    if not os.path.exists(config['model']):
        print(f"预训练模型不存在: {config['model']}")
        print("将自动下载预训练模型...")
    
    # 显示训练前的内存和显存状态
    if gpu_available:
        torch.cuda.empty_cache()
        print(f"训练前显存使用: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
    
    print(f"开始GPU训练条码检测模型...")
    print(f"预计训练时间: 2-3小时（100轮）")
    
    # 记录训练开始时间
    start_time = time.time()
    
    try:
        # 加载预训练模型
        print(f"加载预训练模型: {config['model']}")
        model = YOLO(config['model'])
        
        # 开始训练
        print("开始GPU训练...")
        results = model.train(
            data=config['data'],
            epochs=config['epochs'],
            batch=config['batch_size'],
            imgsz=config['img_size'],
            device=config['device'],
            name=config['name'],
            project=config['project'],
            save_period=config['save_period'],
            patience=config['patience'],
            verbose=config['verbose'],
            plots=config['plots'],
            save_json=config['save_json'],
            exist_ok=config['exist_ok'],
            workers=config['workers'],
            cache=config['cache'],
            optimizer=config['optimizer'],
            lr0=config['lr0'],
            conf=config['conf'],
            rect=config['rect'],
            cos_lr=config['cos_lr'],
            close_mosaic=config['close_mosaic'],
            amp=config['amp'],
            multi_scale=config['multi_scale'],
            fraction=config['fraction'],
            profile=config['profile'],
            freeze=config['freeze'],
            warmup_epochs=config['warmup_epochs'],
            warmup_momentum=config['warmup_momentum'],
            warmup_bias_lr=config['warmup_bias_lr'],
            box=config['box'],
            cls=config['cls'],
            dfl=config['dfl'],
            hsv_h=config['hsv_h'],
            hsv_s=config['hsv_s'],
            hsv_v=config['hsv_v'],
            degrees=config['degrees'],
            translate=config['translate'],
            scale=config['scale'],
            shear=config['shear'],
            perspective=config['perspective'],
            flipud=config['flipud'],
            fliplr=config['fliplr'],
            mosaic=config['mosaic'],
            mixup=config['mixup'],
            copy_paste=config['copy_paste'],
        )
        
        # 计算训练时间
        end_time = time.time()
        training_time = end_time - start_time
        
        print("\n" + "="*50)
        print("训练完成!")
        print(f"训练用时: {training_time/3600:.2f} 小时")
        print(f"最佳模型保存在: {config['project']}/{config['name']}/weights/best.pt")
        print(f"最终模型保存在: {config['project']}/{config['name']}/weights/last.pt")
        
        # 显示训练后的内存状态
        if gpu_available:
            print(f"训练后显存使用: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        
        return results
        
    except Exception as e:
        print(f"训练过程中发生错误: {e}")
        print("可能的原因:")
        print("1. 显存不足 - 尝试减小批次大小")
        print("2. 数据集路径错误 - 检查dataset.yaml配置")
        print("3. CUDA驱动问题 - 检查GPU驱动是否正确安装")
        return None
    finally:
        # 清理显存
        if gpu_available:
            torch.cuda.empty_cache()

def validate_model(model_path, data_path, device='0'):
    """验证模型性能"""
    print(f"\n=== 模型验证 ===")
    print(f"验证模型: {model_path}")
    print(f"数据集: {data_path}")
    
    try:
        model = YOLO(model_path)
        
        # 运行验证
        print("开始验证...")
        metrics = model.val(data=data_path, device=device)
        
        print("\n验证结果:")
        print(f"mAP50: {metrics.box.map50:.4f}")
        print(f"mAP50-95: {metrics.box.map:.4f}")
        print(f"精度: {metrics.box.mp:.4f}")
        print(f"召回率: {metrics.box.mr:.4f}")
        
        # 性能评估
        if metrics.box.map50 >= 0.9:
            print("✓ 模型性能优秀 (mAP50 >= 0.9)")
        elif metrics.box.map50 >= 0.8:
            print("✓ 模型性能良好 (mAP50 >= 0.8)")
        elif metrics.box.map50 >= 0.7:
            print("△ 模型性能一般 (mAP50 >= 0.7)")
        else:
            print("✗ 模型性能较差 (mAP50 < 0.7)")
        
        return metrics
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        return None

def test_model_inference_speed(model_path, test_image_count=10):
    """测试模型推理速度"""
    print(f"\n=== 推理速度测试 ===")
    
    try:
        import cv2
        import numpy as np
        
        model = YOLO(model_path)
        
        # 创建测试图像
        test_images = []
        for i in range(test_image_count):
            # 生成随机测试图像 (1024x1024)
            test_img = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8)
            test_images.append(test_img)
        
        # 预热GPU
        if torch.cuda.is_available():
            _ = model(test_images[0], device='0')
        
        # 测试推理速度
        start_time = time.time()
        for img in test_images:
            _ = model(img, device='0')
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / test_image_count
        fps = 1 / avg_time
        
        print(f"测试图像数量: {test_image_count}")
        print(f"总推理时间: {total_time:.2f} 秒")
        print(f"平均推理时间: {avg_time*1000:.2f} 毫秒")
        print(f"推理速度: {fps:.2f} FPS")
        
        return {
            'total_time': total_time,
            'avg_time_ms': avg_time * 1000,
            'fps': fps
        }
        
    except Exception as e:
        print(f"速度测试失败: {e}")
        return None

if __name__ == "__main__":
    print("YOLO条码检测GPU训练脚本 - 4060ti优化版")
    print("="*60)
    
    # 训练模型
    results = train_barcode_model_gpu()
    
    if results:
        # 验证最佳模型
        best_model_path = 'barcode_training/barcode_detector_4060ti/weights/best.pt'
        data_path = 'barcode_dataset/dataset.yaml'
        device = '0' if torch.cuda.is_available() else 'cpu'
        
        # 运行验证
        metrics = validate_model(best_model_path, data_path, device)
        
        # 测试推理速度
        speed_results = test_model_inference_speed(best_model_path)
        
        if metrics and speed_results:
            print("\n" + "="*60)
            print("🎉 训练和测试全部完成!")
            print(f"✓ 模型性能: mAP50-95 = {metrics.box.map:.4f}")
            print(f"✓ 推理速度: {speed_results['fps']:.2f} FPS")
            print(f"✓ 模型路径: {best_model_path}")
            print("="*60)
        else:
            print("\n⚠️ 训练完成，但验证或速度测试失败")
    else:
        print("\n❌ 训练失败!")
        print("请检查:")
        print("1. GPU环境配置")
        print("2. 数据集路径")
        print("3. 依赖库安装")