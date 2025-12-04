"""
Queue management URL configuration.
"""

from django.urls import path
from . import views

app_name = 'queue'

urlpatterns = [
    # Queue management
    path('', views.queue_management, name='management'),
    
    # Task management
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/cancel/', views.cancel_task, name='cancel_task'),
    path('tasks/<int:task_id>/retry/', views.retry_task, name='retry_task'),
    
    # User views
    path('my-tasks/', views.user_task_list, name='user_task_list'),
    
    # Statistics
    path('statistics/', views.queue_statistics, name='statistics'),
    
    # Task type registry
    path('task-types/', views.task_type_registry, name='task_type_registry'),
    
    # Cleanup actions
    path('clear-failed/', views.clear_failed_tasks, name='clear_failed'),
    path('clear-completed/', views.clear_completed_tasks, name='clear_completed'),
]