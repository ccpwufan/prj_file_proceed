# YOLO条码检测训练测试方案

## 目标
通过专门训练的YOLO模型来准确检测图像中的条码（包括Data Matrix和传统条码），然后集成到现有系统中。

## 方案概述

### 训练流程：
1. **数据集准备** - 收集和标注条码图像
2. **环境配置** - 安装训练依赖
3. **模型训练** - 使用YOLOv8训练专门模型
4. **独立测试** - 使用单独的Python脚本测试
5. **效果验证** - 对比训练前后的检测效果
6. **系统集成** - 将训练好的模型集成到生产代码

## 第一阶段：数据集准备

### 1.1 创建本地标注环境
```bash
# 在本地创建标注工作目录
mkdir -p ~/barcode_work/{images,labels,raw_data,tools}
cd ~/barcode_work

# 创建子目录结构
mkdir -p images/{train,val,test}
mkdir -p labels/{train,val,test}
mkdir -p raw_data/{screenshots,generated,synthetic}
```

### 1.2 收集训练数据
**数据来源：**
- **现有检测帧**: 从Docker容器复制 `media/detection_frames/`
- **合成条码图像**: 使用脚本生成各种条码
- **公开条码数据集**: 下载公开的条码检测数据集
- **实际场景拍摄**: 拍摄真实场景中的条码图像

```bash
# 从Docker复制现有图像
docker cp prj_file_proceed-web-1:/app/media/detection_frames ./raw_data/screenshots

# 生成合成条码图像
python generate_synthetic_barcodes.py --output ./raw_data/synthetic --count 100
```

### 1.3 本地数据标注（使用LabelImg）
**标注类别定义：**
- `barcode` - 传统条码（CODE128, EAN13, UPC-A等）
- `datamatrix` - Data Matrix码
- `qrcode` - QR码

**标注格式：** YOLO格式 (class_id x_center y_center width height)

**LabelImg标注流程：**
1. 启动LabelImg：`labelImg raw_data/ classes.txt`
2. 设置输出格式为YOLO
3. 使用快捷键快速标注
4. 保存标注文件到labels目录

### 1.3 数据集目标
- **训练集**: 200-500张图像
- **验证集**: 50-100张图像  
- **测试集**: 20-30张图像

## 第二阶段：环境配置（混合方案：本地标注 + Docker训练）

### 方案选择说明
**选择混合方案的理由：**
- **本地标注**：GUI响应更快，操作体验更好
- **Docker训练**：环境隔离，避免依赖冲突，训练可后台运行
- **数据管理**：统一的训练数据环境，便于版本控制

### 2.1 本地安装LabelImg标注工具
```bash
# 本地标注环境安装

# 1. 安装Python依赖（如果还没有安装）
pip install pyqt5 lxml

# 2. 安装LabelImg
pip install labelImg

# 3. 或者从源码安装（推荐）
git clone https://github.com/tzutalin/labelImg.git
cd labelImg
pip install -r requirements/requirements.txt
python labelImg.py

# 4. 或者使用conda安装
conda install pyqt=5
conda install -c anaconda lxml
pip install labelImg
```

### 2.2 Docker训练环境配置
```bash
# 在Docker容器中安装训练依赖
docker exec prj_file_proceed-web-1 pip install ultralytics
docker exec prj_file_proceed-web-1 pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 验证安装
docker exec prj_file_proceed-web-1 python -c "from ultralytics import YOLO; print('YOLO installed successfully')"
```

### 2.3 数据流转方案
```bash
# 数据流转：本地 -> Docker -> 本地（结果）

# 1. 从Docker复制原始图像到本地进行标注
docker cp prj_file_proceed-web-1:/app/media/detection_frames ./local_annotation/raw_images

# 2. 本地标注完成后，上传到Docker进行训练
docker cp ./local_annotation/annotated_dataset prj_file_proceed-web-1:/app/barcode_dataset

# 3. 训练完成后，从Docker复制训练结果到本地
docker cp prj_file_proceed-web-1:/app/barcode_training ./local_training_results/
```

### 2.3 LabelImg标注工具使用指南

**启动方式：**
```bash
# 方式1：直接启动
labelImg

# 方式2：指定数据目录
labelImg [IMAGE_PATH] [PRE-DEFINED_CLASS_FILE]

# 方式3：从源码启动
python labelImg.py
```

**标注设置：**
1. **快捷键**：
   - `W` - 创建矩形框
   - `D` - 下一张图像
   - `A` - 上一张图像
   - `Ctrl+S` - 保存标注
   - `Space` - 标记为完成

2. **输出格式**：
   - 选择 `YOLO` 格式
   - 类别文件：`classes.txt`
   - 标注文件：`image_name.txt`

3. **标注类别配置**：
创建 `classes.txt` 文件：
```
barcode
datamatrix
qrcode
```

