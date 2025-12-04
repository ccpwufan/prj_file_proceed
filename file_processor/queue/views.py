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
    Main queue management page.
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
        elif action == 'clear_failed':
            clear_failed_tasks()
            messages.success(request, 'Failed tasks cleared')
        
        return redirect('queue:management')
    
    # Get queue statistics
    stats = queue_manager.get_queue_stats()
    
    # Get recent tasks
    recent_tasks = TaskQueue.objects.select_related('user').order_by('-created_at')[:20]
    
    # Get task type statistics
    from django.db.models import Count
    # Get task type stats by aggregating from TaskQueue
    task_type_stats = []
    for task_type in TaskTypeRegistry.objects.all():
        count = TaskQueue.objects.filter(task_type=task_type.task_type).count()
        task_type_stats.append({
            'task_type': task_type,
            'task_count': count
        })
    # Sort by task count
    task_type_stats.sort(key=lambda x: x['task_count'], reverse=True)
    
    return render(request, 'queue/management.html', {
        'queue_stats': stats,
        'recent_tasks': recent_tasks,
        'task_type_stats': task_type_stats,
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
    
    if task.status != 'failed':
        return JsonResponse({
            'success': False,
            'message': 'Only failed tasks can be retried'
        })
    
    # Reset task status for retry
    task.status = 'pending'
    task.retry_count = 0
    task.error_message = None
    task.started_at = None
    task.completed_at = None
    task.save(update_fields=[
        'status', 'retry_count', 'error_message', 'started_at', 'completed_at'
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
def queue_statistics(request):
    """
    Detailed queue statistics view.
    """
    # Get statistics
    stats = queue_manager.get_queue_stats()
    
    # Time-based statistics
    now = timezone.now()
    last_hour = now - timezone.timedelta(hours=1)
    last_24h = now - timezone.timedelta(hours=24)
    last_week = now - timezone.timedelta(days=7)
    
    time_stats = {
        'last_hour': {
            'completed': TaskQueue.objects.filter(
                status='completed', 
                completed_at__gte=last_hour
            ).count(),
            'failed': TaskQueue.objects.filter(
                status='failed',
                completed_at__gte=last_hour
            ).count(),
        },
        'last_24h': {
            'completed': TaskQueue.objects.filter(
                status='completed',
                completed_at__gte=last_24h
            ).count(),
            'failed': TaskQueue.objects.filter(
                status='failed',
                completed_at__gte=last_24h
            ).count(),
        },
        'last_week': {
            'completed': TaskQueue.objects.filter(
                status='completed',
                completed_at__gte=last_week
            ).count(),
            'failed': TaskQueue.objects.filter(
                status='failed',
                completed_at__gte=last_week
            ).count(),
        }
    }
    
    # Performance by task type
    task_type_performance = []
    for task_type in TaskTypeRegistry.objects.filter(is_active=True):
        tasks = TaskQueue.objects.filter(task_type=task_type.task_type)
        completed = tasks.filter(status='completed').count()
        failed = tasks.filter(status='failed').count()
        
        if completed + failed > 0:
            success_rate = (completed / (completed + failed)) * 100
        else:
            success_rate = 0
        
        task_type_performance.append({
            'task_type': task_type.task_type,
            'description': task_type.description,
            'total': tasks.count(),
            'completed': completed,
            'failed': failed,
            'success_rate': success_rate,
        })
    
    return render(request, 'queue/statistics.html', {
        'stats': stats,
        'time_stats': time_stats,
        'task_type_performance': task_type_performance,
    })


@require_POST
@staff_member_required
def clear_failed_tasks(request):
    """
    Clear all failed tasks.
    """
    count = TaskQueue.objects.filter(status='failed').delete()[0]
    
    return JsonResponse({
        'success': True,
        'message': f'Cleared {count} failed tasks',
        'count': count
    })


@require_POST
@staff_member_required
def clear_completed_tasks(request):
    """
    Clear all completed tasks (older than 24 hours).
    """
    cutoff_time = timezone.now() - timezone.timedelta(hours=24)
    count = TaskQueue.objects.filter(
        status='completed',
        completed_at__lt=cutoff_time
    ).delete()[0]
    
    return JsonResponse({
        'success': True,
        'message': f'Cleared {count} completed tasks',
        'count': count
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


# Helper functions
def clear_failed_tasks():
    """Clear all failed tasks."""
    TaskQueue.objects.filter(status='failed').delete()


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