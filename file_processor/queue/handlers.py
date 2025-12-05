"""
Task Handler Base Classes and Registry

This module provides the base classes for task handlers and a registry
system to manage different types of task handlers.
"""

import logging
import time
import traceback
from abc import ABC, abstractmethod
from django.utils import timezone
from .models import TaskQueue, TaskTypeRegistry

logger = logging.getLogger(__name__)


class BaseTaskHandler(ABC):
    """
    Abstract base class for all task handlers.
    
    Every task handler should inherit from this class and implement
    the execute method. This class provides common functionality
    for task execution, logging, and error handling.
    """
    
    def __init__(self, task):
        """
        Initialize the task handler.
        
        Args:
            task (TaskQueue): The task instance to handle
        """
        self.task = task
        self.start_time = None
        self.task_type_config = None
        
    @abstractmethod
    def execute(self, task_params):
        """
        Execute the task with given parameters.
        
        This method must be implemented by all subclasses.
        
        Args:
            task_params (dict): Parameters required for task execution
            
        Returns:
            dict: Task execution result
            
        Raises:
            Exception: Any exception that occurs during execution
        """
        pass
    
    def run(self):
        """
        Main method to run the task.
        
        This method handles the complete lifecycle of task execution
        including status updates, error handling, and logging.
        
        Returns:
            dict: Task execution result
            
        Raises:
            Exception: Any exception that occurs during execution
        """
        self.start_time = time.time()
        
        try:
            # Load task type configuration
            self._load_task_config()
            
            # Mark task as processing
            self.task.mark_processing()
            self.log(f"Starting task execution: {self.task.task_name}")
            self.log(f"Task parameters: {self.task.task_params}")
            
            # Pre-execution hook
            self.on_task_start()
            
            # Execute the task
            result = self.execute(self.task.task_params)
            
            # Post-execution hook
            self.on_task_success(result)
            
            # Mark task as completed
            self.task.mark_completed(result=result)
            execution_time = time.time() - self.start_time
            self.log(f"Task completed successfully in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg, level='error')
            
            # Error handling hook
            self.on_task_error(e)
            
            # Determine if should retry
            should_retry = self.should_retry(e)
            self.task.mark_failed(error_message=error_msg, retry=should_retry)
            
            if should_retry:
                retry_info = f"Scheduling retry {self.task.retry_count}/{self.task.max_retries}"
                self.log(retry_info)
                self.on_task_retry(e)
            else:
                self.log(f"Task failed permanently after {self.task.retry_count} retries")
                self.on_task_failure(e)
                
            raise
    
    def _load_task_config(self):
        """Load task type configuration from registry."""
        try:
            self.task_type_config = TaskTypeRegistry.objects.get(
                task_type=self.task.task_type,
                is_active=True
            )
        except TaskTypeRegistry.DoesNotExist:
            self.log(f"No configuration found for task type: {self.task.task_type}")
    
    def should_retry(self, exception):
        """
        Determine if the task should be retried.
        
        Subclasses can override this method to implement custom retry logic.
        
        Args:
            exception (Exception): The exception that occurred
            
        Returns:
            bool: True if task should be retried
        """
        # Don't retry if max retries reached
        if self.task.retry_count >= self.task.max_retries:
            return False
        
        # Don't retry critical errors
        if self.task.task_type == 'critical':
            return False
        
        # Custom retry logic based on task type config
        if self.task_type_config:
            max_retries = self.task_type_config.default_max_retries
            return self.task.retry_count < max_retries
        
        # Default: retry all exceptions
        return True
    
    def on_task_start(self):
        """
        Hook called when task starts processing.
        
        Subclasses can override this method to perform setup actions.
        """
        pass
    
    def on_task_success(self, result):
        """
        Hook called when task completes successfully.
        
        Args:
            result: The result returned by execute()
        """
        pass
    
    def on_task_error(self, exception):
        """
        Hook called when an error occurs during task execution.
        
        Args:
            exception (Exception): The exception that occurred
        """
        pass
    
    def on_task_retry(self, exception):
        """
        Hook called when task is scheduled for retry.
        
        Args:
            exception (Exception): The exception that caused the retry
        """
        pass
    
    def on_task_failure(self, exception):
        """
        Hook called when task fails permanently.
        
        Args:
            exception (Exception): The exception that caused the failure
        """
        pass
    
    def log(self, message, level='info'):
        """
        Log a message with timestamp.
        
        Args:
            message (str): Log message
            level (str): Log level ('info', 'warning', 'error', 'debug')
        """
        log_method = getattr(logger, level)
        log_method(f"Task #{self.task.id}: {message}")
        
        # Also save to task execution log
        self.task.log(message)
        self.task.save(update_fields=['execution_log'])
    
    def check_timeout(self):
        """
        Check if the task has exceeded its timeout limit.
        
        Raises:
            TimeoutError: If task has timed out
        """
        timeout_seconds = getattr(self.task_type_config, 'default_timeout', None) or self.task.timeout_seconds
        
        if timeout_seconds and self.start_time:
            elapsed_time = time.time() - self.start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"Task timed out after {elapsed_time:.2f}s (limit: {timeout_seconds}s)")
    
    def update_progress(self, progress, message=None):
        """
        Update task progress.
        
        Args:
            progress (float): Progress percentage (0-100)
            message (str): Optional progress message
        """
        progress_data = {
            'progress': progress,
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'elapsed_time': time.time() - self.start_time if self.start_time else 0
        }
        
        if not self.task.result:
            self.task.result = {}
        
        self.task.result['progress'] = progress_data
        
        # Save progress without triggering full save
        TaskQueue.objects.filter(id=self.task.id).update(
            result=self.task.result
        )
        
        if message:
            self.log(f"Progress: {progress}% - {message}")
        else:
            self.log(f"Progress: {progress}%")
    
    def get_task_config(self, key, default=None):
        """
        Get task type configuration value.
        
        Args:
            key (str): Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self.task_type_config:
            return default
        
        config_map = {
            'timeout': self.task_type_config.default_timeout,
            'priority': self.task_type_config.default_priority,
            'max_retries': self.task_type_config.default_max_retries,
            'max_concurrent': self.task_type_config.max_concurrent,
        }
        
        return config_map.get(key, default)


class TaskHandlerRegistry:
    """
    Registry for managing task handlers.
    
    This class maintains a mapping between task types and their
    corresponding handler classes.
    """
    
    _handlers = {}
    
    @classmethod
    def register(cls, task_type, handler_class):
        """
        Register a handler class for a specific task type.
        
        Args:
            task_type (str): Task type identifier
            handler_class (class): Handler class that inherits from BaseTaskHandler
        """
        if not issubclass(handler_class, BaseTaskHandler):
            raise ValueError(f"Handler class {handler_class} must inherit from BaseTaskHandler")
        
        cls._handlers[task_type] = handler_class
        logger.info(f"Registered handler for task type '{task_type}': {handler_class.__name__}")
    
    @classmethod
    def unregister(cls, task_type):
        """
        Unregister a handler for a specific task type.
        
        Args:
            task_type (str): Task type identifier
        """
        if task_type in cls._handlers:
            del cls._handlers[task_type]
            logger.info(f"Unregistered handler for task type '{task_type}'")
    
    @classmethod
    def get_handler(cls, task_type, task):
        """
        Get a handler instance for a specific task type.
        
        Args:
            task_type (str): Task type identifier
            task (TaskQueue): Task instance
            
        Returns:
            BaseTaskHandler: Handler instance
            
        Raises:
            ValueError: If no handler is registered for the task type
        """
        handler_class = cls._handlers.get(task_type)
        if not handler_class:
            raise ValueError(f"No handler registered for task type: {task_type}")
        
        return handler_class(task)
    
    @classmethod
    def get_registered_types(cls):
        """
        Get a list of all registered task types.
        
        Returns:
            list: List of registered task type identifiers
        """
        return list(cls._handlers.keys())
    
    @classmethod
    def get_handler_class(cls, task_type):
        """
        Get the handler class for a specific task type.
        
        Args:
            task_type (str): Task type identifier
            
        Returns:
            class: Handler class or None if not found
        """
        return cls._handlers.get(task_type)
    
    @classmethod
    def clear(cls):
        """Clear all registered handlers."""
        cls._handlers.clear()
        logger.info("Cleared all registered handlers")


class BatchTaskHandler(BaseTaskHandler):
    """
    Base class for handlers that process multiple items in a batch.
    
    This class provides common functionality for batch processing tasks.
    """
    
    def __init__(self, task):
        super().__init__(task)
        self.batch_size = None
        self.total_items = None
        self.processed_items = 0
    
    def execute(self, task_params):
        """
        Execute batch processing.
        
        Args:
            task_params (dict): Should contain 'items' key with list of items to process
            
        Returns:
            dict: Batch processing results
        """
        items = task_params.get('items', [])
        if not items:
            raise ValueError("No items provided for batch processing")
        
        self.total_items = len(items)
        self.batch_size = task_params.get('batch_size', 10)
        
        results = []
        failed_items = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            try:
                batch_results = self.process_batch(batch)
                results.extend(batch_results)
                
                self.processed_items += len(batch)
                progress = (self.processed_items / self.total_items) * 100
                self.update_progress(progress, f"Processed {self.processed_items}/{self.total_items} items")
                
            except Exception as e:
                # Handle batch failure
                for item in batch:
                    failed_items.append({'item': item, 'error': str(e)})
                self.log(f"Batch processing failed for items {i}-{i+len(batch)}: {e}", level='error')
        
        return {
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'failed_items': len(failed_items),
            'success_rate': (self.processed_items / self.total_items) * 100,
            'results': results,
            'failed_items': failed_items
        }
    
    @abstractmethod
    def process_batch(self, batch):
        """
        Process a batch of items.
        
        Args:
            batch (list): List of items to process
            
        Returns:
            list: Results for processed items
        """
        pass