### 2.4 创建数据集配置文件
```yaml
# /app/barcode_dataset/dataset.yaml （Docker容器中的路径）
path: /app/barcode_dataset
train: images/train
val: images/val
test: images/test

nc: 3  # 类别数量
names:
  0: barcode
  1: datamatrix
  2: qrcode
```

### 2.5 混合方案工作流程

**步骤1：数据准备（Docker → 本地）**
```bash
# 1. 从Docker容器复制原始图像到本地标注目录
docker cp prj_file_proceed-web-1:/app/media/detection_frames ./local_annotation/raw_images

# 2. 创建本地标注目录结构
mkdir -p local_annotation/{raw_images,labels,dataset}
cd local_annotation

# 3. 创建类别定义文件
echo -e "barcode\ndatamatrix\nqrcode" > classes.txt
```

**步骤2：本地标注工作**
```bash
# 启动本地LabelImg进行标注
labelImg raw_images/ classes.txt

# 标注快捷键：
# W - 创建矩形框
# D - 下一张图像  
# A - 上一张图像
# Ctrl+S - 保存标注

# 标注完成后文件结构：
local_annotation/
├── raw_images/          # 原始图像
├── labels/             # YOLO格式标注文件（.txt）
├── classes.txt         # 类别定义
└── dataset/            # 整理后的数据集
```

**步骤3：数据集整理和上传（本地 → Docker）**
```bash
# 1. 整理标注数据为YOLO训练格式
mkdir -p dataset/{images,labels}/{train,val,test}

# 2. 按比例分割数据集（例如80%训练，10%验证，10%测试）
python split_dataset.py --source ./raw_images --labels ./labels --output ./dataset

# 3. 上传到Docker容器
docker cp ./local_annotation/dataset prj_file_proceed-web-1:/app/barcode_dataset

# 4. 在Docker中创建配置文件
docker exec prj_file_proceed-web-1 bash -c 'cat > /app/barcode_dataset/dataset.yaml << EOF
path: /app/barcode_dataset
train: images/train
val: images/val
test: images/test

nc: 3
names:
  0: barcode
  1: datamatrix
  2: qrcode
EOF'
```

## 第三阶段：模型训练

### 3.1 训练参数配置
```python
# 训练配置
TRAIN_CONFIG = {
    'model': 'yolov8n.pt',          # 使用nano版本，速度快
    'data': '/app/barcode_dataset/dataset.yaml',
    'epochs': 100,                   # 训练轮次
    'batch_size': 16,               # 批次大小
    'img_size': 640,                # 图像尺寸
    'device': 'cpu',                # 使用CPU训练（Docker环境）
    'name': 'barcode_detector_v1',  # 模型名称
    'project': 'barcode_training',   # 项目名称
    'save_period': 10,              # 每10轮保存一次
    'patience': 20,                 # 早停耐心值
}
```

### 3.2 训练脚本
创建 `train_barcode_yolo.py`：
```python
#!/usr/bin/env python
"""
YOLO条码检测模型训练脚本
"""
from ultralytics import YOLO
import os

def train_barcode_model():
    # 加载预训练模型
    model = YOLO('yolov8n.pt')
    
    # 开始训练
    results = model.train(
        data='/app/barcode_dataset/dataset.yaml',
        epochs=100,
        batch=16,
        imgsz=640,
        device='cpu',
        name='barcode_detector_v1',
        project='barcode_training',
        save_period=10,
        patience=20,
        verbose=True
    )
    
    return results

if __name__ == "__main__":
    train_barcode_model()
```

## 第四阶段：独立测试

### 4.1 创建测试脚本
创建 `test_trained_yolo.py`：
```python
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
```

### 4.2 对比测试脚本
创建 `compare_yolo_models.py`：
```python
#!/usr/bin/env python
"""
对比原始YOLO模型和训练后模型的检测效果
"""
import cv2
import json
from ultralytics import YOLO

def compare_models(image_path):
    """对比原始模型和训练后模型"""
    
    # 原始模型
    original_model = YOLO('yolov8n.pt')
    original_results = original_model(cv2.imread(image_path))
    
    # 训练后模型
    trained_model = YOLO('barcode_training/barcode_detector_v1/weights/best.pt')
    trained_results = trained_model(cv2.imread(image_path))
    
    # 分析对比结果
    comparison = {
        'image': image_path,
        'original_model': {
            'detections': len(original_results[0].boxes) if original_results[0].boxes else 0,
            'classes': extract_classes(original_results)
        },
        'trained_model': {
            'detections': len(trained_results[0].boxes) if trained_results[0].boxes else 0,
            'classes': extract_classes(trained_results)
        }
    }
    
    return comparison

def extract_classes(results):
    """提取检测到的类别"""
    classes = []
    if results[0].boxes is not None:
        for box in results[0].boxes:
            class_id = int(box.cls[0].cpu().numpy())
            classes.append(results[0].names[class_id])
    return classes

if __name__ == "__main__":
    test_images = [
        '/app/media/detection_frames/snapshot_71_1765980946.jpg',
        '/app/media/detection_frames/complex_test_barcode.jpg'
    ]
    
    for img in test_images:
        comparison = compare_models(img)
        print(f"\n=== {img} ===")
        print(f"原始模型: {comparison['original_model']['detections']} 个检测")
        print(f"  类别: {comparison['original_model']['classes']}")
        print(f"训练模型: {comparison['trained_model']['detections']} 个检测")
        print(f"  类别: {comparison['trained_model']['classes']}")
```

