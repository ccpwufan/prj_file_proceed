# Video Recognition Feature Development TO-DO List

## 项目概述
在现有的file_processor应用内创建video命名空间，实现视频物体识别功能，特别针对视频中手机的识别，支持摄像头和文件上传两种视频来源。

---

## 阶段一：基础文件结构创建

### 创建video命名空间目录结构
- [ ] 在file_processor目录下创建video子目录
  - [ ] 创建video/__init__.py文件
  - [ ] 创建video/models.py文件（数据模型）
  - [ ] 创建video/views.py文件（视图函数）
  - [ ] 创建video/urls.py文件（URL路由）
  - [ ] 创建video/forms.py文件（表单类）
  - [ ] 创建video/services.py文件（业务逻辑）
  - [ ] 创建video/admin.py文件（管理界面）

### 创建模板目录结构
- [ ] 创建file_processor/templates/file_processor/video目录
- [ ] 创建video/base.html基础模板（可继承主base.html）
- [ ] 创建必要的HTML模板文件

---

## 阶段二：数据模型设计

### 实现数据模型
- [ ] 在file_processor/video/models.py中定义数据模型
  - [ ] 实现VideoFile模型（存储上传的视频文件信息）
    ```python
    # 字段包括：user, video_file, original_filename, created_at, duration, status, thumbnail
    ```
  - [ ] 实现VideoAnalysis模型（存储分析任务信息）
    ```python
    # 字段包括：video_file, user, analysis_type, created_at, completed_at, status, result_summary
    ```
  - [ ] 实现DetectionFrame模型（存储检测结果帧信息）
    ```python
    # 字段包括：video_analysis, frame_number, frame_image, detection_data, timestamp
    ```

### 数据库迁移
- [ ] 生成数据库迁移文件
  ```bash
  python manage.py makemigrations
  ```
- [ ] 执行数据库迁移
  ```bash
  python manage.py migrate
  ```

### 管理界面配置
- [ ] 更新file_processor/admin.py
  - [ ] 注册video模型到Django管理界面
  - [ ] 自定义管理界面显示字段

---

## 阶段三：URL配置和路由

### 主路由配置
- [ ] 更新file_processor/urls.py
  - [ ] 添加video命名空间的路由包含
  ```python
  path('video/', include('file_processor.video.urls', namespace='video')),
  ```

### Video路由配置
- [ ] 实现file_processor/video/urls.py
  - [ ] 配置video相关页面的URL路由
  ```python
  urlpatterns = [
      path('home/', views.video_home, name='home'),
      path('upload/', views.video_upload, name='upload'),
      path('camera/', views.camera_detection, name='camera'),
      path('results/<int:analysis_id>/', views.show_results, name='results'),
      path('history/', views.video_history, name='history'),
      path('download/<int:analysis_id>/', views.download_result, name='download'),
  ]
  ```
  - [ ] 设置命名空间

---

## 阶段四：核心服务开发

### 视频处理服务
- [ ] 在file_processor/video/services.py中实现核心功能
  - [ ] 实现视频文件处理服务
    ```python
    def process_uploaded_video(video_file):
        # 视频格式验证、转码、元数据提取
    ```
  - [ ] 实现视频帧提取功能
    ```python
    def extract_frames(video_path, interval=1.0):
        # 按时间间隔提取视频帧
    ```
  - [ ] 实现视频预处理功能
    ```python
    def preprocess_frame(frame):
        # 图像大小调整、归一化等
    ```

### AI识别服务
- [ ] 集成AI模型
  - [ ] 添加OpenCV等依赖到requirements.txt
    ```
    opencv-python>=4.5.0
    numpy>=1.19.0
    Pillow>=8.0.0
    ```
  - [ ] 实现手机检测模型加载和推理
    ```python
    def load_phone_detection_model():
        # 加载预训练的YOLO或其他检测模型
    ```
  - [ ] 实现绿色框标注功能
    ```python
    def draw_detection_boxes(frame, detections):
        # 在检测到的手机周围绘制绿色边框
    ```
  - [ ] 实现检测结果视频生成
    ```python
    def generate_annotated_video(original_video, detections):
        # 生成带标注的结果视频
    ```

