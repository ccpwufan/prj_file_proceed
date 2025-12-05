"""
Universal Task Queue Models

This module defines the database models for the universal task queue system.
It provides a flexible way to handle different types of background tasks
with priority, retry logic, and comprehensive logging.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class TaskQueue(models.Model):
    """
    Universal task queue model for handling various background tasks.
    
    This model stores information about tasks that need to be processed
    asynchronously, including their type, parameters, status, and execution details.
    """
    
    # Task identification
    task_name = models.CharField(max_length=100, db_index=True, 
                                help_text="Human-readable name of the task")
    task_type = models.CharField(max_length=50, db_index=True,
                                help_text="Task type identifier: video_conversion, pdf_processing, etc.")
    
    # Task owner and parameters
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                           help_text="User who initiated this task")
    task_params = models.JSONField(default=dict,
                                  help_text="Parameters required for task execution")
    
    # Status management
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('retrying', 'Retrying'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                             db_index=True, help_text="Current status of the task")
    
    # Priority and execution control
    priority = models.IntegerField(default=0, db_index=True,
                                 help_text="Priority level (higher numbers = higher priority)")
    max_retries = models.IntegerField(default=3,
                                    help_text="Maximum number of retry attempts")
    retry_count = models.IntegerField(default=0,
                                     help_text="Current number of retry attempts")
    
    # Timing information
    created_at = models.DateTimeField(auto_now_add=True, db_index=True,
                                     help_text="When the task was created")
    started_at = models.DateTimeField(null=True, blank=True,
                                     help_text="When the task started processing")
    completed_at = models.DateTimeField(null=True, blank=True,
                                       help_text="When the task completed (or failed)")
    
    # Execution control
    delay_until = models.DateTimeField(null=True, blank=True,
                                      help_text="Delay execution until this time")
    timeout_seconds = models.IntegerField(null=True, blank=True,
                                         help_text="Task timeout in seconds")
    
    # Results and logging
    result = models.JSONField(null=True, blank=True,
                             help_text="Task execution result")
    error_message = models.TextField(null=True, blank=True,
                                    help_text="Detailed error message if task failed")
    execution_log = models.TextField(null=True, blank=True,
                                    help_text="Execution log with timestamps")
    
    class Meta:
        ordering = ['-priority', 'created_at']
        db_table = 'queue_task_queue'
        indexes = [
            models.Index(fields=['status', 'priority', 'created_at']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"Task #{self.id}: {self.task_name} ({self.status})"
    
    def mark_processing(self):
        """Mark task as processing and set start time."""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
        self.log("Task marked as processing")
        self.save(update_fields=['execution_log'])
    
    def mark_completed(self, result=None):
        """Mark task as completed and set result."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save(update_fields=['status', 'completed_at', 'result'])
        self.log("Task completed successfully")
        self.save(update_fields=['execution_log'])
    
    def mark_failed(self, error_message=None, retry=False):
        """
        Mark task as failed or schedule for retry.
        
        Args:
            error_message (str): Detailed error message
            retry (bool): Whether this is a retry attempt
        """
        self.retry_count += 1
        self.completed_at = timezone.now()
        
        if retry and self.retry_count < self.max_retries:
            self.status = 'retrying'
            self.log(f"Task failed, scheduling retry {self.retry_count}/{self.max_retries}")
        else:
            self.status = 'failed'
            self.log(f"Task failed permanently after {self.retry_count} retries")
        
        if error_message:
            self.error_message = error_message
        
        self.save(update_fields=['status', 'retry_count', 'completed_at', 'error_message'])
        self.save(update_fields=['execution_log'])
    
    def mark_cancelled(self):
        """Mark task as cancelled."""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
        self.log("Task cancelled")
        self.save(update_fields=['execution_log'])
    
    def should_retry(self):
        """Check if task should be retried based on retry count and status."""
        return (self.retry_count < self.max_retries and 
                self.status == 'failed' and 
                self.task_type != 'critical')
    
    def is_ready_to_process(self):
        """Check if task is ready for processing."""
        now = timezone.now()
        return (self.status in ['pending', 'retrying'] and
                (self.delay_until is None or self.delay_until <= now))
    
    def is_expired(self):
        """Check if task has exceeded its timeout."""
        if not self.timeout_seconds or not self.started_at:
            return False
        return (timezone.now() - self.started_at).total_seconds() > self.timeout_seconds
    
    def get_duration(self):
        """Get task execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def log(self, message):
        """Add timestamped message to execution log."""
        timestamp = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        if self.execution_log:
            self.execution_log += f"\n{log_entry}"
        else:
            self.execution_log = log_entry
        
        # Don't save here to avoid recursion; caller should save
        return log_entry


class TaskTypeRegistry(models.Model):
    """
    Registry for different task types and their handlers.
    
    This model maintains a registry of all available task types,
    their handler classes, and configuration parameters.
    """
    
    task_type = models.CharField(max_length=50, unique=True, db_index=True,
                                help_text="Unique task type identifier")
    handler_class = models.CharField(max_length=255,
                                    help_text="Fully qualified class name of the task handler")
    description = models.TextField(blank=True,
                                  help_text="Description of what this task type does")
    
    # Default configuration
    default_timeout = models.IntegerField(default=300,
                                         help_text="Default timeout in seconds")
    default_priority = models.IntegerField(default=0,
                                         help_text="Default priority for this task type")
    max_concurrent = models.IntegerField(default=1,
                                        help_text="Maximum concurrent tasks of this type")
    default_max_retries = models.IntegerField(default=3,
                                             help_text="Default maximum retry attempts")
    
    # Status
    is_active = models.BooleanField(default=True,
                                   help_text="Whether this task type is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'queue_task_type_registry'
        ordering = ['task_type']
    
    def __str__(self):
        return f"{self.task_type} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_handler_class(self):
        """Import and return the handler class."""
        try:
            module_name, class_name = self.handler_class.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Cannot import handler class {self.handler_class}: {e}")