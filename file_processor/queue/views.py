"""
Queue Management Views

This module provides views for managing and monitoring the task queue system.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db.models import Count, Q
from .models import TaskQueue, TaskTypeRegistry
from .manager import queue_manager


@staff_member_required
def queue_management(request):
    """
    Main queue management page with filtered and paginated task list.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start':
            queue_manager.start()
            messages.success(request, 'Task queue started successfully')
        elif action == 'stop':
            queue_manager.stop()
            messages.success(request, 'Task queue stopped')
        elif action == 'pause':
            queue_manager.pause()
            messages.success(request, 'Task queue paused')
        elif action == 'resume':
            queue_manager.resume()
            messages.success(request, 'Task queue resumed')

        
        # Preserve filters and page when redirecting
        query_params = request.GET.copy()
        return redirect(f"{request.path}?{query_params.urlencode()}")
    
    # Get queue statistics
    stats = queue_manager.get_queue_stats()
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    task_type_filter = request.GET.get('task_type', '')
    created_from_filter = request.GET.get('created_from', '')
    created_to_filter = request.GET.get('created_to', '')
    
    # Build query for all tasks
    tasks = TaskQueue.objects.select_related('user').order_by('-created_at')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if task_type_filter:
        tasks = tasks.filter(task_type=task_type_filter)
    
    if created_from_filter:
        try:
            from datetime import datetime
            created_from = datetime.strptime(created_from_filter, '%Y-%m-%d')
            tasks = tasks.filter(created_at__date__gte=created_from.date())
        except ValueError:
            pass
    
    if created_to_filter:
        try:
            from datetime import datetime
            created_to = datetime.strptime(created_to_filter, '%Y-%m-%d')
            tasks = tasks.filter(created_at__date__lte=created_to.date())
        except ValueError:
            pass
    
    # Pagination (10 tasks per page)
    page = request.GET.get('page', 1)
    paginator = Paginator(tasks, 10)
    
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)
    
    # Get filter options
    status_choices = TaskQueue.STATUS_CHOICES
    task_types = TaskQueue.objects.values('task_type').distinct().order_by('task_type')
    
    return render(request, 'queue/management.html', {
        'queue_stats': stats,
        'tasks': tasks_page,
        'paginator': paginator,
        'status_filter': status_filter,
        'task_type_filter': task_type_filter,
        'created_from_filter': created_from_filter,
        'created_to_filter': created_to_filter,
        'status_choices': status_choices,
        'task_types': task_types,
        'is_running': queue_manager.is_running,
        'is_paused': queue_manager.is_paused,
    })


@staff_member_required
def task_list(request):
    """
    Detailed task list with filtering and pagination.
    """
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    task_type_filter = request.GET.get('task_type', '')
    user_filter = request.GET.get('user', '')
    
    # Build query
    tasks = TaskQueue.objects.select_related('user').order_by('-created_at')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if task_type_filter:
        tasks = tasks.filter(task_type=task_type_filter)
    
    if user_filter:
        tasks = tasks.filter(user__username__icontains=user_filter)
    
    # Pagination
    page = request.GET.get('page', 1)
    page_size = 25
    paginator = Paginator(tasks, page_size)
    
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)
    
    # Get filter options
    status_choices = TaskQueue.STATUS_CHOICES
    task_types = TaskQueue.objects.values('task_type').distinct().order_by('task_type')
    
    return render(request, 'queue/task_list.html', {
        'tasks': tasks_page,
        'status_filter': status_filter,
        'task_type_filter': task_type_filter,
        'user_filter': user_filter,
        'status_choices': status_choices,
        'task_types': task_types,
        'paginator': paginator,
    })


@staff_member_required
def task_detail(request, task_id):
    """
    Detailed view for a specific task.
    """
    task = get_object_or_404(TaskQueue.objects.select_related('user'), id=task_id)
    
    # Parse execution log for better display
    execution_log_lines = []
    if task.execution_log:
        execution_log_lines = task.execution_log.split('\n')
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return only the modal content for AJAX requests
        return render(request, 'queue/task_detail_modal.html', {
            'task': task,
            'execution_log_lines': execution_log_lines,
        })
    else:
        # Full page render for regular requests
        return render(request, 'queue/task_detail.html', {
            'task': task,
            'execution_log_lines': execution_log_lines,
        })


@require_POST
@staff_member_required
def cancel_task(request, task_id):
    """
    Cancel a specific task.
    """
    success = queue_manager.cancel_task(task_id)
    
    if success:
        return JsonResponse({'success': True, 'message': 'Task cancelled successfully'})
    else:
        return JsonResponse({
            'success': False, 
            'message': 'Task not found or cannot be cancelled'
        })


@require_POST
@staff_member_required
def retry_task(request, task_id):
    """
    Retry a failed task.
    """
    task = get_object_or_404(TaskQueue, id=task_id)
    
    # Allow retry for failed, completed, and cancelled tasks
    if task.status not in ['failed', 'completed', 'cancelled']:
        return JsonResponse({
            'success': False,
            'message': 'Only failed, completed, or cancelled tasks can be retried'
        })
    
    # Reset task status for retry
    task.status = 'pending'
    task.retry_count = 0
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    task.execution_log = None
    task.save(update_fields=[
        'status', 'retry_count', 'error_message', 'started_at', 'completed_at', 'execution_log'
    ])
    
    return JsonResponse({
        'success': True,
        'message': 'Task queued for retry'
    })


@login_required
def user_task_list(request):
    """
    View for users to see their own tasks.
    """
    tasks = TaskQueue.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    page_size = 20
    paginator = Paginator(tasks, page_size)
    
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)
    
    return render(request, 'queue/user_task_list.html', {
        'tasks': tasks_page,
        'paginator': paginator,
    })








@staff_member_required
def task_type_registry(request):
    """
    View for managing task type registry.
    """
    if request.method == 'POST':
        task_type_id = request.POST.get('task_type_id')
        action = request.POST.get('action')
        
        if action == 'toggle_active':
            task_type = get_object_or_404(TaskTypeRegistry, id=task_type_id)
            task_type.is_active = not task_type.is_active
            task_type.save()
            
            status = 'activated' if task_type.is_active else 'deactivated'
            messages.success(request, f'Task type {task_type.task_type} {status}')
        
        return redirect('queue:task_type_registry')
    
    task_types = TaskTypeRegistry.objects.all().order_by('task_type')
    
    return render(request, 'queue/task_type_registry.html', {
        'task_types': task_types,
    })





def get_task_duration_display(task):
    """
    Get a human-readable display of task duration.
    
    Args:
        task (TaskQueue): Task instance
        
    Returns:
        str: Formatted duration
    """
    if task.started_at and task.completed_at:
        duration = task.get_duration()
        if duration:
            if duration < 60:
                return f"{duration:.1f}s"
            elif duration < 3600:
                return f"{duration/60:.1f}m"
            else:
                return f"{duration/3600:.1f}h"
    return "N/A"


@require_POST
@staff_member_required
def delete_task(request):
    """
    Delete a single task with status validation.
    """
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        
        if not task_id:
            return JsonResponse({
                'success': False,
                'message': 'No task ID provided'
            })
        
        # Only allow deletion of tasks with specific statuses
        allowed_statuses = ['completed', 'failed', 'cancelled']
        
        try:
            task = TaskQueue.objects.get(id=task_id)
        except TaskQueue.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Task not found'
            })
        
        if task.status not in allowed_statuses:
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete task with status "{task.status}". Only completed, failed, or cancelled tasks can be deleted.'
            })
        
        task.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Task deleted successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })