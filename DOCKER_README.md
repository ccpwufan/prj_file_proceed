# Docker部署说明

## 快速启动

### 1. 使用Docker Compose启动应用
```bash
# 构建并启动容器
docker-compose up --build -d

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs web

# 进入sh
docker-compose exec -it prj_file_proceed-web-1 bash
```


### 2. 访问应用
- 应用地址: http://127.0.0.1:8000
- 管理后台: http://127.0.0.1:8000/admin/

### 3. 数据库迁移
首次启动时，容器会自动执行数据库迁移。如需手动执行：
```bash
docker-compose exec web python manage.py migrate
```

### 4. 创建超级用户（可选）
```bash
docker-compose exec web python manage.py createsuperuser
```

## 环境配置

### 环境变量文件
配置文件：`.env.docker`

```bash
# Docker环境标识
DOCKER_ENV=true

# Django设置
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库配置
DATABASE_PATH=/app/db.sqlite3

# Dify API配置
DIFY_SERVER=http://dify.example.com
DIFY_API_KEY=your-dify-api-key
DIFY_USER=admin
DIFY_TIMEOUT=30

# 媒体文件路径
MEDIA_ROOT=/app/media
```

## 数据持久化

### SQLite数据库
- 数据库文件位置：`/app/db.sqlite3`

### 媒体文件
- 上传文件位置：`/app/media/`
- 目录结构：
  - `/app/media/pdfs/` - PDF文件
  - `/app/media/images/` - 图片文件

## 常用命令

### 容器管理
```bash
# 启动容器
docker-compose up -d

# 停止容器
docker-compose down

# 重启容器
docker-compose restart web

# 进入容器
docker-compose exec web bash
```

### 应用管理
```bash
# 数据库迁移
docker-compose exec web python manage.py migrate

# 创建超级用户
docker-compose exec web python manage.py createsuperuser

# 收集静态文件
docker-compose exec web python manage.py collectstatic --noinput

# Django shell
docker-compose exec web python manage.py shell
```

### 日志查看
```bash
# 查看所有日志
docker-compose logs

# 查看web服务日志
docker-compose logs web

# 实时查看日志
docker-compose logs -f web
```

## 故障排除

### 1. 容器无法启动
```bash
# 查看容器状态
docker-compose ps

# 查看错误日志
docker-compose logs web

# 重新构建镜像
docker-compose build --no-cache
```

### 2. 数据库连接问题
```bash
# 检查数据库文件权限
docker-compose exec web ls -la /app/db_data/

# 手动执行迁移
docker-compose exec web python manage.py migrate
```

### 3. 文件上传问题
```bash
# 检查媒体目录权限
docker-compose exec web ls -la /app/media/

# 创建必要目录
docker-compose exec web mkdir -p /app/media/pdfs /app/media/images
```

### 4. Dify API连接问题
```bash
# 检查环境变量
docker-compose exec web python -c "import os; from dotenv import load_dotenv; load_dotenv('/app/.env.docker'); print('DIFY_SERVER:', os.getenv('DIFY_SERVER'))"

# 测试API连接
docker-compose exec web python -c "import requests; print(requests.get('http://your-dify-server', timeout=5).status_code)"
```

## 生产环境注意事项

### 1. 安全配置
- 修改默认的SECRET_KEY
- 设置DEBUG=False
- 配置ALLOWED_HOSTS为实际域名
- 使用HTTPS协议

### 2. 性能优化
- 使用Gunicorn或uWSGI替代开发服务器
- 配置Nginx作为反向代理
- 启用静态文件缓存

### 3. 备份策略
```bash
# 备份数据库
docker-compose exec web cp /app/db_data/db.sqlite3 /backup/db_backup_$(date +%Y%m%d).sqlite3

# 备份媒体文件
docker run --rm -v $(pwd)/media:/source -v $(pwd)/backup:/backup alpine cp -r /source /backup/media_$(date +%Y%m%d)
```

## 版本信息
- Django: 5.2.8
- PyMuPDF: 1.23.0
- Pillow: 10.0.0
- requests: 2.31.0
- Markdown: 3.10
- python-dotenv: 1.0.0

## 技术支持
如有问题，请检查：
1. Docker和Docker Compose版本兼容性
2. 环境变量配置正确性
3. 网络连接和防火墙设置
4. 磁盘空间和权限设置