# File Processor 生产环境部署清单

## 概述

本文档详细描述了如何将 File Processor 项目部署到 Ubuntu 24.03 服务器上的生产环境。项目使用：
- **Docker** 和 **docker-compose** 进行容器化部署
- **Nginx** 作为反向代理和静态文件服务
- **SQLite** 数据库（适合中小型应用）
- **Django 5.2.8** 作为Web框架

### 项目特性
- PDF文件处理和转换
- 视频文件转换（HEVC → H.264）
- 文件上传和管理
- Dify API集成
- 队列任务处理系统

## 部署前检查清单

### 🔍 项目状态检查
- [x] 代码已提交到版本控制系统
- [x] 本地环境测试通过
- [x] 视频转换重试问题已修复
- [x] 时区显示问题已解决

### 🖥️ 服务器环境要求
**系统要求：**
- Ubuntu 24.03 LTS
- 最少 4GB RAM
- 最少 20GB 磁盘空间（用于媒体文件存储）
- Docker 20.10+ 
- docker-compose 2.0+

**网络要求：**
- 防火墙允许端口 80（HTTP）
- 如果使用 HTTPS，需要端口 443
- 能够访问 Dify API 服务器

### 📋 部署清单

#### 阶段1：环境准备
- [ ] 确认 Docker 和 docker-compose 已安装
- [ ] 配置防火墙规则
- [ ] 创建部署目录
- [ ] 设置适当的文件权限
- [ ] 创建备份目录

#### 阶段2：项目配置
- [ ] 传输项目代码到服务器
- [ ] 配置生产环境变量
- [ ] 生成强随机 SECRET_KEY
- [ ] 配置 ALLOWED_HOSTS
- [ ] 设置 Dify API 凭据

#### 阶段3：容器配置
- [ ] 创建 Nginx 配置文件
- [ ] 创建 Docker 网络
- [ ] 配置静态文件服务
- [ ] 配置媒体文件服务

#### 阶段4：部署验证
- [ ] 构建 Docker 镜像
- [ ] 收集静态文件
- [ ] 启动容器服务
- [ ] 验证服务可访问性
- [ ] 测试文件上传功能
- [ ] 验证视频转换功能

#### 阶段5：运维配置
- [ ] 设置自动重启策略
- [ ] 配置日志管理
- [ ] 实施备份策略
- [ ] 设置监控告警

## 配置文件详解

### 1. `.env.production` - 生产环境配置

**安全配置：**
```bash
# 生成强随机密钥（复制输出结果）
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**完整配置模板：**
```env
# ========================================
# Django 基础配置
# ========================================
# 生成的强随机密钥（替换上面的输出）
SECRET_KEY=django-insecure-GENERATE-RANDOM-KEY-HERE
DEBUG=False
ALLOWED_HOSTS=sgibm-scorpio.eur.gd.corp,localhost,127.0.0.1,your-server-ip

# ========================================
# Dify API 配置
# ========================================
DIFY_API_KEY=app-YOUR-DIFY-API-KEY-HERE
DIFY_USER=your-dify-username
DIFY_SERVER=http://sgibm-scorpio.eur.gd.corp  # 或 https://api.dify.ai
DIFY_TIMEOUT=300

# 特殊API密钥（发票分析）
DIFY_API_KEY_INVOICE_FILES=app-YOUR-INVOICE-API-KEY

# ========================================
# 环境标识
# ========================================
DOCKER_ENV=true

# ========================================
# 可选：性能和安全配置
# ========================================
# 数据库连接优化（SQLite）
DATABASE_TIMEOUT=30

# 文件上传限制（字节）
MAX_UPLOAD_SIZE=52428800  # 50MB

# 会话安全配置
SESSION_COOKIE_SECURE=False  # 设为True如果使用HTTPS
CSRF_COOKIE_SECURE=False     # 设为True如果使用HTTPS
```

### 2. `docker-compose.production.yml` - 生产环境容器配置

**当前项目已包含此文件，可根据需要调整：**
```yaml
version: '3.8'

