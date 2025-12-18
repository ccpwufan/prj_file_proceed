#!/usr/bin/env python3
"""
数据集分割脚本 - 将标注好的数据分割为训练/验证/测试集
"""
import os
import shutil
import random
from pathlib import Path
import argparse

def split_dataset(source_dir, labels_dir, output_dir, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1):
    """
    分割数据集
    Args:
        source_dir: 原始图像目录
        labels_dir: 标注文件目录
        output_dir: 输出目录
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
    """
    # 检查比例总和
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.001:
        raise ValueError("训练、验证、测试比例之和必须等于1.0")
    
    # 创建输出目录
    images_dir = Path(output_dir) / "images"
    labels_out_dir = Path(output_dir) / "labels"
    
    for split in ['train', 'val', 'test']:
        (images_dir / split).mkdir(parents=True, exist_ok=True)
        (labels_out_dir / split).mkdir(parents=True, exist_ok=True)
    
    # 获取所有图像文件
    image_files = []
    source_path = Path(source_dir)
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
        image_files.extend(source_path.glob(ext))
    
    print(f"找到 {len(image_files)} 张图像")
    
    # 随机打乱
    random.shuffle(image_files)
    
    # 计算分割点
    total = len(image_files)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    test_count = total - train_count - val_count
    
    print(f"分割比例 - 训练: {train_count}, 验证: {val_count}, 测试: {test_count}")
    
    # 分割数据
    splits = {
        'train': image_files[:train_count],
        'val': image_files[train_count:train_count + val_count],
        'test': image_files[train_count + val_count:]
    }
    
    # 复制文件
    for split_name, files in splits.items():
        print(f"处理 {split_name} 集合...")
        
        for img_file in files:
            # 复制图像
            img_dest = images_dir / split_name / img_file.name
            shutil.copy2(img_file, img_dest)
            
            # 复制对应的标注文件
            label_file = Path(labels_dir) / f"{img_file.stem}.txt"
            if label_file.exists():
                label_dest = labels_out_dir / split_name / f"{img_file.stem}.txt"
                shutil.copy2(label_file, label_dest)
            else:
                print(f"警告: 找不到标注文件 {label_file}")
    
    print("数据集分割完成!")
    print(f"输出目录: {output_dir}")

def create_dataset_yaml(output_dir):
    """创建dataset.yaml配置文件"""
    yaml_content = f"""path: /app/barcode_dataset
train: images/train
val: images/val
test: images/test

nc: 3
names:
  0: barcode
  1: datamatrix
  2: qrcode
"""
    
    yaml_file = Path(output_dir) / "dataset.yaml"
    with open(yaml_file, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    
    print(f"已创建配置文件: {yaml_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='分割数据集')
    parser.add_argument('--source', required=True, help='原始图像目录')
    parser.add_argument('--labels', required=True, help='标注文件目录')
    parser.add_argument('--output', required=True, help='输出目录')
    parser.add_argument('--train-ratio', type=float, default=0.8, help='训练集比例')
    parser.add_argument('--val-ratio', type=float, default=0.1, help='验证集比例')
    parser.add_argument('--test-ratio', type=float, default=0.1, help='测试集比例')
    
    args = parser.parse_args()
    
    split_dataset(
        args.source,
        args.labels,
        args.output,
        args.train_ratio,
        args.val_ratio,
        args.test_ratio
    )
    
    create_dataset_yaml(args.output)