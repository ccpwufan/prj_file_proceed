#!/usr/bin/env python
"""
检查4060ti YOLO训练环境
"""
import sys
import os

def check_environment():
    print("="*60)
    print("4060ti YOLO训练环境检查")
    print("="*60)
    
    print("\n1. 检查Python版本...")
    print(f"Python版本: {sys.version}")
    
    print("\n2. 检查PyTorch...")
    try:
        import torch
        print(f"✓ PyTorch版本: {torch.__version__}")
        print(f"✓ CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✓ GPU名称: {torch.cuda.get_device_name(0)}")
            print(f"✓ 显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    except ImportError as e:
        print(f"✗ PyTorch未安装: {e}")
        return False
    
    print("\n3. 检查训练依赖...")
    deps = {
        'ultralytics': 'YOLO训练库',
        'cv2': 'OpenCV图像处理',
        'psutil': '系统监控'
    }
    
    for dep, desc in deps.items():
        try:
            __import__(dep)
            print(f"✓ {desc}已安装")
        except ImportError:
            print(f"✗ {desc}未安装")
            return False
    
    print("\n4. 检查数据集...")
    dataset_path = "barcode_dataset"
    if not os.path.exists(f"{dataset_path}/dataset.yaml"):
        print(f"✗ 数据集配置文件不存在")
        return False
    else:
        print(f"✓ 数据集配置文件存在")
    
    # 统计数据集文件
    try:
        train_images = len([f for f in os.listdir(f"{dataset_path}/images/train") if f.endswith('.jpg')])
        val_images = len([f for f in os.listdir(f"{dataset_path}/images/val") if f.endswith('.jpg')])
        test_images = len([f for f in os.listdir(f"{dataset_path}/images/test") if f.endswith('.jpg')])
        train_labels = len([f for f in os.listdir(f"{dataset_path}/labels/train") if f.endswith('.txt')])
        val_labels = len([f for f in os.listdir(f"{dataset_path}/labels/val") if f.endswith('.txt')])
        test_labels = len([f for f in os.listdir(f"{dataset_path}/labels/test") if f.endswith('.txt')])
        
        print(f"✓ 训练集: {train_images} 张图像, {train_labels} 个标注")
        print(f"✓ 验证集: {val_images} 张图像, {val_labels} 个标注")  
        print(f"✓ 测试集: {test_images} 张图像, {test_labels} 个标注")
        
        total_images = train_images + val_images + test_images
        total_labels = train_labels + val_labels + test_labels
        
        if total_images != total_labels:
            print(f"⚠ 图像数量({total_images})与标注数量({total_labels})不匹配")
        
        if total_images < 10:
            print("⚠ 数据集较小，可能影响训练效果")
        
    except Exception as e:
        print(f"✗ 检查数据集时出错: {e}")
        return False
    
    print("\n" + "="*60)
    print("环境检查完成！")
    print("="*60)
    return True

if __name__ == "__main__":
    if check_environment():
        print("\n🎉 环境检查通过，可以开始训练！")
        print("运行训练命令: python train_barcode_yolo_4060ti.py")
    else:
        print("\n❌ 环境检查失败，请安装缺失的依赖")
        print("运行安装命令: pip install ultralytics opencv-python psutil")