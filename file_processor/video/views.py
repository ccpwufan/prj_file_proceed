import json
import threading
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
from .services import VideoProcessor, generate_thumbnail
from file_processor.queue.manager import queue_manager


@login_required
def video_home(request):
    """Video module home page - redirect to main home with video option"""
    return redirect('file_processor:home')


@login_required
def video_upload(request):
    """Handle video file upload with queue-based conversion"""
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Create video file record
            video_file = form.save(commit=False)
            video_file.user = request.user
            video_file.original_filename = request.FILES['video_file'].name
            video_file.status = 'uploaded'  # Set status to uploaded (will be processed by queue)
            video_file.save()
            
            try:
                # Add video conversion task to queue
                task = queue_manager.add_task(
                    task_name=f"Convert video: {video_file.original_filename}",
                    task_type='video_conversion',
                    task_params={'video_file_id': video_file.id},
                    user=request.user,
                    priority=0,  # Default priority
                    max_retries=3
                )
                
                messages.success(request, f'Video "{video_file.original_filename}" uploaded successfully! It has been added to the conversion queue (Task #{task.id}).')
                
            except Exception as e:
                # If queue fails, fallback to immediate processing
                messages.warning(request, f'Queue system unavailable, processing immediately. Error: {e}')
                
                # Fallback to old method
                def process_video_background():
                    try:
                        processor = VideoProcessor()
                        success = processor.process_uploaded_video(video_file)
                        
                        if success:
                            try:
                                thumbnail_path = generate_thumbnail(video_file.video_file.path)
                                if thumbnail_path:
                                    video_file.thumbnail.name = thumbnail_path.replace('media/', '')
                                video_file.status = 'processed'
                            except Exception as e:
                                print(f"Thumbnail generation failed: {e}")
                                video_file.status = 'processed'
                        else:
                            video_file.status = 'failed'
                        
                        video_file.save()
                        
                    except Exception as e:
                        print(f"Video processing failed: {e}")
                        video_file.status = 'failed'
                        video_file.save()
                
                # Start background processing as fallback
                thread = threading.Thread(target=process_video_background)
                thread.daemon = True
                thread.start()
                
                messages.info(request, f'Video processing started in background due to queue unavailability.')
            
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
    total_size_bytes = sum(video.file_size or 0 for video in video_files)
    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)  # Convert to MB and round to 2 decimal places
    
    # Get first page of data for initial load
    page = 1
    page_size = 8
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
            'video_url': video_file.video_file.url if video_file.video_file else None,
            'conversion_status': video_file.conversion_status,
            'conversion_progress': video_file.conversion_progress,
            'is_web_compatible': video_file.is_web_compatible,
            'conversion_error': video_file.conversion_error,
            'original_format': video_file.original_format,
            'converted_format': video_file.converted_format,
        })
    
    return render(request, 'file_processor/video/video_list.html', {
        'video_files': json.dumps(video_files_data),
        'statistics': json.dumps({
            'totalVideos': total_videos,
            'processedVideos': processed_videos,
            'processingVideos': processing_videos,
            'totalSize': total_size_mb,
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
            'video_url': video_file.video_file.url if video_file.video_file else None,
            'conversion_status': video_file.conversion_status,
            'conversion_progress': video_file.conversion_progress,
            'is_web_compatible': video_file.is_web_compatible,
            'conversion_error': video_file.conversion_error,
            'original_format': video_file.original_format,
            'converted_format': video_file.converted_format,
        })
    
    # Calculate total size in MB
    user_videos = VideoFile.objects.filter(user=user)
    total_size_bytes = sum(video.file_size or 0 for video in user_videos)
    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
    
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
            'totalVideos': user_videos.count(),
            'processedVideos': user_videos.filter(status='processed').count(),
            'processingVideos': user_videos.filter(status='processing').count(),
            'totalSize': total_size_mb,
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
    """Delete a video file and all associated files"""
    import os
    from django.conf import settings
    
    video_file = get_object_or_404(VideoFile, id=video_file_id, user=request.user)
    
    try:
        # 1. Delete physical files
        files_to_delete = [
            video_file.video_file,
            video_file.original_file, 
            video_file.converted_file,
            video_file.thumbnail
        ]
        
        for file_field in files_to_delete:
            if file_field and os.path.exists(file_field.path):
                try:
                    os.remove(file_field.path)
                    # Also remove the directory if it becomes empty
                    dir_path = os.path.dirname(file_field.path)
                    if os.path.exists(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except OSError as e:
                    print(f"Warning: Could not delete file {file_field.path}: {e}")
        
        # 2. Delete detection frame images
        for analysis in video_file.analyses.all():
            for frame in analysis.detection_frames.all():
                if frame.frame_image and os.path.exists(frame.frame_image.path):
                    try:
                        os.remove(frame.frame_image.path)
                    except OSError as e:
                        print(f"Warning: Could not delete frame image {frame.frame_image.path}: {e}")
        
        # 3. Delete database record (cascade will handle related records)
        video_file.delete()
        
        return JsonResponse({'success': True, 'message': 'Video file and all associated files deleted successfully!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
@login_required
def delete_analysis(request, analysis_id):
    """Delete a video analysis"""
    analysis = get_object_or_404(VideoAnalysis, id=analysis_id, user=request.user)
    analysis.delete()
    messages.success(request, 'Analysis deleted successfully!')


@login_required
def video_conversion_status(request, video_file_id):
    """Get conversion status for a specific video file"""
    video_file = get_object_or_404(VideoFile, id=video_file_id, user=request.user)
    
    return JsonResponse({
        'conversion_status': video_file.conversion_status,
        'conversion_progress': video_file.conversion_progress,
        'is_web_compatible': video_file.is_web_compatible,
        'conversion_error': video_file.conversion_error,
        'status': video_file.status,
        'original_format': video_file.original_format,
        'converted_format': video_file.converted_format,
    })
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