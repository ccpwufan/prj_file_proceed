#!/usr/bin/env python
"""
Docker测试脚本：测试视频缩略图生成功能
在Docker容器中执行：python test_thumbnail_docker.py
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
sys.path.append('/app')

django.setup()

from django.contrib.auth.models import User
from file_processor.video.models import VideoFile
from file_processor.video.services import generate_thumbnail
from django.core.files.uploadedfile import SimpleUploadedFile

def test_thumbnail_generation():
    """测试缩略图生成功能"""
    print("🧪 开始测试视频缩略图生成功能...")
    
    try:
        # 1. 检查是否有测试用户
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return False
        
        print(f"✅ 找到测试用户: {user.username}")
        
        # 2. 查找现有视频文件
        videos = VideoFile.objects.all()
        if not videos.exists():
            print("❌ 没有找到视频文件，请先上传视频")
            return False
        
        print(f"✅ 找到 {videos.count()} 个视频文件")
        
        # 3. 测试为没有缩略图的视频生成缩略图
        videos_without_thumbnails = videos.filter(thumbnail='')
        print(f"📊 {videos_without_thumbnails.count()} 个视频没有缩略图")
        
        success_count = 0
        error_count = 0
        
        for video in videos_without_thumbnails[:3]:  # 测试前3个
            print(f"\n🎬 处理视频: {video.original_filename}")
            
            try:
                # 检查视频文件是否存在
                if not os.path.exists(video.video_file.path):
                    print(f"❌ 视频文件不存在: {video.video_file.path}")
                    error_count += 1
                    continue
                
                print(f"📁 视频文件路径: {video.video_file.path}")
                
                # 生成缩略图
                print(f"🔧 开始生成缩略图...")
                thumbnail_path = generate_thumbnail(video.video_file.path)
                
                print(f"🔧 缩略图路径结果: {thumbnail_path}")
                
                if thumbnail_path:
                    full_thumbnail_path = f"/app/media/{thumbnail_path}"
                    print(f"🔧 完整缩略图路径: {full_thumbnail_path}")
                    print(f"🔧 文件是否存在: {os.path.exists(full_thumbnail_path)}")
                
                if thumbnail_path and os.path.exists(f"/app/media/{thumbnail_path}"):
                    # 更新数据库
                    relative_path = thumbnail_path.replace('/app/media/', '')
                    video.thumbnail.name = relative_path
                    video.save()
                    
                    print(f"✅ 缩略图生成成功: {relative_path}")
                    success_count += 1
                else:
                    print(f"❌ 缩略图生成失败")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ 生成缩略图时出错: {str(e)}")
                error_count += 1
        
        # 4. 测试结果统计
        print(f"\n📊 测试结果统计:")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {error_count}")
        
        if success_count > 0:
            print(f"\n🎉 缩略图功能测试通过！")
            return True
        else:
            print(f"\n💥 缩略图功能测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_opencv_import():
    """测试OpenCV导入"""
    print("🔍 测试OpenCV导入...")
    
    try:
        import cv2
        print(f"✅ OpenCV版本: {cv2.__version__}")
        return True
    except ImportError as e:
        print(f"❌ OpenCV导入失败: {str(e)}")
        return False

def check_media_directory():
    """检查媒体目录结构"""
    print("📁 检查媒体目录结构...")
    
    media_root = '/app/media'
    if not os.path.exists(media_root):
        print(f"❌ 媒体目录不存在: {media_root}")
        return False
    
    thumbnails_dir = os.path.join(media_root, 'thumbnails')
    if not os.path.exists(thumbnails_dir):
        print(f"📁 创建缩略图目录: {thumbnails_dir}")
        os.makedirs(thumbnails_dir, exist_ok=True)
    
    print(f"✅ 媒体目录正常: {media_root}")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🎬 Docker视频缩略图功能测试")
    print("=" * 60)
    
    # 1. 检查OpenCV
    if not test_opencv_import():
        print("💥 OpenCV未安装，无法继续测试")
        sys.exit(1)
    
    # 2. 检查媒体目录
    if not check_media_directory():
        print("💥 媒体目录问题，无法继续测试")
        sys.exit(1)
    
    # 3. 测试缩略图生成
    success = test_thumbnail_generation()
    
    if success:
        print("\n🎉 所有测试通过！")
        print("📱 现在可以访问 http://localhost:8001/video/video_list/ 查看缩略图")
    else:
        print("\n💥 测试失败，请检查错误信息")
    
    print("=" * 60)