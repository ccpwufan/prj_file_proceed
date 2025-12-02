#!/bin/bash
# 临时启动脚本 - 确保所有依赖都安装后再启动Django

# 安装 python-dotenv
pip install python-dotenv

# 运行数据库迁移
python manage.py migrate

# 启动Django开发服务器
python manage.py runserver 0.0.0.0:8000