services:
  # Django Web应用容器
  web:
    build: .
    command: /start.sh
    env_file:
      - .env.production
    restart: unless-stopped
    volumes:
      # 媒体文件持久化存储
      - ./media:/app/media
      # SQLite数据库持久化
      - ./db.sqlite3:/app/db.sqlite3
    networks:
      - app-network
    # 资源限制（可选）
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  # Nginx反向代理容器
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      # - "443:443"  # HTTPS端口（如需要）
    volumes:
      # Nginx配置
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      # 静态文件服务
      - ./static:/app/static:ro
      # 媒体文件服务
      - ./media:/app/media:ro
      # SSL证书（如需要）
      # - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
    networks:
      - app-network
    restart: unless-stopped

# Docker网络配置
networks:
  app-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 3. Nginx配置文件

**创建目录和配置：**
```bash
# 创建Nginx配置目录
mkdir -p nginx/conf.d
```

**nginx/conf.d/file-processor.conf：**
```nginx
# 上游服务器配置
upstream file_processor_backend {
    server web:8000;
    # 负载均衡（如需要多实例）
    # server web:8000 weight=1 max_fails=3 fail_timeout=30s;
}

# 服务器配置
server {
    listen 80;
    server_name sgibm-scorpio.eur.gd.corp;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # 客户端上传大小限制
    client_max_body_size 50M;
    
    # 静态文件服务
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # 压缩配置
        gzip_static on;
        gzip_types text/css application/javascript application/json;
    }
    
    # 媒体文件服务（用户上传文件）
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
        
        # 安全配置：禁止执行脚本
        location ~* \.(php|jsp|asp|sh|py)$ {
            deny all;
        }
    }
    
    # Django应用代理
    location / {
        proxy_pass http://file_processor_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # WebSocket支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 健康检查端点
    location /health/ {
        proxy_pass http://file_processor_backend/admin/;
        access_log off;
    }
    
    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

## 详细部署步骤

### 🚀 阶段1：环境准备

#### 1.1 系统要求验证
```bash
# 检查系统版本
lsb_release -a

# 检查Docker版本
docker --version
docker-compose --version

# 检查系统资源
free -h
df -h
```

#### 1.2 防火墙配置
```bash
# 使用 ufw（Ubuntu默认）
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp  # HTTPS（如需要）
sudo ufw reload

# 或使用 iptables
sudo iptables -L
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

#### 1.3 创建部署结构
```bash
# 主部署目录
sudo mkdir -p /opt/file-processor
sudo mkdir -p /backup/file-processor
sudo mkdir -p /var/log/file-processor

# 设置权限
sudo chown -R $USER:$USER /opt/file-processor
sudo chown -R $USER:$USER /backup/file-processor
sudo chown -R $USER:$USER /var/log/file-processor

# 设置目录权限
chmod 755 /opt/file-processor
chmod 700 /backup/file-processor
chmod 755 /var/log/file-processor
```

### 📦 阶段2：项目部署

#### 2.1 代码部署
```bash
cd /opt/file-processor

# 方法1：Git clone（推荐）
git clone https://your-repo-url.git .

# 方法2：SCP上传（从本地执行）
# scp -r /path/to/local/prj_file_proceed/* user@server:/opt/file-processor/

# 验证文件完整性
ls -la
```

#### 2.2 配置生产环境变量
```bash
# 生成安全密钥
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# 创建.env.production文件
cat > .env.production << EOF
# Django 配置
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=sgibm-scorpio.eur.gd.corp,localhost,127.0.0.1

# Dify API 配置
DIFY_API_KEY=app-YOUR-ACTUAL-API-KEY
DIFY_USER=your-dify-username
DIFY_SERVER=http://sgibm-scorpio.eur.gd.corp
DIFY_TIMEOUT=300

DIFY_API_KEY_INVOICE_FILES=app-YOUR-INVOICE-API-KEY

# 环境配置
DOCKER_ENV=true
EOF

# 设置文件权限
chmod 600 .env.production
```

