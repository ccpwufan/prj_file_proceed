@echo off
echo 正在检查4060ti YOLO训练环境...
echo.

echo 1. 检查Python版本...
python --version
echo.

echo 2. 检查PyTorch...
python -c "import torch; print('PyTorch版本:', torch.__version__); print('CUDA可用:', torch.cuda.is_available())"
echo.

echo 3. 检查GPU信息...
python -c "import torch; print('GPU名称:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '无'); print('显存总量:', round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1), 'GB' if torch.cuda.is_available() else '')"
echo.

echo 4. 检查训练依赖...
python -c "try:
    import ultralytics
    print('✓ Ultralytics已安装')
except ImportError:
    print('✗ Ultralytics未安装')

try:
    import cv2
    print('✓ OpenCV已安装')
except ImportError:
    print('✗ OpenCV未安装')

try:
    import psutil
    print('✓ psutil已安装')
except ImportError:
    print('✗ psutil未安装')"
echo.

echo 5. 检查数据集...
if exist "barcode_dataset\dataset.yaml" (
    echo ✓ 数据集配置文件存在
) else (
    echo ✗ 数据集配置文件不存在
)

echo 6. 统计数据集文件数量...
python -c "
import os
train_images = len([f for f in os.listdir('barcode_dataset/images/train') if f.endswith('.jpg')])
val_images = len([f for f in os.listdir('barcode_dataset/images/val') if f.endswith('.jpg')])
test_images = len([f for f in os.listdir('barcode_dataset/images/test') if f.endswith('.jpg')])
train_labels = len([f for f in os.listdir('barcode_dataset/labels/train') if f.endswith('.txt')])
val_labels = len([f for f in os.listdir('barcode_dataset/labels/val') if f.endswith('.txt')])
test_labels = len([f for f in os.listdir('barcode_dataset/labels/test') if f.endswith('.txt')])
print(f'训练集: {train_images} 张图像, {train_labels} 个标注')
print(f'验证集: {val_images} 张图像, {val_labels} 个标注')  
print(f'测试集: {test_images} 张图像, {test_labels} 个标注')
print(f'总计: {train_images + val_images + test_images} 张图像')
"
echo.

echo 环境检查完成！
pause