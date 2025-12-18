# 条码数据标注指南

## 标注类别
1. **barcode** - 传统条码（CODE128, EAN13, UPC-A等一维条码）
2. **datamatrix** - Data Matrix二维码（方形点阵）
3. **qrcode** - QR码（正方形二维码）

## 标注规范

### 识别要点
- **barcode**: 通常为矩形，由平行的黑白条纹组成
- **datamatrix**: 黑白点阵组成的正方形，边缘有定位框
- **qrcode**: 正方形，有明显的三个角部定位图案

### 标注要求
1. **准确框选**: 框要紧密包围条码，不要包含过多背景
2. **完整包含**: 确保条码完全在框内
3. **避免重叠**: 多个条码不要框在一起，分别标注

### 使用LabelImg

#### 启动标注工具
```bash
labelImg raw_images/ classes.txt
```

#### 快捷键
- **W** - 创建矩形框
- **D** - 下一张图像
- **A** - 上一张图像
- **Ctrl+S** - 保存标注
- **Space** - 标记为完成

#### 标注步骤
1. 打开LabelImg，选择YOLO格式
2. 使用W键创建矩形框
3. 选择正确的类别
4. 调整框选区域
5. 保存（Ctrl+S）
6. 下一张图像（D键）

#### 输出格式
标注文件自动保存为YOLO格式：
```
<class_id> <x_center> <y_center> <width> <height>
```

## 质量检查
- 每标注10张图像，回查一遍质量
- 确保类别选择正确
- 检查框选是否准确

## 完成后的文件结构
```
local_annotation/
├── raw_images/          # 原始图像
├── labels/             # YOLO格式标注文件
├── classes.txt         # 类别定义
├── dataset/            # 分割后的数据集
└── split_dataset.py    # 数据集分割脚本
```

## 数据集分割
标注完成后，运行：
```bash
python split_dataset.py --source ./raw_images --labels ./labels --output ./dataset
```