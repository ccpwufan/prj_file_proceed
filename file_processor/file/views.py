from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
from django.db.models import Case, When, Value, CharField
from .models import FileHeader, FileDetail, FileAnalysis
from .forms import PDFUploadForm, CustomUserCreationForm
from .services import DifyAPIService
import fitz  # PyMuPDF
import os
from django.conf import settings
import threading
from django.core.paginator import Paginator
from datetime import datetime

def append_log(file_header, message):
    """Append timestamped message to file_header log field"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"

    # Get current log or start with empty string
    current_log = file_header.log or ""
    file_header.log = current_log + log_entry
    file_header.save()

def home(request):
    return render(request, 'file_processor/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('file:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_header = form.save(commit=False)
            file_header.user = request.user
            # 设置文件类型
            if file_header.file_header_filename:
                file_header.file_type = file_header.file_header_filename.name.split('.')[-1].lower()
            file_header.save()
            # Start conversion in background
            thread = threading.Thread(target=convert_pdf_to_images, args=(file_header,))
            thread.start()
            messages.success(request, 'PDF uploaded and conversion started!')
            return redirect(f"{reverse('file:file_list')}?selected_file={file_header.pk}")
    else:
        form = PDFUploadForm()
    
    return render(request, 'file_processor/file/upload.html', {'form': form})

@login_required
def file_detail(request, pk):
    conversion = get_object_or_404(FileHeader, pk=pk)
    if not request.user.is_superuser and conversion.user != request.user:
        messages.error(request, 'You can only view your own conversions.')
        return redirect('file:file_list')
    
    images = conversion.images.all()
    return render(request, 'file_processor/file/file_detail.html', {
        'conversion': conversion,
        'images': images
    })

@login_required
def file_list(request):
    if request.user.is_superuser:
        conversions = FileHeader.objects.all()
    else:
        conversions = FileHeader.objects.filter(user=request.user)
    
    # 添加comments字段的模糊查询功能
    search_query = request.GET.get('search', '')
    if search_query:
        conversions = conversions.filter(comments__icontains=search_query)
    
    # 分页，每页显示10条记录
    paginator = Paginator(conversions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'file_processor/file/file_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })


@login_required
def file_detail_partial(request, pk):
    """返回文件详情的局部HTML，用于AJAX加载"""
    conversion = get_object_or_404(FileHeader, pk=pk)
    if not request.user.is_superuser and conversion.user != request.user:
        return JsonResponse({'error': 'You can only view your own conversions.'}, status=403)
    
    # 获取相关的图片
    images = conversion.images.all()
    
    # 获取最近一次FileAnalysis的created_at时间
    latest_analysis = conversion.header_analyses.order_by('-created_at').first()
    latest_analysis_time = latest_analysis.created_at if latest_analysis else None
    
    # 渲染局部模板
    html = render_to_string('file_processor/file/file_detail_partial.html', {
        'conversion': conversion,
        'images': images,
        'latest_analysis_time': latest_analysis_time
    }, request=request)
    
    return JsonResponse({'html': html})





@login_required
def analysis_list(request):
    if request.user.is_superuser:
        analyses = FileAnalysis.objects.all()
    else:
        analyses = FileAnalysis.objects.filter(user=request.user)
    
    # 处理排序参数
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = ['created_at', '-created_at', 'status', '-status', 'analysis_type', '-analysis_type', 'user__username', '-user__username', 'rate', '-rate', 'file_header__comments', '-file_header__comments']
    
    # 检查是否是按文件名排序
    if sort_by == 'file_name' or sort_by == '-file_name':
        # 使用 annotate 添加文件名字段用于排序
        analyses = analyses.annotate(
            file_name=Case(
                When(analysis_type='header', then='file_header__file_header_filename'),
                When(analysis_type='single', then='file_detail__file_header__file_header_filename'),
                default=Value(''),
                output_field=CharField()
            )
        )
        
        if sort_by == 'file_name':
            analyses = analyses.order_by('file_name')
        else:
            analyses = analyses.order_by('-file_name')
    elif sort_by in valid_sort_fields:
        analyses = analyses.order_by(sort_by)
    else:
        analyses = analyses.order_by('-created_at')
    
    # 分页，每页显示10条记录
    paginator = Paginator(analyses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'file_processor/file/analysis_list.html', {
        'page_obj': page_obj,
        'current_sort': sort_by
    })


def get_file_name_for_analysis(analysis):
    """
    获取分析记录对应的文件名，用于排序
    """
    if analysis.analysis_type == 'header' and analysis.file_header:
        return analysis.file_header.file_header_filename.name
    elif analysis.analysis_type == 'single' and analysis.file_detail:
        return analysis.file_detail.file_header.file_header_filename.name
    else:
        return ""  # 如果无法确定文件名，则返回空字符串

@login_required
def analyze_single_file(request):
    """分析单个文件"""
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
        try:
            import json
            data = json.loads(request.body)
            image_id = data.get('image_id')
            
            # 获取图像对象
            image = get_object_or_404(FileDetail, id=image_id)
            
            # 检查权限
            if not request.user.is_superuser and image.file_header.user != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # 创建新的FileAnalysis记录
            analysis = FileAnalysis.objects.create(
                user=request.user,
                file_detail=image,
                analysis_type='single',
                status='processing',
                api_key_used=settings.DIFY_API_KEY
            )
            
            # 清除已有的result_data
            image.result_data = None
            # 更新状态为处理中
            image.save()
            
            # 调用AI服务进行分析
            dify_service = DifyAPIService()
            result_data = dify_service.analyze_single_image(image)
            
            # 更新分析记录
            if 'error' not in result_data:
                analysis.status = 'completed'
                analysis.result_data = str(result_data)
                analysis.save()
                
                # 更新结果数据和状态
                image.result_data = {
                    'status': 'success',
                    'result_data': result_data
                }
                image.status = 'completed'
                image.save()
                
                return JsonResponse({
                    'status': 'success',
                    'analysis_id': analysis.id,
                    'result_data': result_data
                })
            else:
                analysis.status = 'failed'
                analysis.result_data = str(result_data)
                analysis.save()
                
                image.status = 'failed'
                image.save()
                
                return JsonResponse({'error': result_data.get('error')}, status=500)
                
        except Exception as e:
            # 记录异常
            if 'analysis' in locals():
                analysis.status = 'failed'
                analysis.result_data = f"Exception: {str(e)}"
                analysis.save()
            
            # 更新状态为失败
            if 'image' in locals():
                # 组织错误信息存入result_data
                error_data = {
                    'error': str(e),
                    'status': 'failed',
                    'timestamp': timezone.now().isoformat()
                }
                image.result_data = error_data
                image.status = 'failed'
                image.save()
            
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def analyze_all_files(request, pk):
    """分析当前file_header的所有文件"""
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
        try:
            import json
            data = json.loads(request.body)
            
            # 获取file_header对象
            file_header = get_object_or_404(FileHeader, pk=pk)
            
            # 检查权限
            if not request.user.is_superuser and file_header.user != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # 获取所有相关的图片
            images = file_header.images.all()
            
            if not images.exists():
                return JsonResponse({'error': 'No images found for this file'}, status=400)
            
            # 创建新的FileAnalysis记录
            analysis = FileAnalysis.objects.create(
                user=request.user,
                file_header=file_header,
                analysis_type='header',
                status='processing',
                api_key_used=settings.DIFY_API_KEY_INVICE_FILES
            )
            
            # Set status to processing and clear existing log
            file_header.status = 'processing'
            file_header.log = ""
            file_header.save()
            append_log(file_header, f"Starting analysis for {len(images)} images")
            
            # 初始化DifyAPIService，使用指定的API KEY
            append_log(file_header, "Initializing Dify API service")
            dify_service = DifyAPIService(api_key=settings.DIFY_API_KEY_INVICE_FILES)
            
            # 上传所有图片并收集file_ids
            append_log(file_header, "Starting image upload process")
            file_ids = []
            for i, image in enumerate(images, 1):
                try:
                    file_id = dify_service.upload_image(image.file_detail_filename.path)
                    file_ids.append(file_id)
                    append_log(file_header, f"Uploaded image {i}/{len(images)}: Page {image.page_number}")
                except Exception as e:
                    append_log(file_header, f"Failed to upload image {i}/{len(images)}: Page {image.page_number} - {str(e)}")
                    raise
            
            append_log(file_header, f"All images uploaded successfully. Starting workflow analysis")
            
            # 调用run_workflow_files方法
            success, result_data, error_msg = dify_service.run_workflow_files(file_ids)
            
            if success:
                # 更新分析记录
                analysis.status = 'completed'
                analysis.result_data = result_data
                analysis.save()
                
                # 解析result_content（模仿result_detail函数的逻辑）
                result_content = result_data
                if '<think>' in result_data and '</think>' in result_data:
                    # Extract content between <think> tags
                    start_idx = result_data.find('<think>') + len('<think>')
                    end_idx = result_data.find('</think>', start_idx)
                    think_content = result_data[start_idx:end_idx].strip()
                    
                    # Remove think section from result content
                    result_content = result_data[:result_data.find('<think>')].strip()
                    if result_data.find('</think>') + len('</think>') < len(result_data):
                        result_content += result_data[result_data.find('</think>') + len('</think>'):].strip()
                
                # 从result_content中提取部门和姓名信息写入header.comments
                comments_parts = []
                if isinstance(result_content, str):
                    import re
                    
                # 更健壮的版本，处理关键词可能缺失的情况
                dept_match = re.search(r'(?:部门|dept)\s*[:：]?\s*([^,\n\r]+)', result_content, re.IGNORECASE)
                if dept_match:
                    department = dept_match.group(1).strip()
                    comments_parts.append(f"部门：{department}")

                name_match = re.search(r'(?:姓名|name)\s*[:：]?\s*([^,\n\r]+)', result_content, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1).strip()
                    comments_parts.append(f"姓名：{name}")
                
                # 更新file_header状态为completed，并保存result_data
                append_log(file_header, "Workflow analysis completed successfully")
                file_header.status = 'completed'
                # 将result_data转换为字符串存储
                file_header.result_data = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + result_data)
                
                # 将提取的信息保存到comments字段（存为一行，去掉换行符）
                if comments_parts:
                    file_header.comments = ", ".join(comments_parts)
                
                file_header.save()
                
                return JsonResponse({
                    'status': 'success',
                    'analysis_id': analysis.id,
                    'message': f'Successfully analyzed {len(images)} images',
                    'result_data': result_data
                })
            else:
                # 更新分析记录
                analysis.status = 'failed'
                analysis.result_data = f"Error: {error_msg}"
                analysis.save()
                
                # 更新file_header状态为failed，并保存错误信息
                append_log(file_header, f"Workflow analysis failed: {error_msg}")
                file_header.status = 'failed'
                file_header.result_data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + f"Error: {error_msg}"
                file_header.save()
                
                return JsonResponse({'error': error_msg}, status=500)
                
        except Exception as e:
            # 记录异常到分析记录
            if 'analysis' in locals():
                analysis.status = 'failed'
                analysis.result_data = f"Exception: {str(e)}"
                analysis.save()
            
            append_log(file_header if 'file_header' in locals() else get_object_or_404(FileHeader, pk=pk), f"Analysis failed with exception: {str(e)}")
            # 更新file_header状态为failed，并保存错误信息
            file_header.status = 'failed'
            file_header.result_data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")+": " + f"Analysis failed with exception:: {str(e)}"
            file_header.save()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_log(request, pk):
    """获取file_header的日志信息"""
    try:
        # 获取file_header对象
        file_header = get_object_or_404(FileHeader, pk=pk)
        
        # 检查权限
        if not request.user.is_superuser and file_header.user != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # 返回日志和状态
        return JsonResponse({
            'log': file_header.log or '',
            'status': file_header.status
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def delete_file(request, pk):
    """删除文件及其相关数据"""
    if request.method == 'POST':
        try:
            # 获取文件对象
            file_header = get_object_or_404(FileHeader, pk=pk)
            
            # 检查权限
            if not request.user.is_superuser and file_header.user != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # 删除相关的图片文件和记录
            images = FileDetail.objects.filter(file_header=file_header)
            for image in images:
                # 删除图片文件
                if image.file_detail_filename and os.path.exists(image.file_detail_filename.path):
                    os.remove(image.file_detail_filename.path)
            
            # 删除原始PDF文件
            if file_header.file_header_filename and os.path.exists(file_header.file_header_filename.path):
                os.remove(file_header.file_header_filename.path)
            
            # 删除数据库记录
            images.delete()  # 删除FileDetail记录
            file_header.delete()  # 删除FileHeader记录
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def convert_pdf_to_images(pdf_conversion):
    """Convert PDF to PNG images"""
    try:
        pdf_conversion.status = 'converting'
        pdf_conversion.save()
        
        # Open PDF file
        pdf_path = pdf_conversion.file_header_filename.path
        pdf_document = fitz.open(pdf_path)
        pdf_conversion.total_pages = len(pdf_document)
        pdf_conversion.save()
        
        # Convert each page to PNG
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            img_data = pix.tobytes("png")
            
            # Save image
            img_name = f"{os.path.splitext(os.path.basename(pdf_conversion.file_header_filename.name))[0]}_page_{page_num + 1}.png"
            img_path = os.path.join(settings.MEDIA_ROOT, 'images', img_name)
            
            # Ensure images directory exists
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            
            with open(img_path, 'wb') as f:
                f.write(img_data)
            
            # Create FileDetail record
            FileDetail.objects.create(
                file_header=pdf_conversion,
                file_detail_filename=f'images/{img_name}',
                page_number=page_num + 1
            )
        
        pdf_document.close()
        pdf_conversion.status = 'converted'
        pdf_conversion.save()
        
    except Exception as e:
        pdf_conversion.status = 'failed'
        pdf_conversion.save()
        print(f"Conversion failed: {str(e)}")

@login_required
def rate_analysis(request, pk):
    """处理分析记录评分"""
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
        try:
            import json
            data = json.loads(request.body)
            rating = data.get('rating')
            
            # 验证评分范围
            if not rating or not 1 <= rating <= 5:
                return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
            
            # 获取分析记录
            analysis = get_object_or_404(FileAnalysis, pk=pk)
            
            # 检查权限
            if not request.user.is_superuser and analysis.user != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # 保存评分
            analysis.rate = rating
            analysis.save()
            
            return JsonResponse({
                'status': 'success',
                'rating': rating,
                'message': 'Thank you for your rating!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def result_detail(request, pk):
    """Display result data with tabs for Result and Think sections"""
    analysis = get_object_or_404(FileAnalysis, pk=pk)
    
    # Check permission
    if not request.user.is_superuser and analysis.user != request.user:
        return redirect('file:login')
    
    result_data = analysis.result_data or ''
    
    # Debug: Print result_data info
    print(f"Result data length: {len(result_data)}")
    print(f"Has </think> tags: {'</think>' in result_data}")
    
    # Parse result_data to separate Think section
    think_content = ''
    result_content = result_data
    
    if '<think>' in result_data and '</think>' in result_data:
        # Extract content between <think> tags
        start_idx = result_data.find('<think>') + len('<think>')
        end_idx = result_data.find('</think>', start_idx)
        think_content = result_data[start_idx:end_idx].strip()
        
        # Remove think section from result content
        result_content = result_data[:result_data.find('<think>')].strip()
        if result_data.find('</think>') + len('</think>') < len(result_data):
            result_content += result_data[result_data.find('</think>') + len('</think>'):].strip()
    
    context = {
        'analysis': analysis,
        'result_content': result_content,
        'think_content': think_content,
        'log_content': analysis.log or '',
        'prompt_content': analysis.prompt or '',
    }
    
    return render(request, 'file_processor/file/result_detail.html', context)

@login_required
def test_pdf_access(request, pk):
    """Test PDF file access"""
    from django.http import HttpResponse, Http404
    import mimetypes
    
    file_header = get_object_or_404(FileHeader, pk=pk)
    
    # Check permission
    if not request.user.is_superuser and file_header.user != request.user:
        raise Http404("Permission denied")
    
    file_path = file_header.file_header_filename.path
    
    if not os.path.exists(file_path):
        raise Http404("File not found")
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    
    # Serve file
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=mime_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response
