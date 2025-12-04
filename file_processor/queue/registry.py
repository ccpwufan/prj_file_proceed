"""
Task Handler Registry Decorators

This module provides decorators and utilities for registering task handlers
with the queue system in a convenient way.
"""

import logging
from functools import wraps
from .handlers import TaskHandlerRegistry
from .models import TaskTypeRegistry

logger = logging.getLogger(__name__)


def register_task_handler(task_type, **registry_options):
    """
    Decorator for registering task handlers.
    
    This decorator automatically registers a task handler with the TaskHandlerRegistry
    and creates a corresponding entry in the TaskTypeRegistry model.
    
    Args:
        task_type (str): Task type identifier (e.g., 'video_conversion', 'pdf_processing')
        **registry_options: Additional options for TaskTypeRegistry:
            - description (str): Description of the task type
            - default_timeout (int): Default timeout in seconds
            - default_priority (int): Default priority
            - max_concurrent (int): Maximum concurrent tasks
            - is_active (bool): Whether the task type is active
    
    Returns:
        decorator: The decorator function
    
    Usage:
        @register_task_handler('video_conversion', 
                              description='Convert video files to web format',
                              default_timeout=300,
                              default_priority=5)
        class VideoConversionHandler(BaseTaskHandler):
            def execute(self, task_params):
                # Implementation here
                pass
    """
    def decorator(handler_class):
        # Register with TaskHandlerRegistry
        try:
            TaskHandlerRegistry.register(task_type, handler_class)
            logger.info(f"Registered handler for '{task_type}': {handler_class.__name__}")
        except Exception as e:
            logger.error(f"Failed to register handler for '{task_type}': {e}")
            raise
        
        # Prepare registry options
        registry_data = {
            'task_type': task_type,
            'handler_class': f"{handler_class.__module__}.{handler_class.__name__}",
            'description': registry_options.get('description', handler_class.__doc__ or ""),
            'default_timeout': registry_options.get('default_timeout', 300),
            'default_priority': registry_options.get('default_priority', 0),
            'max_concurrent': registry_options.get('max_concurrent', 1),
            'default_max_retries': registry_options.get('default_max_retries', 3),
            'is_active': registry_options.get('is_active', True),
        }
        
        # Update or create in database
        try:
            # Only update if tables exist (avoid migration issues)
            from django.db import connection
            if TaskTypeRegistry._meta.db_table in connection.introspection.table_names():
                TaskTypeRegistry.objects.update_or_create(
                    task_type=task_type,
                    defaults=registry_data
                )
                logger.info(f"Updated TaskTypeRegistry for '{task_type}'")
            else:
                logger.debug(f"TaskTypeRegistry table not yet created, skipping database update for '{task_type}'")
        except Exception as e:
            # This might fail during migrations or early Django startup
            # Don't prevent the application from starting
            logger.warning(f"Could not update TaskTypeRegistry for '{task_type}': {e}")
        
        # Add metadata to the handler class
        handler_class._task_type = task_type
        handler_class._registry_options = registry_options
        
        return handler_class
    
    return decorator


def batch_task_handler(batch_size=10, **registry_options):
    """
    Decorator for registering batch task handlers.
    
    This is a convenience decorator for batch processing tasks that
    automatically sets up batch-related options.
    
    Args:
        batch_size (int): Default batch size for processing
        **registry_options: Additional options for TaskTypeRegistry
    
    Returns:
        decorator: The decorator function
    """
    def decorator(task_type, **options):
        # Add batch-specific options
        options.update({
            'description': options.get('description', f"Batch processing for {task_type}"),
            'max_concurrent': options.get('max_concurrent', 2),  # Allow more concurrency for batch tasks
            **registry_options
        })
        
        return register_task_handler(task_type, **options)
    
    return decorator


def high_priority_task_handler(task_type, **registry_options):
    """
    Decorator for registering high-priority task handlers.
    
    Args:
        task_type (str): Task type identifier
        **registry_options: Additional options for TaskTypeRegistry
    
    Returns:
        decorator: The decorator function
    """
    registry_options.setdefault('default_priority', 8)
    registry_options.setdefault('description', 
                               registry_options.get('description', f"High priority task: {task_type}"))
    
    return register_task_handler(task_type, **registry_options)


def low_priority_task_handler(task_type, **registry_options):
    """
    Decorator for registering low-priority task handlers.
    
    Args:
        task_type (str): Task type identifier
        **registry_options: Additional options for TaskTypeRegistry
    
    Returns:
        decorator: The decorator function
    """
    registry_options.setdefault('default_priority', 1)
    registry_options.setdefault('description', 
                               registry_options.get('description', f"Low priority task: {task_type}"))
    
    return register_task_handler(task_type, **registry_options)


def task_handler_with_timeout(default_timeout, **registry_options):
    """
    Decorator factory for registering task handlers with specific timeout.
    
    Args:
        default_timeout (int): Default timeout in seconds
        **registry_options: Additional options for TaskTypeRegistry
    
    Returns:
        decorator: The decorator function
    
    Usage:
        @task_handler_with_timeout(600)  # 10 minutes timeout
        def register_long_running_task(task_type):
            return register_task_handler(task_type, default_timeout=600)
    """
    def decorator(task_type, **options):
        options.setdefault('default_timeout', default_timeout)
        return register_task_handler(task_type, **options)
    
    return decorator