#### 2.3 Nginx配置
```bash
# 创建Nginx配置目录
mkdir -p nginx/conf.d

# 创建Nginx配置文件
cat > nginx/conf.d/file-processor.conf << 'EOF'
upstream file_processor_backend {
    server web:8000;
}

server {
    listen 80;
    server_name sgibm-scorpio.eur.gd.corp;
    
    client_max_body_size 50M;
    
    location /static/ {
        alias /app/static/;
        expires 30d;
    }
    
    location /media/ {
        alias /app/media/;
        expires 7d;
    }
    
    location / {
        proxy_pass http://file_processor_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

### 🏗️ 阶段3：容器构建和启动

#### 3.1 构建Docker镜像
```bash
# 确保在项目根目录
cd /opt/file-processor

# 构建镜像（首次构建可能需要10-20分钟）
docker-compose -f docker-compose.production.yml build --no-cache

# 验证镜像构建
docker images | grep file-processor
```

#### 3.2 数据库初始化
```bash
# 运行数据库迁移
docker-compose -f docker-compose.production.yml run --rm web python manage.py migrate

# 创建超级用户（可选）
docker-compose -f docker-compose.production.yml run --rm web python manage.py createsuperuser

# 收集静态文件
docker-compose -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput
```

#### 3.3 启动服务
```bash
# 启动所有服务
docker-compose -f docker-compose.production.yml up -d

# 检查服务状态
docker-compose -f docker-compose.production.yml ps

# 查看启动日志
docker-compose -f docker-compose.production.yml logs -f --tail=50
```

### ✅ 阶段4：部署验证

#### 4.1 基础连接测试
```bash
# 测试服务连通性
curl -I http://localhost
curl -I http://sgibm-scorpio.eur.gd.corp

# 检查容器健康状态
docker-compose -f docker-compose.production.yml exec web python manage.py check
```

#### 4.2 功能验证
```bash
# 测试管理后台
curl http://localhost/admin/

# 测试API端点（如果存在）
curl http://localhost/api/

# 检查静态文件
curl -I http://localhost/static/
```

#### 4.3 性能基准测试
```bash
# 安装Apache Bench进行简单测试
sudo apt-get install -y apache2-utils

# 并发测试
ab -n 100 -c 10 http://localhost/

# 压力测试（可选）
ab -n 1000 -c 50 http://localhost/
```

### 🔧 阶段5：运维配置

#### 5.1 日志管理配置
```bash
# 创建日志轮转配置
sudo tee /etc/logrotate.d/file-processor << 'EOF'
/var/log/file-processor/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF

# Docker日志配置
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
EOF

# 重启Docker服务
sudo systemctl restart docker
```

#### 5.2 自动备份配置
```bash
# 创建备份脚本
cat > /opt/file-processor/backup.sh << 'EOF'
#!/bin/bash

# 配置
BACKUP_DIR="/backup/file-processor"
PROJECT_DIR="/opt/file-processor"
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/$DATE"

# 创建备份目录
mkdir -p "$BACKUP_PATH"

# 备份数据库
echo "备份数据库..."
cp "$PROJECT_DIR/db.sqlite3" "$BACKUP_PATH/"

# 备份配置文件
echo "备份配置文件..."
cp "$PROJECT_DIR/.env.production" "$BACKUP_PATH/"
cp -r "$PROJECT_DIR/nginx" "$BACKUP_PATH/"

# 备份媒体文件
echo "备份媒体文件..."
tar -czf "$BACKUP_PATH/media.tar.gz" -C "$PROJECT_DIR" media

# 清理旧备份（保留30天）
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -mtime +30 -type d -exec rm -rf {} \;

echo "备份完成: $BACKUP_PATH"
EOF

chmod +x backup.sh

# 添加到crontab（每日凌晨2点备份）
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/file-processor/backup.sh >> /var/log/file-processor/backup.log 2>&1") | crontab -
```

#### 5.3 监控和告警
```bash
# 创建健康检查脚本
cat > /opt/file-processor/health_check.sh << 'EOF'
#!/bin/bash

# 检查服务状态
if ! docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo "ERROR: 服务未正常运行"
    exit 1
fi

# 检查Web服务响应
if ! curl -f -s http://localhost/ > /dev/null; then
    echo "ERROR: Web服务无响应"
    exit 1
fi

echo "OK: 服务运行正常"
EOF

