#!/usr/bin/env python
"""
YOLO条码检测模型训练脚本
在Docker容器中运行此脚本
"""
from ultralytics import YOLO
import os
import torch

def train_barcode_model():
    """训练条码检测模型"""
    
    # 训练配置 - 优化版本
    config = {
        'model': 'yolov8n.pt',          # 使用nano版本，速度快
        'data': '/app/barcode_dataset/dataset.yaml',
        'epochs': 50,                    # 减少到50轮，加快训练
        'batch_size': 4,                # 减少到4，防止内存溢出
        'img_size': 640,                # 图像尺寸
        'device': 'cpu',                # 使用CPU训练（Docker环境）
        'name': 'barcode_detector_v2',  # 使用新名称避免冲突
        'project': 'barcode_training',   # 项目名称
        'save_period': 5,               # 每5轮保存一次
        'patience': 50,                 # 增加耐心值，防止过早停止
        'verbose': True,
        'plots': True,                  # 生成训练图表
        'save_json': True,              # 保存JSON结果
        'exist_ok': True,               # 允许覆盖现有项目
        'workers': 2,                   # 减少数据加载线程数
        'cache': False,                 # 禁用缓存减少内存使用
        'optimizer': 'AdamW',           # 使用AdamW优化器
        'lr0': 0.001,                   # 降低学习率
        'val_conf': 0.25,               # 降低验证置信度阈值
        'rect': False,                  # 禁用矩形训练
        'cos_lr': True,                 # 使用余弦学习率调度
        'close_mosaic': 5               # 最后5轮关闭mosaic增强
    }
    
    print("开始训练条码检测模型...")
    print(f"训练配置: {config}")
    
    # 检查数据集文件是否存在
    if not os.path.exists(config['data']):
        print(f"错误: 数据集配置文件不存在: {config['data']}")
        return None
    
    # 加载预训练模型
    print(f"加载预训练模型: {config['model']}")
    model = YOLO(config['model'])
    
    try:
        # 开始训练
        print("开始训练...")
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
            exist_ok=config['exist_ok']
        )
        
        print("训练完成!")
        print(f"最佳模型保存在: {config['project']}/{config['name']}/weights/best.pt")
        
        return results
        
    except Exception as e:
        print(f"训练过程中发生错误: {e}")
        return None

def validate_model(model_path, data_path):
    """验证模型性能"""
    print(f"验证模型: {model_path}")
    
    try:
        model = YOLO(model_path)
        metrics = model.val(data=data_path)
        
        print("验证结果:")
        print(f"mAP50: {metrics.box.map50:.4f}")
        print(f"mAP50-95: {metrics.box.map:.4f}")
        print(f"精度: {metrics.box.mp:.4f}")
        print(f"召回率: {metrics.box.mr:.4f}")
        
        return metrics
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        return None

if __name__ == "__main__":
    # 训练模型
    results = train_barcode_model()
    
    if results:
        # 验证最佳模型
        best_model_path = 'barcode_training/barcode_detector_v2/weights/best.pt'
        data_path = '/app/barcode_dataset/dataset.yaml'
        
        metrics = validate_model(best_model_path, data_path)
        
        if metrics:
            print("训练和验证完成!")
        else:
            print("训练完成，但验证失败!")
    else:
        print("训练失败!")