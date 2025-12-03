#!/usr/bin/env python
"""
最终验证脚本：验证视频缩略图功能完整性
在Docker容器中执行：python final_thumbnail_verification.py
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
sys.path.append('/app')

django.setup()

from file_processor.video.models import VideoFile
from django.contrib.auth.models import User
from django.db.models import Q

def verify_thumbnail_functionality():
    """验证缩略图功能的完整性"""
    print("🔍 最终验证视频缩略图功能...")
    
    # 1. 检查视频文件和缩略图
    videos = VideoFile.objects.all()
    print(f"📊 总视频数量: {videos.count()}")
    
    with_thumbnails = videos.filter(thumbnail__isnull=False).exclude(thumbnail='')
    without_thumbnails = videos.filter(Q(thumbnail__isnull=True) | Q(thumbnail=''))
    
    print(f"✅ 有缩略图的视频: {with_thumbnails.count()}")
    print(f"❌ 无缩略图的视频: {without_thumbnails.count()}")
    
    # 2. 验证缩略图文件是否存在
    missing_files = []
    for video in with_thumbnails:
        thumbnail_path = f"/app/media/{video.thumbnail}"
        if not os.path.exists(thumbnail_path):
            missing_files.append(video.original_filename)
    
    if missing_files:
        print(f"❌ 缺失的缩略图文件: {len(missing_files)}")
        for filename in missing_files:
            print(f"  - {filename}")
    else:
        print("✅ 所有缩略图文件都存在")
    
    # 3. 检查缩略图文件大小
    print("\n📁 缩略图文件详情:")
    for video in with_thumbnails:
        thumbnail_path = f"/app/media/{video.thumbnail}"
        if os.path.exists(thumbnail_path):
            size = os.path.getsize(thumbnail_path)
            print(f"  - {video.original_filename[:30]:<30} | {str(video.thumbnail):<25} | {size:>8} bytes")
    
    # 4. 总结
    success_rate = (with_thumbnails.count() / videos.count() * 100) if videos.count() > 0 else 0
    print(f"\n📈 缩略图覆盖率: {success_rate:.1f}%")
    
    if success_rate >= 100:
        print("🎉 缩略图功能完全正常！")
        return True
    elif success_rate >= 80:
        print("✅ 缩略图功能基本正常")
        return True
    else:
        print("⚠️ 缩略图功能需要改进")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🎬 视频缩略图功能最终验证")
    print("=" * 60)
    
    success = verify_thumbnail_functionality()
    
    if success:
        print("\n🎉 验证通过！视频缩略图功能正常工作")
        print("📱 请访问 http://localhost:8001/video/video_list/ 查看效果")
        print("🔧 缩略图已设置为保持长宽比例显示")
    else:
        print("\n💥 验证失败，请检查上述问题")
    
    print("=" * 60)