chmod +x health_check.sh

# 每5分钟检查一次（可选）
# (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/file-processor/health_check.sh >> /var/log/file-processor/health.log 2>&1") | crontab -
```

### 🔄 更新和维护

#### 应用更新流程
```bash
# 1. 备份当前版本
./backup.sh

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建镜像
docker-compose -f docker-compose.production.yml build

# 4. 运行数据库迁移
docker-compose -f docker-compose.production.yml run --rm web python manage.py migrate

# 5. 收集静态文件
docker-compose -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput

# 6. 重启服务
docker-compose -f docker-compose.production.yml up -d --force-recreate

# 7. 验证更新
./health_check.sh
```

## 注意事项

1. **安全性**：
   - 确保 `.env.production` 文件权限设置正确，仅允许应用访问
   - 不要在代码仓库中提交实际的密钥文件
   - 在生产环境中始终将 DEBUG 设置为 False
   - 通过 Docker 网络实现容器间安全通信

2. **性能考虑**：
   - 虽然继续使用 SQLite，但在高并发场景下仍可能成为瓶颈
   - Nginx 提供静态文件服务有助于提升性能

3. **监控**：
   - 可以通过 Docker 和系统工具监控应用状态
   - 设置适当的告警机制以检测服务故障

4. **扩展性**：
   - 当前架构适用于中小型应用
   - 如需处理更多并发请求，可考虑横向扩展

## 🚨 故障排除和常见问题

### 常见启动问题

#### 1. 容器启动失败
**症状：** `docker-compose up` 后容器立即退出
```bash
# 检查容器日志
docker-compose -f docker-compose.production.yml logs web

# 常见原因和解决方案
# 检查端口占用
sudo netstat -tulpn | grep :80

# 检查Docker服务状态
sudo systemctl status docker

# 重新构建镜像
docker-compose -f docker-compose.production.yml build --no-cache
```

#### 2. 数据库连接错误
**症状：** SQLite数据库无法访问或权限错误
```bash
# 检查数据库文件权限
ls -la db.sqlite3

# 修复权限
sudo chown $USER:$USER db.sqlite3
chmod 664 db.sqlite3

# 检查数据库完整性
docker-compose -f docker-compose.production.yml run --rm web python manage.py check --database default
```

#### 3. 静态文件404错误
**症状：** CSS/JS文件无法加载
```bash
# 重新收集静态文件
docker-compose -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput --clear

# 检查static目录权限
ls -la static/

# 验证Nginx配置
docker-compose -f docker-compose.production.yml exec nginx nginx -t
```

### 性能问题排查

#### 1. 响应缓慢
```bash
# 检查容器资源使用
docker stats

# 检查系统负载
top
htop
iostat -x 1

# 分析Nginx访问日志
docker-compose -f docker-compose.production.yml exec nginx tail -f /var/log/nginx/access.log
```

#### 2. 内存不足
```bash
# 检查内存使用
free -h
docker system df

# 清理Docker缓存
docker system prune -f
docker image prune -f
```

### 应用特定问题

#### 1. 视频转换失败
```bash
# 检查FFmpeg是否正确安装
docker-compose -f docker-compose.production.yml exec web ffmpeg -version

# 检查视频处理队列状态
docker-compose -f docker-compose.production.yml exec web python manage.py shell
>>> from file_processor.queue.models import ProcessingTask
>>> ProcessingTask.objects.filter(status='failed').count()
```

#### 2. Dify API连接问题
```bash
# 测试API连通性
docker-compose -f docker-compose.production.yml exec web curl -v $DIFY_SERVER

# 检查API密钥配置
docker-compose -f docker-compose.production.yml exec web python -c "
import os
from django.conf import settings
print('DIFY_SERVER:', settings.DIFY_SERVER)
print('DIFY_API_KEY:', settings.DIFY_API_KEY[:10] + '...' if settings.DIFY_API_KEY else 'None')
"
```

## 🔒 SSL/HTTPS配置指南

### Let's Encrypt免费证书配置

#### 1. 安装Certbot
```bash
# 在服务器上安装Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d sgibm-scorpio.eur.gd.corp