### 摄像头处理服务
- [ ] 实现摄像头处理服务
  - [ ] 实现摄像头访问和流处理
  - [ ] 实现实时帧捕获和检测
  - [ ] 实现检测结果WebSocket传输（可选）

---

## 阶段五：视图函数开发

### 视图函数实现
- [ ] 在file_processor/video/views.py中实现视图函数
  - [ ] 实现video_home视图（主页，选择视频来源）
  - [ ] 实现video_upload视图（视频上传和处理）
  - [ ] 实现camera_detection视图（摄像头检测）
  - [ ] 实现show_results视图（展示检测结果）
  - [ ] 实现video_history视图（历史记录）
  - [ ] 实现download_result视图（下载结果视频）

### 表单类实现
- [ ] 在file_processor/video/forms.py中实现表单
  - [ ] 实现VideoUploadForm表单
    ```python
    class VideoUploadForm(forms.ModelForm):
        class Meta:
            model = VideoFile
            fields = ['video_file']
    ```
  - [ ] 实现DetectionParametersForm表单
    ```python
    class DetectionParametersForm(forms.Form):
        detection_threshold = forms.FloatField(min_value=0.0, max_value=1.0)
        frame_interval = forms.FloatField(min_value=0.1)
    ```

---

## 阶段六：前端模板开发

### HTML模板创建
- [ ] 在file_processor/templates/file_processor/video/目录下创建模板
  - [ ] 创建base.html基础模板
    ```html
    {% extends "file_processor/base.html" %}
    {% block content %}
    <!-- video specific content -->
    {% endblock %}
    ```
  - [ ] 创建home.html主页模板（视频源选择）
  - [ ] 创建upload.html视频上传模板
  - [ ] 创建camera.html摄像头检测模板
  - [ ] 创建results.html结果展示模板
  - [ ] 创建history.html历史记录模板

### 前端交互逻辑
- [ ] 实现JavaScript功能
  - [ ] 实现摄像头访问和视频流显示（WebRTC）
  - [ ] 实现视频上传进度显示
  - [ ] 实现视频播放控制（HTML5 Video API）
  - [ ] 实现检测结果展示（绿色框标注）
  - [ ] 实现AJAX异步调用处理API

### 导航更新
- [ ] 更新主base.html导航
  - [ ] 在file_processor/templates/file_processor/base.html中添加"视频识别"导航链接
  ```html
  <li><a href="{% url 'file_processor:video:home' %}">视频识别</a></li>
  ```

---

## 阶段七：集成和优化

### 配置文件更新
- [ ] 更新settings.py和requirements.txt
  - [ ] 添加视频处理相关依赖到requirements.txt
  - [ ] 配置媒体文件路径支持视频文件
  ```python
  MEDIA_URL = '/media/'
  MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
  ```

### Docker配置更新
- [ ] 更新Docker配置
  - [ ] 更新Dockerfile安装OpenCV和FFmpeg
    ```dockerfile
    RUN apt-get update && apt-get install -y \
        ffmpeg \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libglib2.0-0
    ```
  - [ ] 更新docker-compose.yml支持视频处理

### 静态文件处理
- [ ] 实现静态文件处理
  - [ ] 配置视频文件的存储和访问
  - [ ] 实现结果视频的存储和访问
  - [ ] 配置视频缩略图生成

---

## 阶段八：测试和文档

### 功能测试
- [ ] 单元测试
  - [ ] 测试视频上传功能
  - [ ] 测试视频处理和AI识别
  - [ ] 测试摄像头检测功能
  - [ ] 测试结果展示和下载

### 集成测试
- [ ] 完整工作流测试
  - [ ] 测试文件上传模式的完整流程
  - [ ] 测试摄像头模式的完整流程
  - [ ] 测试历史记录查看功能
  - [ ] 测试错误处理和异常情况

### 性能测试
- [ ] 性能优化测试
  - [ ] 测试不同大小视频处理时间
  - [ ] 测试并发处理能力
  - [ ] 测试内存使用情况

### 浏览器兼容性测试
- [ ] 前端兼容性测试
  - [ ] 测试Chrome浏览器兼容性
  - [ ] 测试Firefox浏览器兼容性
  - [ ] 测试移动端浏览器兼容性

