import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import VideoFile, VideoAnalysis, VideoDetectionFrame
from .forms import VideoUploadForm, VideoAnalysisForm
from .services import VideoProcessingService, generate_thumbnail


@login_required
def video_home(request):
    """Video module home page - redirect to main home with video option"""
    return redirect('file_processor:home')


@login_required
def video_upload(request):
    """Handle video file upload"""
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video_file = form.save(commit=False)
            video_file.user = request.user
            video_file.original_filename = request.FILES['video_file'].name
            video_file.save()
            
            # Generate thumbnail after video upload
            try:
                thumbnail_path = generate_thumbnail(video_file.video_file.path)
                if thumbnail_path:
                    # Update thumbnail field relative to media root
                    video_file.thumbnail.name = thumbnail_path.replace('media/', '')
                    video_file.save()
                    messages.success(request, f'Video "{video_file.original_filename}" uploaded successfully with thumbnail!')
                else:
                    messages.warning(request, f'Video "{video_file.original_filename}" uploaded successfully, but thumbnail generation failed.')
            except Exception as e:
                messages.warning(request, f'Video "{video_file.original_filename}" uploaded successfully, but thumbnail generation failed: {str(e)}')
            
            return redirect('video:video_list')
    else:
        form = VideoUploadForm()
    
    return render(request, 'file_processor/video/upload.html', {'form': form})


@login_required
def camera_detection(request):
    """Camera detection page"""
    return render(request, 'file_processor/video/camera.html')


@login_required
def analyze_video(request, video_file_id):
    """Video analysis page"""
    video_file = get_object_or_404(VideoFile, id=video_file_id, user=request.user)
    
    if request.method == 'POST':
        form = VideoAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.video_file = video_file
            analysis.user = request.user
            analysis.save()
            
            messages.success(request, 'Video analysis started!')
            return redirect('video:analyze_camera', analysis_id=analysis.id)
    else:
        form = VideoAnalysisForm()
    
    # Get existing analyses
    analyses = video_file.analyses.all()
    
    return render(request, 'file_processor/video/video_analysis.html', {
        'video_file': video_file,
        'form': form,
        'analyses': analyses
    })


@login_required
def analyze_camera(request, analysis_id):
    """Display camera analysis results"""
    analysis = get_object_or_404(VideoAnalysis, id=analysis_id, user=request.user)
    detection_frames = analysis.detection_frames.all()
    
    # Serialize for JavaScript
    frames_data = []
    for frame in detection_frames:
        frames_data.append({
            'id': frame.id,
            'frame_number': frame.frame_number,
            'frame_image': frame.frame_image.url,
            'detection_data': frame.detection_data,
            'timestamp': frame.timestamp,
            'created_at': frame.created_at.isoformat(),
        })
    
    return render(request, 'file_processor/video/camera_analysis.html', {
        'analysis': analysis,
        'detection_frames': json.dumps(frames_data)
    })


@login_required
def video_list(request):
    """Video list page - display video files with server-side pagination"""
    # Handle AJAX requests for paginated data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return get_video_list_data(request)
    
    # Initial page load - get first page data and statistics
    video_files = VideoFile.objects.filter(user=request.user)
    
    # Get statistics
    total_videos = video_files.count()
    processed_videos = video_files.filter(status='processed').count()
    processing_videos = video_files.filter(status='processing').count()
    total_size = sum(video.file_size or 0 for video in video_files)
    
    # Get first page of data for initial load
    page = 1
    page_size = 9
    paginator = Paginator(video_files.order_by('-created_at'), page_size)
    
    try:
        video_files_page = paginator.page(page)
    except PageNotAnInteger:
        video_files_page = paginator.page(1)
    except EmptyPage:
        video_files_page = paginator.page(paginator.num_pages)
    
    # Serialize current page data
    video_files_data = []
    for video_file in video_files_page:
        video_files_data.append({
            'id': video_file.id,
            'original_filename': video_file.original_filename,
            'created_at': video_file.created_at.isoformat(),
            'duration': video_file.duration,
            'file_size': video_file.file_size,
            'resolution': video_file.resolution,
            'status': video_file.status,
            'thumbnail': video_file.thumbnail.url if video_file.thumbnail else None,
        })
    
    return render(request, 'file_processor/video/video_list.html', {
        'video_files': json.dumps(video_files_data),
        'statistics': json.dumps({
            'totalVideos': total_videos,
            'processedVideos': processed_videos,
            'processingVideos': processing_videos,
            'totalSize': total_size,
        })
    })


