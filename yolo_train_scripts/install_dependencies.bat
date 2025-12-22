@echo off
echo 正在安装4060ti YOLO训练所需依赖...
echo.

echo 1. 安装ultralytics...
pip install ultralytics -i https://pypi.douban.com/simple/
if %ERRORLEVEL% NEQ 0 (
    echo 尝试备用源...
    pip install ultralytics -i https://mirrors.aliyun.com/pypi/simple/
)
echo.

echo 2. 安装OpenCV...
pip install opencv-python -i https://pypi.douban.com/simple/
if %ERRORLEVEL% NEQ 0 (
    echo 尝试备用源...
    pip install opencv-python -i https://mirrors.aliyun.com/pypi/simple/
)
echo.

echo 3. 安装psutil...
pip install psutil -i https://pypi.douban.com/simple/
if %ERRORLEVEL% NEQ 0 (
    echo 尝试备用源...
    pip install psutil -i https://mirrors.aliyun.com/pypi/simple/
)
echo.

echo 4. 验证安装...
python -c "
try:
    import ultralytics
    print('✓ Ultralytics安装成功')
except ImportError:
    print('✗ Ultralytics安装失败')

try:
    import cv2
    print('✓ OpenCV安装成功')
except ImportError:
    print('✗ OpenCV安装失败')

try:
    import psutil
    print('✓ psutil安装成功')
except ImportError:
    print('✗ psutil安装失败')
"
echo.

echo 依赖安装完成！
pause