from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db import transaction
from .models import FileHeader, FileDetail, ImageAnalysis, AnalysisResult
from .forms import PDFUploadForm, CustomUserCreationForm, ImageSelectionForm
from .services import DifyAPIService
import fitz  # PyMuPDF
import os
from django.conf import settings
import threading
from django.core.paginator import Paginator

def home(request):
    return render(request, 'file_processor/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
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
            return redirect('file_detail', pk=file_header.pk)
    else:
        form = PDFUploadForm()
    
    return render(request, 'file_processor/upload.html', {'form': form})

@login_required
def file_detail(request, pk):
    conversion = get_object_or_404(FileHeader, pk=pk)
    if not request.user.is_superuser and conversion.user != request.user:
        messages.error(request, 'You can only view your own conversions.')
        return redirect('file_list')
    
    images = conversion.images.all()
    return render(request, 'file_processor/file_detail.html', {
        'conversion': conversion,
        'images': images
    })

@login_required
def file_list(request):
    if request.user.is_superuser:
        conversions = FileHeader.objects.all()
    else:
        conversions = FileHeader.objects.filter(user=request.user)
    
    # 分页，每页显示10条记录
    paginator = Paginator(conversions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'file_processor/file_list.html', {'page_obj': page_obj})


@login_required
def file_detail_partial(request, pk):
    """返回文件详情的局部HTML，用于AJAX加载"""
    conversion = get_object_or_404(FileHeader, pk=pk)
    if not request.user.is_superuser and conversion.user != request.user:
        return JsonResponse({'error': 'You can only view your own conversions.'}, status=403)
    
    # 获取相关的图片
    images = conversion.images.all()
    
    # 渲染局部模板
    html = render_to_string('file_processor/file_detail_partial.html', {
        'conversion': conversion,
        'images': images
    }, request=request)
    
    return JsonResponse({'html': html})

@login_required
def image_analysis(request):
    if request.method == 'POST':
        form = ImageSelectionForm(request.user, request.POST)
        if form.is_valid():
            selected_images = form.cleaned_data['selected_images']
            
            # Create analysis record
            analysis = ImageAnalysis.objects.create(user=request.user)
            analysis.images.set(selected_images)
            
            # Start analysis in background
            dify_service = DifyAPIService()
            thread = threading.Thread(target=dify_service.analyze_images, args=(analysis.id,))
            thread.start()
            
            messages.success(request, f'Analysis started for {selected_images.count()} images!')
            return redirect('analysis_detail', pk=analysis.pk)
    else:
        form = ImageSelectionForm(request.user)
    
    return render(request, 'file_processor/image_analysis.html', {'form': form})

@login_required
def analysis_detail(request, pk):
    analysis = get_object_or_404(ImageAnalysis, pk=pk)
    if not request.user.is_superuser and analysis.user != request.user:
        messages.error(request, 'You can only view your own analyses.')
        return redirect('analysis_list')
    
    results = analysis.results.all()
    return render(request, 'file_processor/analysis_detail.html', {
        'analysis': analysis,
        'results': results
    })

@login_required
def analysis_list(request):
    if request.user.is_superuser:
        analyses = ImageAnalysis.objects.all()
    else:
        analyses = ImageAnalysis.objects.filter(user=request.user)
    return render(request, 'file_processor/analysis_list.html', {'analyses': analyses})

@login_required
def analyze_image(request):
    """分析单个图像"""
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
            
            # 更新状态为处理中
            image.status = 'processing'
            image.save()
            
            # 调用AI服务进行分析
            dify_service = DifyAPIService()
            result_data = dify_service.analyze_single_image(image)
            
            # 更新结果数据和状态
            image.result_data = result_data
            image.status = 'completed'
            image.save()
            
            return JsonResponse({
                'status': 'success',
                'result_data': result_data
            })
        except Exception as e:
            # 更新状态为失败
            if 'image' in locals():
                image.status = 'failed'
                image.save()
            
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def convert_pdf_to_images(pdf_conversion):
    """Convert PDF to PNG images"""
    try:
        pdf_conversion.status = 'processing'
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
        pdf_conversion.status = 'completed'
        pdf_conversion.save()
        
    except Exception as e:
        pdf_conversion.status = 'failed'
        pdf_conversion.save()
        print(f"Conversion failed: {str(e)}")
