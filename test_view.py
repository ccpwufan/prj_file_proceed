import os, django, sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prj_file_proceed.settings')
django.setup()

from file_processor.models import FileHeader
from django.contrib.auth.models import User
from django.test import RequestFactory
from file_processor.views import result_detail

# 获取测试数据
user = User.objects.filter(username='testuser').first()
file_header = FileHeader.objects.filter(result_data__isnull=False).exclude(result_data='').first()

if user and file_header:
    print(f'测试用户: {user.username}')
    print(f'文件: {file_header.file_header_filename.name}')
    print(f'result_data长度: {len(file_header.result_data or "")}')
    
    # 创建请求
    factory = RequestFactory()
    request = factory.get(f'/result/detail/{file_header.pk}/')
    request.user = user
    
    try:
        response = result_detail(request, file_header.pk)
        print(f'响应状态: {response.status_code}')
        if response.status_code == 200:
            print('✅ 视图函数测试成功')
        elif response.status_code == 302:
            print(f'ℹ️ 重定向到: {response.url}')
            print('✅ 视图函数正常工作（需要登录）')
        else:
            print(f'❌ 视图函数返回错误状态: {response.status_code}')
    except Exception as e:
        print(f'❌ 视图函数测试失败: {e}')
        import traceback
        traceback.print_exc()
else:
    print('❌ 没有找到测试数据')