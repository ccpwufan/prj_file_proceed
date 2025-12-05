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
    path('task_detail/', views.task_list, name='task_list'),
    path('task_detail/<int:task_id>/', views.task_detail, name='task_detail'),
    path('task_detail/<int:task_id>/cancel/', views.cancel_task, name='cancel_task'),
    path('task_detail/<int:task_id>/retry/', views.retry_task, name='retry_task'),
    
    # User views
    path('my-tasks/', views.user_task_list, name='user_task_list'),
    

    
    # Task type registry
    path('task-types/', views.task_type_registry, name='task_type_registry'),
    
    # Task operations
    path('delete-task/', views.delete_task, name='delete_task'),
]