def get_video_list_data(request):
    """AJAX endpoint to get paginated video data"""
    user = request.user
    
    # Get parameters
    page = request.GET.get('page', 1)
    page_size = request.GET.get('pageSize', 9)
    search_query = request.GET.get('search', '')
    filter_status = request.GET.get('status', '')
    sort_field = request.GET.get('sortField', 'created_at')
    sort_order = request.GET.get('sortOrder', 'desc')
    
    try:
        page = int(page)
        page_size = int(page_size)
    except ValueError:
        page = 1
        page_size = 9
    
    # Build query
    video_files = VideoFile.objects.filter(user=user)
    
    # Apply search filter
    if search_query:
        video_files = video_files.filter(
            Q(original_filename__icontains=search_query)
        )
    
    # Apply status filter
    if filter_status:
        video_files = video_files.filter(status=filter_status)
    
    # Apply sorting
    sort_prefix = '-' if sort_order == 'desc' else ''
    if sort_field in ['original_filename', 'created_at', 'file_size', 'status']:
        video_files = video_files.order_by(f"{sort_prefix}{sort_field}")
    else:
        video_files = video_files.order_by('-created_at')
    
    # Paginate
    paginator = Paginator(video_files, page_size)
    
    try:
        video_files_page = paginator.page(page)
    except PageNotAnInteger:
        video_files_page = paginator.page(1)
    except EmptyPage:
        video_files_page = paginator.page(paginator.num_pages)
    
    # Serialize data
    video_files_data = []
    for video_file in video_files_page:
        video_files_data.append({
            'id': video_file.id,
            'original_filename': video_file.original_filename,
            'created_at': video_file.created_at.isoformat(),
            'duration': video_file.duration,
            'file_size': video_file.file_size,
            'resolution': video_file.resolution,
            'status': video_file.status,
            'thumbnail': video_file.thumbnail.url if video_file.thumbnail else None,
        })
    
    # Return JSON response
    return JsonResponse({
        'videos': video_files_data,
        'pagination': {
            'currentPage': page,
            'totalPages': paginator.num_pages,
            'totalItems': paginator.count,
            'hasNext': video_files_page.has_next(),
            'hasPrevious': video_files_page.has_previous(),
            'pageSize': page_size,
        },
        'statistics': {
            'totalVideos': VideoFile.objects.filter(user=user).count(),
            'processedVideos': VideoFile.objects.filter(user=user, status='processed').count(),
            'processingVideos': VideoFile.objects.filter(user=user, status='processing').count(),
            'totalSize': sum(video.file_size or 0 for video in VideoFile.objects.filter(user=user)),
        }
    })


@login_required
def video_analysis_history(request):
    """Video analysis history page"""
    video_files = VideoFile.objects.filter(user=request.user)
    analyses = VideoAnalysis.objects.filter(user=request.user).select_related('video_file')
    
    # Serialize for JavaScript
    analyses_data = []
    for analysis in analyses:
        analyses_data.append({
            'id': analysis.id,
            'video_file': {
                'id': analysis.video_file.id,
                'original_filename': analysis.video_file.original_filename,
                'file_size': analysis.video_file.file_size,
                'thumbnail': analysis.video_file.thumbnail.url if analysis.video_file.thumbnail else None,
            },
            'analysis_type': analysis.analysis_type,
            'created_at': analysis.created_at.isoformat(),
            'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None,
            'status': analysis.status,
            'total_frames_processed': analysis.total_frames_processed,
            'total_detections': analysis.total_detections,
        })
    
    return render(request, 'file_processor/video/video_analysis_history.html', {
        'video_files': video_files,
        'analyses': json.dumps(analyses_data)
    })


@require_POST
@login_required
def delete_video_file(request, video_file_id):
    """Delete a video file"""
    video_file = get_object_or_404(VideoFile, id=video_file_id, user=request.user)
    
    try:
        video_file.delete()
        return JsonResponse({'success': True, 'message': 'Video file deleted successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
@login_required
def delete_analysis(request, analysis_id):
    """Delete a video analysis"""
    analysis = get_object_or_404(VideoAnalysis, id=analysis_id, user=request.user)
    analysis.delete()
    messages.success(request, 'Analysis deleted successfully!')
    return redirect('video:video_analysis_history')


@require_POST
@login_required
def generate_video_thumbnail(request, video_file_id):
    """Generate thumbnail for an existing video file"""
    video_file = get_object_or_404(VideoFile, id=video_file_id, user=request.user)
    
    try:
        thumbnail_path = generate_thumbnail(video_file.video_file.path)
        if thumbnail_path:
            # Update thumbnail field relative to media root
            video_file.thumbnail.name = thumbnail_path.replace('media/', '')
            video_file.save()
            messages.success(request, f'Thumbnail generated successfully for "{video_file.original_filename}"!')
        else:
            messages.error(request, f'Failed to generate thumbnail for "{video_file.original_filename}"')
    except Exception as e:
        messages.error(request, f'Error generating thumbnail for "{video_file.original_filename}": {str(e)}')
    
    return redirect('video:video_list')


@require_POST
@login_required
def generate_all_thumbnails(request):
    """Generate thumbnails for all videos without thumbnails"""
    videos_without_thumbnails = VideoFile.objects.filter(user=request.user, thumbnail='')
    
    success_count = 0
    error_count = 0
    
    for video_file in videos_without_thumbnails:
        try:
            thumbnail_path = generate_thumbnail(video_file.video_file.path)
            if thumbnail_path:
                video_file.thumbnail.name = thumbnail_path.replace('media/', '')
                video_file.save()
                success_count += 1
            else:
                error_count += 1
        except Exception:
            error_count += 1
    
    if success_count > 0:
        messages.success(request, f'Successfully generated {success_count} thumbnail(s)!')
    if error_count > 0:
        messages.warning(request, f'Failed to generate {error_count} thumbnail(s).')
    
    return redirect('video:video_list')