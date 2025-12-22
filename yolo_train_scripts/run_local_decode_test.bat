@echo off
echo ========================================
echo 本地YOLO + 条码解码测试工具
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python未安装或未添加到PATH
    echo 请先安装Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install required packages if needed
echo 🔧 检查依赖包...
pip show ultralytics >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装ultralytics...
    pip install ultralytics
)

pip show opencv-python >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装opencv-python...
    pip install opencv-python
)

REM Install optional decoders
pip show pyzbar >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ pyzbar未安装，安装命令: pip install pyzbar
    echo Windows可能需要额外安装支持库
)

pip show pyzxing >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ pyzxing未安装，安装命令: pip install pyzxing
)

echo.
echo 🚀 开始运行测试...
echo.

REM Run the test script
python yolo_train_scripts\test_yolo_decode_local.py

echo.
echo 测试完成！查看当前目录下的JSON结果文件。
pause