### 文档更新
- [ ] 更新项目文档
  - [ ] 更新DOCKER_README.md添加视频处理说明
  - [ ] 创建视频功能使用说明
  - [ ] 添加API文档

---

## 文件结构预览

```
file_processor/
├── __init__.py
├── admin.py              # 更新：注册video模型
├── apps.py
├── urls.py               # 更新：添加video路由
├── models.py             # 现有文件处理模型
├── views.py              # 现有文件处理视图
├── forms.py              # 现有文件处理表单
├── services.py           # 现有文件处理服务
├── templates/
│   └── file_processor/
│       ├── base.html     # 更新：添加视频识别导航
│       ├── (现有模板文件)
│       └── video/
│           ├── base.html
│           ├── home.html
│           ├── upload.html
│           ├── camera.html
│           ├── results.html
│           └── history.html
├── file/                 # 现有文件处理功能
│   └── (现有文件)
└── video/                # 新增视频处理命名空间
    ├── __init__.py
    ├── models.py         # 视频相关模型
    ├── views.py          # 视频相关视图
    ├── urls.py           # 视频相关路由
    ├── forms.py          # 视频相关表单
    ├── services.py       # 视频处理服务
    └── admin.py          # 视频模型管理
```

---

## URL设计示例

```
/file_processor/video/home                    # 视频识别主页
/file_processor/video/upload                  # 视频上传
/file_processor/video/camera                  # 摄像头检测
/file_processor/video/results/<analysis_id>   # 结果展示
/file_processor/video/history                 # 历史记录
/file_processor/video/download/<analysis_id>  # 下载结果
```

---

## 技术选型建议

### 后端技术栈
- **Django**: 基础框架（已有）
- **OpenCV**: 视频处理和图像分析
- **FFmpeg**: 视频格式转换和处理
- **NumPy**: 数值计算支持

### AI模型选择
- **方案一（快速实现）**: OpenCV DNN + YOLO预训练模型
- **方案二（高精度）**: 自定义训练手机检测模型
- **方案三（集成现有）**: 使用现有的Dify API（如果支持图像识别）

### 前端技术栈
- **HTML5 Video API**: 视频播放和控制
- **WebRTC**: 摄像头访问
- **JavaScript**: 视频流处理和结果展示
- **WebSocket**: 实时视频流传输（可选）

---

## 可能的挑战和解决方案

### 1. 大视频文件处理
**挑战**: 大文件上传和处理可能导致超时
**解决方案**: 
- 使用分块上传
- 实现异步任务队列（Celery）
- 添加进度显示

### 2. 实时处理性能
**挑战**: 实时视频处理可能影响性能
**解决方案**:
- 使用帧跳跃策略（不必处理每一帧）
- 多线程/异步处理
- 结果缓存机制

### 3. 浏览器兼容性
**挑战**: 不同浏览器对WebRTC支持程度不同
**解决方案**:
- 使用成熟的WebRTC库（如adapter.js）
- 提供降级方案
- 充分的浏览器测试

### 4. AI模型部署
**挑战**: AI模型加载和推理可能需要大量资源
**解决方案**:
- 使用容器化部署
- 模型量化优化
- GPU加速（如果可用）

---

## 开发优先级建议

### MVP版本（最小可行产品）
1. **必须实现**: 视频文件上传 + 基础手机检测
2. **次要功能**: 结果展示 + 历史记录
3. **扩展功能**: 摄像头实时检测 + 高级配置

### 完整版本
1. 实现所有基础功能
2. 添加性能优化
3. 完善错误处理
4. 添加扩展功能

---

## 注意事项

1. **依赖关系**: 阶段一和阶段二是基础，必须先完成
2. **并行开发**: 阶段二、三、四可以部分并行开发
3. **测试驱动**: 每个功能模块完成后立即进行测试
4. **文档同步**: 及时更新相关文档和注释
5. **版本控制**: 定期提交代码，便于回滚和协作

---

## 完成标准

每个阶段的完成标准：
- [ ] 代码实现完成
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 代码审查完成
- [ ] 文档更新完成

---

*最后更新: 2025-12-03*
*项目: file_processor video recognition feature*