def retry_task_handler(max_retries=5, **registry_options):
    """
    Decorator factory for registering task handlers with custom retry count.
    
    Args:
        max_retries (int): Maximum number of retries
        **registry_options: Additional options for TaskTypeRegistry
    
    Returns:
        decorator: The decorator function
    """
    def decorator(task_type, **options):
        options.setdefault('default_max_retries', max_retries)
        return register_task_handler(task_type, **options)
    
    return decorator


# Utility functions for managing task handlers
def get_registered_task_types():
    """
    Get all registered task types.
    
    Returns:
        list: List of task type identifiers
    """
    return TaskHandlerRegistry.get_registered_types()


def get_task_handler_class(task_type):
    """
    Get the handler class for a specific task type.
    
    Args:
        task_type (str): Task type identifier
        
    Returns:
        class: Handler class or None if not found
    """
    return TaskHandlerRegistry.get_handler_class(task_type)


def unregister_task_handler(task_type):
    """
    Unregister a task handler.
    
    Args:
        task_type (str): Task type identifier
    """
    TaskHandlerRegistry.unregister(task_type)
    
    # Also deactivate in database
    try:
        TaskTypeRegistry.objects.filter(task_type=task_type).update(is_active=False)
        logger.info(f"Deactivated task type '{task_type}' in database")
    except Exception as e:
        logger.warning(f"Could not deactivate task type '{task_type}' in database: {e}")


def reactivate_task_handler(task_type):
    """
    Reactivate a deactivated task handler.
    
    Args:
        task_type (str): Task type identifier
    """
    try:
        TaskTypeRegistry.objects.filter(task_type=task_type).update(is_active=True)
        logger.info(f"Reactivated task type '{task_type}' in database")
    except Exception as e:
        logger.error(f"Could not reactivate task type '{task_type}' in database: {e}")


def update_task_handler_config(task_type, **config):
    """
    Update configuration for a task handler.
    
    Args:
        task_type (str): Task type identifier
        **config: Configuration options to update
    """
    allowed_fields = {
        'description', 'default_timeout', 'default_priority', 
        'max_concurrent', 'default_max_retries', 'is_active'
    }
    
    # Filter valid fields
    update_data = {k: v for k, v in config.items() if k in allowed_fields}
    
    if not update_data:
        logger.warning(f"No valid configuration options provided for task type '{task_type}'")
        return
    
    try:
        TaskTypeRegistry.objects.filter(task_type=task_type).update(**update_data)
        logger.info(f"Updated configuration for task type '{task_type}': {update_data}")
    except Exception as e:
        logger.error(f"Could not update configuration for task type '{task_type}': {e}")


# Context manager for temporary task handler registration
class TemporaryTaskHandler:
    """
    Context manager for temporarily registering a task handler.
    
    This is useful for testing or for one-time task processing.
    """
    
    def __init__(self, task_type, handler_class, **registry_options):
        self.task_type = task_type
        self.handler_class = handler_class
        self.registry_options = registry_options
        self.was_registered = False
    
    def __enter__(self):
        # Check if already registered
        if self.task_type in TaskHandlerRegistry.get_registered_types():
            self.was_registered = True
            return self.handler_class
        
        # Register temporarily
        register_task_handler(self.task_type, **self.registry_options)(self.handler_class)
        return self.handler_class
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Unregister if it wasn't already registered
        if not self.was_registered:
            unregister_task_handler(self.task_type)


# Decorator for adding task creation methods to classes
def task_creator(task_type):
    """
    Decorator that adds a task creation method to a class.
    
    The created method will be named f'add_{task_type}_task'.
    
    Args:
        task_type (str): Task type identifier
    
    Usage:
        @task_creator('video_conversion')
        class VideoService:
            pass
        
        # Now VideoService has add_video_conversion_task method
        service = VideoService()
        service.add_video_conversion_task(video_file_id=123)
    """
    def decorator(cls):
        def add_task_method(self, user=None, priority=None, **task_params):
            """Dynamically created task creation method."""
            from .manager import queue_manager
            
            # Get default priority from task type registry
            if priority is None:
                try:
                    task_type_config = TaskTypeRegistry.objects.get(task_type=task_type, is_active=True)
                    priority = task_type_config.default_priority
                except TaskTypeRegistry.DoesNotExist:
                    priority = 0
            
            return queue_manager.add_task(
                task_name=f"{task_type} task",
                task_type=task_type,
                task_params=task_params,
                user=user,
                priority=priority
            )
        
        # Set method name and docstring
        method_name = f"add_{task_type}_task"
        add_task_method.__name__ = method_name
        add_task_method.__doc__ = f"""Add a {task_type} task to the queue.
        
        Args:
            user (User): User who initiated the task
            priority (int): Task priority (overrides default)
            **task_params: Task-specific parameters
            
        Returns:
            TaskQueue: Created task instance
        """
        
        # Add method to class
        setattr(cls, method_name, add_task_method)
        
        return cls
    
    return decorator