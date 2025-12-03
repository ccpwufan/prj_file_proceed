#!/usr/bin/env python
"""
测试视频删除功能的API响应
在Docker容器中执行：python test_delete_function.py
"""
import os
import sys
import django
import json

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
sys.path.append('/app')

django.setup()

from django.test import Client
from django.contrib.auth.models import User
from file_processor.video.models import VideoFile

def test_delete_api():
    """测试删除API的JSON响应"""
    print("🧪 测试视频删除API响应...")
    
    # 获取测试用户
    user = User.objects.first()
    if not user:
        print("❌ 没有找到测试用户")
        return False
    
    # 获取测试视频
    video = VideoFile.objects.first()
    if not video:
        print("❌ 没有找到测试视频")
        return False
    
    print(f"✅ 找到测试用户: {user.username}")
    print(f"✅ 找到测试视频: {video.original_filename} (ID: {video.id})")
    
    # 创建测试客户端
    client = Client()
    client.force_login(user)
    
    # 测试删除API
    print(f"🔧 测试删除视频 ID: {video.id}")
    
    try:
        # 获取CSRF token
        client.get('/video/video_list/')  # 先访问页面获取CSRF token
        csrf_token = client.cookies['csrftoken'].value if 'csrftoken' in client.cookies else ''
        
        response = client.post(
            f'/video/delete-video/{video.id}/',
            HTTP_X_CSRFTOKEN=csrf_token,
            content_type='application/json'
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📊 响应内容类型: {response.get('Content-Type')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ JSON响应: {data}")
                
                if data.get('success'):
                    print("✅ 删除成功!")
                    
                    # 验证视频确实被删除
                    remaining_videos = VideoFile.objects.filter(id=video.id).count()
                    if remaining_videos == 0:
                        print("✅ 视频已从数据库中删除")
                        return True
                    else:
                        print("❌ 视频仍然存在于数据库中")
                        return False
                else:
                    print(f"❌ 删除失败: {data.get('message')}")
                    return False
                    
            except json.JSONDecodeError:
                print(f"❌ 响应不是有效的JSON: {response.content}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"❌ 响应内容: {response.content}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🗑️ 视频删除功能测试")
    print("=" * 60)
    
    success = test_delete_api()
    
    if success:
        print("\n🎉 删除功能测试通过！")
        print("📱 现在前端删除视频后应该能正确更新页面")
    else:
        print("\n💥 删除功能测试失败")
    
    print("=" * 60)