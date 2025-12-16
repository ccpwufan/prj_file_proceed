import json
import os
import logging
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
from .models import VideoFile, VideoAnalysis, VideoDetectionFrame
from .forms import VideoUploadForm, VideoAnalysisForm
from .services.video_services import VideoProcessor, generate_thumbnail
from .services.camera_service import CameraService
from file_processor.queue.manager import queue_manager

# Configure logging
logger = logging.getLogger(__name__)


@login_required
def video_home(request):
    """Video module home page - redirect to main home with video option"""
    return redirect('file_processor:home')


@login_required
def test_camera_system(request):
    """Test camera detection system page"""
    return render(request, 'file_processor/video/test_camera_detection.html')


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
                # Queue system unavailable - show error only
                messages.error(request, f'Queue system is currently unavailable. Please try again later. Error: {e}')
            
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


@csrf_exempt
@require_POST
def capture_snapshot(request):
    """
    Save snapshot from camera detection
    
    Expected JSON payload:
    {
        "image": "base64_image_data",
        "detections": [...],
        "timestamp": "timestamp",
        "detection_time": "detection_time",
        "frame_count": "frame_count"
    }
    """
    try:
        camera_service = CameraService()
        
        # Get data from request
        data = json.loads(request.body)
        
        # Extract image data and create detection_data for the service
        image_data = data.get('image', '')
        
        # Create metadata from the flattened data structure
        detection_data = {
            'detections': data.get('detections', []),
            'detection_type': data.get('detection_type', 'barcode'),
            'threshold': data.get('threshold', 0.5),
            'time': data.get('time', 0)
        }

                
        # Decode base64 image data
        import base64
        if image_data.startswith('data:image/'):
            # Remove data URL prefix
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Create or get camera analysis session
        analysis = camera_service.create_camera_analysis(
                    user=request.user,
                    title=f"Camera Detection Session {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    detection_types=[detection_data.get('detection_type', 'barcode')],
                    status='completed'
                )
        
        # Save snapshot with proper parameters
        snapshot_result = camera_service.save_detection_snapshot(
            analysis_id=analysis.id,
            image_data=image_bytes,
            detection_data=detection_data
        )
        
        if 'error' in snapshot_result:
            return JsonResponse({
                'success': False,
                'message': snapshot_result['error']
            }, status=400)
        else:
            return JsonResponse({
                'success': True,
                'message': 'Snapshot saved successfully',
                'snapshot_id': snapshot_result.get('snapshot_id'),
                'frame_number': snapshot_result.get('frame_number'),
                'detection_count': snapshot_result.get('detection_count', 0)
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in capture_snapshot: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)





@login_required
def get_detection_history(request):
    """Get camera detection history"""
    try:
        camera_service = CameraService()
        detection_history = camera_service.get_detection_history()
        
        return JsonResponse({
            'success': True,
            'data': detection_history
        })
        
    except Exception as e:
        logger.error(f"Error in get_detection_history: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)





@csrf_exempt
@require_POST
def re_detect(request):
    """
    Re-detect specified video frame
    Expected JSON payload: {"frame_id": 123}
    """
    try:
        camera_service = CameraService()
        data = json.loads(request.body)
        
        frame_id = data.get('frame_id')
        if not frame_id:
            return JsonResponse({
                'success': False,
                'message': 'frame_id is required'
            }, status=400)
        
        re_detection_result = camera_service.re_detect(frame_id)
        
        if re_detection_result:
            return JsonResponse({
                'success': True,
                'message': 'Re-detection completed successfully',
                'data': re_detection_result
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Re-detection failed'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in re_detect: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


def get_video_list_data(request):
    """AJAX endpoint to get paginated video data"""
    user = request.user
    
    # Get parameters
    page = request.GET.get('page', 1)
    page_size = request.GET.get('pageSize', 8)
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
    # Debug: Print user info and count
    print(f"DEBUG: Current user: {request.user.username} (ID: {request.user.id})")
    
    # Get analyses with debug info (show all users' analyses)
    analyses = VideoAnalysis.objects.all().select_related('video_file')
    print(f"DEBUG: Found {analyses.count()} total analyses (all users)")
    
    # Debug: Print all analyses in database
    all_analyses = VideoAnalysis.objects.all()
    print(f"DEBUG: Total analyses in database: {all_analyses.count()}")
    for analysis in all_analyses:
        print(f"  Analysis ID: {analysis.id}, User: {analysis.user.username if analysis.user else 'None'}, Video: {analysis.video_file}")
    
    # Serialize for JavaScript with error handling
    analyses_data = []
    for analysis in analyses:
        try:
            # Handle camera analysis (no video_file) vs file analysis
            video_file_info = {
                'id': None,  # Camera analysis has no video file
                'original_filename': 'Camera Snapshot',
                'file_size': 0,
                'thumbnail': None,
            }
            
            if analysis.video_file:
                video_file_info = {
                    'id': analysis.video_file.id,
                    'original_filename': analysis.video_file.original_filename,
                    'file_size': analysis.video_file.file_size or 0,
                    'thumbnail': analysis.video_file.thumbnail.url if analysis.video_file.thumbnail else None,
                }
            
            # Handle result_summary parsing
            result_summary_data = analysis.result_summary
            if isinstance(result_summary_data, str):
                try:
                    result_summary_data = json.loads(result_summary_data)
                except:
                    result_summary_data = {'raw': result_summary_data}
            
            analyses_data.append({
                'id': analysis.id,
                'video_file': video_file_info,
                'analysis_type': analysis.analysis_type,
                'detection_type': analysis.detection_type or 'unknown',
                'result_summary': result_summary_data or {},
                'user': {
                    'id': analysis.user.id if analysis.user else None,
                    'username': analysis.user.username if analysis.user else 'Unknown'
                },
                'created_at': analysis.created_at.isoformat(),
                'completed_at': analysis.completed_at.isoformat() if analysis.completed_at else None,
                'status': analysis.status,
                'total_frames_processed': analysis.total_frames_processed or 0,
                'total_detections': analysis.total_detections or 0,
            })
        except Exception as e:
            print(f"Error serializing analysis {analysis.id}: {e}")
            continue
    
    print(f"DEBUG: Serialized {len(analyses_data)} analyses")
    
    return render(request, 'file_processor/video/video_analysis_history.html', {
        'video_files': VideoFile.objects.all(),
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
    try:
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
        except VideoAnalysis.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Analysis {analysis_id} not found or access denied'})
        
        # Delete associated detection frame files
        for frame in analysis.detection_frames.all():
            if frame.frame_image and os.path.exists(frame.frame_image.path):
                try:
                    os.remove(frame.frame_image.path)
                except OSError as e:
                    logger.warning(f"Failed to delete frame image {frame.frame_image.path}: {e}")
        
        # Delete analysis record (cascade will delete related detection frames)
        analysis.delete()
        
        return JsonResponse({'success': True, 'message': 'Analysis deleted successfully!'})
        
    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {e}")
        return JsonResponse({'success': False, 'message': str(e)})


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


@login_required
def get_analysis_details(request, analysis_id):
    """Get analysis details for modal display"""
    analysis = get_object_or_404(VideoAnalysis, id=analysis_id, user=request.user)
    detection_frames = analysis.detection_frames.all().order_by('frame_number')
    
    # Prepare data for the template
    frames_data = []
    for frame in detection_frames:
        # Convert detection_data to JSON string for pretty display
        detection_data_json = json.dumps(frame.detection_data, indent=2, ensure_ascii=False) if frame.detection_data else None
        
        frames_data.append({
            'id': frame.id,
            'frame_number': frame.frame_number,
            'frame_image_url': frame.frame_image.url if frame.frame_image else None,
            'detection_data': detection_data_json,
            'detection_type': frame.detection_type,
            'processing_time': frame.processing_time,
            'timestamp': frame.timestamp,
            'created_at': frame.created_at,
        })
    
    # Render the partial template
    return render(request, 'file_processor/video/video_analysis_partial.html', {
        'analysis': analysis,
        'frames_data': frames_data,
    })


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


