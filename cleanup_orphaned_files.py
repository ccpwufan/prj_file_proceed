#!/usr/bin/env python
"""
清理脚本：删除videos、original和converted文件夹中在数据库里面没有记录的文件
"""

import os
import django
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.video.models import VideoFile


def get_all_database_files():
    """获取数据库中所有记录的文件路径"""
    db_files = set()
    
    # 获取所有video_file字段
    for video in VideoFile.objects.all():
        if video.video_file:
            db_files.add(video.video_file.path)
    
    # 获取所有original_file字段
    for video in VideoFile.objects.all():
        if video.original_file:
            db_files.add(video.original_file.path)
    
    # 获取所有converted_file字段
    for video in VideoFile.objects.all():
        if video.converted_file:
            db_files.add(video.converted_file.path)
    
    # 获取所有thumbnail字段
    for video in VideoFile.objects.all():
        if video.thumbnail:
            db_files.add(video.thumbnail.path)
    
    return db_files


def scan_directory_files(directory_path):
    """扫描目录中的所有文件"""
    files = set()
    if os.path.exists(directory_path):
        for root, dirs, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                files.add(file_path)
    return files


def cleanup_orphaned_files(dry_run=True):
    """清理孤立文件"""
    print("开始清理孤立文件...")
    
    # 获取数据库中的所有文件路径
    db_files = get_all_database_files()
    print(f"数据库中共有 {len(db_files)} 个文件记录")
    
    # 定义要扫描的目录
    media_root = 'media'
    directories_to_scan = [
        os.path.join(media_root, 'videos'),
        os.path.join(media_root, 'videos', 'original'),
        os.path.join(media_root, 'videos', 'converted'),
        os.path.join(media_root, 'video_thumbnails'),  # 也清理缩略图
    ]
    
    total_deleted = 0
    total_size_freed = 0
    
    for directory in directories_to_scan:
        print(f"\n扫描目录: {directory}")
        
        if not os.path.exists(directory):
            print(f"  目录不存在: {directory}")
            continue
        
        # 扫描目录中的所有文件
        fs_files = scan_directory_files(directory)
        print(f"  目录中共有 {len(fs_files)} 个文件")
        
        # 找出不在数据库中的文件
        orphaned_files = fs_files - db_files
        
        if not orphaned_files:
            print(f"  没有发现孤立文件")
            continue
        
        print(f"  发现 {len(orphaned_files)} 个孤立文件:")
        
        # 删除孤立文件
        for file_path in orphaned_files:
            try:
                file_size = os.path.getsize(file_path)
                if dry_run:
                    print(f"    [DRY RUN] 将删除: {file_path} ({file_size} bytes)")
                else:
                    os.remove(file_path)
                    print(f"    已删除: {file_path} ({file_size} bytes)")
                
                total_deleted += 1
                total_size_freed += file_size
                
            except OSError as e:
                print(f"    删除失败 {file_path}: {e}")
    
    # 输出统计信息
    print(f"\n{'='*50}")
    if dry_run:
        print(f"[DRY RUN] 模拟完成")
    else:
        print(f"清理完成")
    
    print(f"总删除文件数: {total_deleted}")
    print(f"总释放空间: {total_size_freed / (1024*1024):.2f} MB")
    
    return total_deleted, total_size_freed


def interactive_cleanup():
    """交互式清理"""
    print("视频文件清理工具")
    print("="*50)
    
    # 先执行一次dry run
    print("\n1. 预览模式 (Dry Run) - 不会真正删除文件:")
    deleted, size = cleanup_orphaned_files(dry_run=True)
    
    if deleted == 0:
        print("\n没有发现需要清理的文件。")
        return
    
    # 询问用户是否确认删除
    print(f"\n2. 确认删除:")
    print(f"即将删除 {deleted} 个文件，释放 {size / (1024*1024):.2f} MB 空间")
    
    confirm = input("\n确认删除这些文件吗? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y', '是']:
        print("\n执行实际删除...")
        cleanup_orphaned_files(dry_run=False)
    else:
        print("操作已取消。")


if __name__ == '__main__':
    # 检查是否在Docker环境中运行
    if not os.path.exists('/app'):
        print("警告: 此脚本应该在Docker容器中运行")
        print("如果要在本地运行，请确保Django设置正确")
    
    interactive_cleanup()