# 测试自动续期
sudo certbot renew --dry-run
```

#### 2. 更新Nginx配置支持HTTPS
```nginx
server {
    listen 80;
    server_name sgibm-scorpio.eur.gd.corp;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name sgibm-scorpio.eur.gd.corp;
    
    # SSL证书配置（Let's Encrypt自动生成）
    ssl_certificate /etc/letsencrypt/live/sgibm-scorpio.eur.gd.corp/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sgibm-scorpio.eur.gd.corp/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # 其他配置保持不变...
    client_max_body_size 50M;
    
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://file_processor_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3. 更新Docker Compose配置
```yaml
# docker-compose.production.yml 更新
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
    - ./static:/app/static:ro
    - ./media:/app/media:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro  # SSL证书目录
```

#### 4. 更新Django设置
```env
# .env.production 更新
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

## 📊 性能监控和优化

### 1. 系统监控设置

#### 安装监控工具
```bash
# 安装htop和iotop
sudo apt-get install -y htop iotop

# 安装Docker监控工具
docker run -d --name=cadvisor \
  -p 8080:8080 \
  -v /:/rootfs:ro \
  -v /var/run:/var/run:rw \
  -v /sys:/sys:ro \
  -v /var/lib/docker/:/var/lib/docker:ro \
  gcr.io/cadvisor/cadvisor:latest
```

#### 创建性能监控脚本
```bash
cat > /opt/file-processor/monitor.sh << 'EOF'
#!/bin/bash

LOG_FILE="/var/log/file-processor/performance.log"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

# 系统资源使用
echo "=== $DATE ===" >> $LOG_FILE
echo "CPU使用率:" >> $LOG_FILE
top -bn1 | grep "Cpu(s)" >> $LOG_FILE

echo "内存使用:" >> $LOG_FILE
free -h >> $LOG_FILE

echo "磁盘使用:" >> $LOG_FILE
df -h /app/media >> $LOG_FILE

echo "Docker容器状态:" >> $LOG_FILE
docker-compose -f /opt/file-processor/docker-compose.production.yml ps >> $LOG_FILE

echo "=================" >> $LOG_FILE
echo "" >> $LOG_FILE
EOF

chmod +x monitor.sh

# 每10分钟记录一次性能数据
(crontab -l 2>/dev/null; echo "*/10 * * * * /opt/file-processor/monitor.sh") | crontab -
```

### 2. 数据库优化

#### SQLite性能调优
```sql
-- 在Django shell中执行
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
```

#### 创建数据库维护脚本
```bash
cat > /opt/file-processor/db_maintenance.sh << 'EOF'
#!/bin/bash

# 数据库优化
docker-compose -f docker-compose.production.yml exec web python manage.py shell << 'PYTHON'
import sqlite3
import os

DB_PATH = '/app/db.sqlite3'
conn = sqlite3.connect(DB_PATH)

# 执行优化命令
conn.execute("PRAGMA optimize")
conn.execute("VACUUM")
conn.execute("ANALYZE")

conn.close()
print("数据库优化完成")
PYTHON

# 检查数据库大小
du -h /opt/file-processor/db.sqlite3
EOF

chmod +x db_maintenance.sh

# 每周执行一次数据库维护
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/file-processor/db_maintenance.sh >> /var/log/file-processor/db_maintenance.log 2>&1") | crontab -
```

### 3. 应用性能优化

#### Django缓存配置
```python
# 在settings.py中添加（如果还没有）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# 会话配置
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## 🆘 灾难恢复和应急响应

### 1. 数据恢复流程

#### 完整数据恢复
```bash
# 1. 停止当前服务
docker-compose -f docker-compose.production.yml down

# 2. 备份当前状态（可选）
./backup.sh

# 3. 选择备份版本
BACKUP_DATE="20231201_020000"  # 替换为实际备份日期
BACKUP_PATH="/backup/file-processor/$BACKUP_DATE"

# 4. 恢复数据库
cp "$BACKUP_PATH/db.sqlite3" ./db.sqlite3

# 5. 恢复媒体文件
tar -xzf "$BACKUP_PATH/media.tar.gz"

# 6. 恢复配置文件
cp "$BACKUP_PATH/.env.production" ./

# 7. 重启服务
docker-compose -f docker-compose.production.yml up -d

# 8. 验证恢复
./health_check.sh
```

#### 快速回滚到上一个版本
```bash
# 快速回滚脚本
cat > /opt/file-processor/rollback.sh << 'EOF'
#!/bin/bash

LATEST_BACKUP=$(ls -t /backup/file-processor/ | head -n 1)
echo "回滚到备份: $LATEST_BACKUP"

BACKUP_PATH="/backup/file-processor/$LATEST_BACKUP"

# 停止服务
docker-compose -f docker-compose.production.yml down

# 恢复关键文件
cp "$BACKUP_PATH/db.sqlite3" ./db.sqlite3
cp "$BACKUP_PATH/.env.production" ./

# 重启服务
docker-compose -f docker-compose.production.yml up -d

echo "回滚完成"
EOF

chmod +x rollback.sh
```

### 2. 应急响应检查清单

#### 服务完全宕机响应
```bash
# 1. 快速诊断脚本
cat > /opt/file-processor/emergency_check.sh << 'EOF'
#!/bin/bash

echo "=== 紧急状态检查 ==="

# 检查Docker服务
if ! systemctl is-active --quiet docker; then
    echo "❌ Docker服务未运行"
    sudo systemctl start docker
else
    echo "✅ Docker服务正常"
fi

# 检查容器状态
if ! docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo "❌ 容器未运行"
    echo "尝试重启服务..."
    docker-compose -f docker-compose.production.yml up -d
else
    echo "✅ 容器运行正常"
fi

# 检查端口
if ! netstat -tuln | grep -q ":80 "; then
    echo "❌ 端口80未监听"
else
    echo "✅ 端口80正常监听"
fi

# 检查磁盘空间
DISK_USAGE=$(df /app | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "❌ 磁盘使用率过高: ${DISK_USAGE}%"
    echo "清理Docker缓存..."
    docker system prune -f
else
    echo "✅ 磁盘空间充足: ${DISK_USAGE}%"
fi

echo "=== 检查完成 ==="
EOF

chmod +x emergency_check.sh
```

### 3. 业务连续性计划

#### 灾难恢复时间目标（RTO）和恢复点目标（RPO）
- **RTO**: 2小时（从故障到完全恢复）
- **RPO**: 24小时（最多丢失24小时的数据）

#### 关键恢复步骤优先级
1. **P0 - 立即恢复**（<15分钟）: 服务可用性检查
2. **P1 - 紧急恢复**（<1小时）: 数据库和关键配置恢复
3. **P2 - 重要恢复**（<2小时）: 媒体文件和应用功能恢复
4. **P3 - 完整恢复**（<24小时）: 完整系统验证和优化

## 🛡️ 安全加固和最佳实践

### 1. 系统安全配置

#### 防火墙强化
```bash
# 详细的防火墙配置
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 限制SSH访问（可选）
sudo ufw limit ssh

# 启用防火墙
sudo ufw enable
```

#### Fail2ban配置
```bash
# 安装fail2ban
sudo apt-get install -y fail2ban

# 创建配置文件
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
EOF

# 启动fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 2. Docker安全最佳实践

#### 容器安全配置更新
```yaml
# docker-compose.production.yml 安全增强
version: '3.8'

services:
  web:
    build: .
    command: /start.sh
    env_file:
      - .env.production
    restart: unless-stopped
    volumes:
      - ./media:/app/media:rw
      - ./db.sqlite3:/app/db.sqlite3:rw
    networks:
      - app-network
    # 安全配置
    user: "1000:1000"  # 非root用户运行
    read_only: true     # 文件系统只读（除指定目录）
    tmpfs:
      - /tmp
      - /var/tmp
    # 资源限制
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
    # 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/admin/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./static:/app/static:ro
      - ./media:/app/media:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    networks:
      - app-network
    restart: unless-stopped
    # 安全配置
    user: "101:101"
    read_only: true
    tmpfs:
      - /var/cache/nginx
      - /var/run
    # 资源限制
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

### 3. 应用安全配置

#### Django安全设置检查
```bash
# 创建安全检查脚本
cat > /opt/file-processor/security_check.sh << 'EOF'
#!/bin/bash

echo "=== Django安全设置检查 ==="

# 检查Django安全设置
docker-compose -f docker-compose.production.yml exec web python -c "
from django.conf import settings
import os

security_checks = [
    ('DEBUG', settings.DEBUG, False),
    ('SESSION_COOKIE_SECURE', getattr(settings, 'SESSION_COOKIE_SECURE', False), True),
    ('CSRF_COOKIE_SECURE', getattr(settings, 'CSRF_COOKIE_SECURE', False), True),
    ('SECURE_SSL_REDIRECT', getattr(settings, 'SECURE_SSL_REDIRECT', False), True),
    ('SECURE_HSTS_SECONDS', getattr(settings, 'SECURE_HSTS_SECONDS', 0), 31536000),
]

for setting_name, current_value, expected_value in security_checks:
    status = '✅' if current_value == expected_value else '❌'
    print(f'{status} {setting_name}: {current_value} (期望: {expected_value})')
"

# 检查文件权限
echo "检查关键文件权限:"
ls -la .env.production
ls -la db.sqlite3

echo "=== 安全检查完成 ==="
EOF

chmod +x security_check.sh
```

### 4. 定期安全维护

#### 安全更新脚本
```bash
cat > /opt/file-processor/security_updates.sh << 'EOF'
#!/bin/bash

echo "=== 执行安全更新 ==="

# 更新系统包
sudo apt-get update
sudo apt-get upgrade -y

# 更新Docker镜像
docker-compose -f docker-compose.production.yml pull

# 重启服务（如果需要）
if [ $? -eq 0 ]; then
    echo "Docker镜像更新成功，重启服务..."
    docker-compose -f docker-compose.production.yml up -d
fi

# 清理旧镜像
docker image prune -f

echo "=== 安全更新完成 ==="
EOF

chmod +x security_updates.sh

# 每月第一个周日执行安全更新
(crontab -l 2>/dev/null; echo "0 2 * * 0 [ $(date +\%d) -le 7 ] && /opt/file-processor/security_updates.sh >> /var/log/file-processor/security_updates.log 2>&1") | crontab -
```

---

## 📋 总结和检查清单

### 部署完成验证清单

#### 基础功能验证 ✅
- [ ] 服务正常启动并响应HTTP请求
- [ ] 静态文件正确加载
- [ ] 数据库连接正常
- [ ] 文件上传功能正常
- [ ] 视频转换功能正常
- [ ] Dify API集成正常

#### 安全配置验证 ✅
- [ ] HTTPS证书正确配置
- [ ] 安全头设置正确
- [ ] 防火墙规则生效
- [ ] 文件权限设置正确
- [ ] 非root用户运行容器

#### 监控和备份验证 ✅
- [ ] 日志轮转配置生效
- [ ] 自动备份任务正常运行
- [ ] 健康检查脚本正常
- [ ] 性能监控数据收集
- [ ] 磁盘空间监控

#### 运维流程验证 ✅
- [ ] 更新流程文档完整
- [ ] 回滚流程测试通过
- [ ] 应急响应脚本可用
- [ ] 安全更新计划制定
- [ ] 灾难恢复计划确认

### 联系和支持信息

**关键联系信息：**
- 系统管理员: [管理员邮箱]
- 开发团队: [开发团队联系方式]
- 运维团队: [运维团队联系方式]

**重要文件位置：**
- 配置文件: `/opt/file-processor/.env.production`
- 日志目录: `/var/log/file-processor/`
- 备份目录: `/backup/file-processor/`
- 部署文档: `/opt/file-processor/production_deploy.md`

**快速命令参考：**
```bash
# 查看服务状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs -f

# 重启服务
docker-compose -f docker-compose.production.yml restart

# 执行备份
/opt/file-processor/backup.sh

# 健康检查
/opt/file-processor/health_check.sh

# 安全检查
/opt/file-processor/security_check.sh
```

---

*最后更新: $(date +"%Y-%m-%d")*
*文档版本: 2.0*