## 第五阶段：性能验证

### 5.1 准确性指标
- **精确率 (Precision)**: 检测到的条码中真正是条码的比例
- **召回率 (Recall)**: 真实条码中被正确检测出的比例  
- **F1分数**: 精确率和召回率的调和平均数
- **mAP (mean Average Precision)**: 目标检测的核心指标

### 5.2 性能指标
- **检测速度**: 每张图像的处理时间
- **内存使用**: 模型运行时的内存占用
- **模型大小**: 模型文件的大小

### 5.3 验证数据集
使用预留的测试集进行验证：
```python
# 验证脚本
def validate_model(model_path, test_dataset_path):
    model = YOLO(model_path)
    metrics = model.val(data=test_dataset_path)
    return metrics
```

## 第六阶段：系统集成计划

### 6.1 修改现有检测器
在 `file_processor/video/detectors/` 中创建新的 `yolo_trained_detector.py`：

```python
class TrainedYOLODetector:
    def __init__(self, model_path='barcode_training/barcode_detector_v1/weights/best.pt'):
        self.model = YOLO(model_path)
        self.confidence_threshold = 0.5
    
    def detect(self, image):
        """使用训练好的模型检测条码"""
        results = self.model(image, conf=self.confidence_threshold)
        
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    detection = self.extract_detection_info(box)
                    detections.append(detection)
        
        return detections
```

### 6.2 集成到现有流程
修改 `detection_service.py` 添加新的检测器：
```python
def detect_with_trained_yolo(self, image):
    """使用训练后的YOLO模型进行检测"""
    if hasattr(self, 'trained_yolo_detector'):
        return self.trained_yolo_detector.detect(image)
    return []
```

## 时间计划（混合方案）

### 第一周：数据准备（本地标注 + Docker集成）
- **第1-2天**：
  - 本地安装LabelImg标注工具
  - 从Docker容器复制图像数据到本地
  - 创建本地标注目录结构
- **第3-4天**：
  - 使用本地LabelImg进行标注工作
  - 质量检查和标注规范制定
- **第5-7天**：
  - 数据集划分（train/val/test）
  - 上传标注数据到Docker容器
  - 在Docker中创建训练配置文件

### 第二周：模型训练和测试（Docker环境）
- **第1-3天**：
  - Docker训练环境配置和测试
  - 模型训练（在Docker后台运行）
- **第4-5天**：
  - 训练结果下载到本地
  - 独立测试脚本开发和验证
- **第6-7天**：
  - 模型对比测试和性能评估
  - 模型调优（如需要）

### 第三周：系统集成
- **第1-3天**：修改现有代码，集成新模型
- **第4-5天**：系统测试和优化
- **第6-7天**：部署和文档更新

## 预期效果

### 训练前（原始YOLOv8）：
- **条码检测率**: 20-30%（通用模型）
- **误检率**: 较高（需要通过后处理过滤）
- **处理速度**: 快速，但准确度有限

### 训练后（专门模型）：
- **条码检测率**: 70-90%（针对条码优化）
- **误检率**: 显著降低
- **处理速度**: 稍慢（专门模型），但整体效果更好

## 风险评估

### 技术风险：
- **数据量不足**: 可能影响模型效果
- **训练时间**: 在CPU上训练可能较慢
- **模型过拟合**: 需要合理的数据增强

### 解决方案：
- **数据增强**: 使用旋转、缩放、亮度调整等
- **迁移学习**: 从预训练模型开始
- **早停机制**: 防止过拟合

## 需要确认的事项

1. **本地LabelImg安装：是否同意在本地安装LabelImg进行标注工作？**
2. **数据标注工作量：预计需要标注200-500张图像，时间投入是否可接受？**
3. **训练时间：在CPU上训练可能需要几个小时，是否可以接受？**
4. **简化版方案：是否需要我准备简化版方案（使用更少的数据和更短的训练时间）？**
5. **系统集成：训练完成后，是否希望立即集成到现有系统中？**

## 本地环境要求

**标注工具要求：**
- Python 3.7+
- PyQt5（用于GUI）
- 足够的磁盘空间存储图像和标注文件

**推荐标注工作流程：**
1. 批次处理：每次标注50-100张图像
2. 质量检查：定期检查标注质量
3. 备份管理：定期备份标注文件

请确认这个更新后的训练测试方案，我将按照您的指示开始执行本地标注环境的准备工作。

请确认这个训练测试方案，我将按照您的指示开始执行。