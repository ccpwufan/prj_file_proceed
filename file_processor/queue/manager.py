"""
Queue Manager

This module implements the core queue management system that handles
task scheduling, execution, and monitoring.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from django.db import transaction, models
from django.utils import timezone
from django.core.management import call_command
from .models import TaskQueue, TaskTypeRegistry
from .handlers import TaskHandlerRegistry

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Universal queue manager for handling background tasks.
    
    This class manages the execution of tasks in the queue,
    including scheduling, worker management, and statistics.
    """
    
    def __init__(self, workers_count=1, sleep_interval=2, max_idle_cycles=10):
        """
        Initialize the queue manager.
        
        Args:
            workers_count (int): Number of worker threads to spawn
            sleep_interval (int): Sleep interval between task checks (seconds)
            max_idle_cycles (int): Maximum idle cycles before worker becomes lazy
        """
        self.workers_count = workers_count
        self.sleep_interval = sleep_interval
        self.max_idle_cycles = max_idle_cycles
        
        # Runtime state
        self.is_running = False
        self.is_paused = False
        self.worker_threads = []
        self.task_types = {}
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'tasks_completed': 0,
            'start_time': None,
            'last_activity': None,
            'idle_cycles': 0
        }
        
        logger.info(f"QueueManager initialized with {workers_count} workers")
    
    def start(self):
        """Start the queue manager and worker threads."""
        if self.is_running:
            logger.warning("Queue manager is already running")
            return
        
        self.is_running = True
        self.is_paused = False
        self.shutdown_event.clear()
        self.stats['start_time'] = timezone.now()
        
        # Load task types from registry
        self._load_task_types()
        
        # Create and start worker threads
        for i in range(self.workers_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"QueueWorker-{i}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="QueueMonitor",
            daemon=True
        )
        monitor_thread.start()
        
        logger.info(f"Queue manager started with {len(self.worker_threads)} workers")
    
    def stop(self, timeout=30):
        """
        Stop the queue manager and all worker threads.
        
        Args:
            timeout (int): Maximum time to wait for workers to finish (seconds)
        """
        if not self.is_running:
            logger.warning("Queue manager is not running")
            return
        
        logger.info("Stopping queue manager...")
        
        # Signal shutdown
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=timeout)
            if worker.is_alive():
                logger.warning(f"Worker {worker.name} did not stop gracefully")
        
        self.worker_threads = []
        
        logger.info("Queue manager stopped")
    
    def pause(self):
        """Pause task processing (workers will wait)."""
        self.is_paused = True
        logger.info("Queue manager paused")
    
    def resume(self):
        """Resume task processing."""
        self.is_paused = False
        logger.info("Queue manager resumed")
    
    def add_task(self, task_name, task_type, task_params=None, user=None,
                 priority=0, delay_until=None, max_retries=3, timeout_seconds=None):
        """
        Add a new task to the queue.
        
        Args:
            task_name (str): Human-readable task name
            task_type (str): Task type identifier
            task_params (dict): Task parameters
            user (User): User who initiated the task
            priority (int): Task priority (higher numbers = higher priority)
            delay_until (datetime): Delay execution until this time
            max_retries (int): Maximum retry attempts
            timeout_seconds (int): Task timeout in seconds
            
        Returns:
            TaskQueue: Created task instance
        """
        # Get default values from task type registry
        task_type_config = self.task_types.get(task_type)
        if task_type_config:
            if priority == 0:
                priority = task_type_config.default_priority
            if max_retries == 3:
                max_retries = task_type_config.default_max_retries
            if timeout_seconds is None:
                timeout_seconds = task_type_config.default_timeout
        
        with transaction.atomic():
            task = TaskQueue.objects.create(
                task_name=task_name,
                task_type=task_type,
                user=user,
                task_params=task_params or {},
                priority=priority,
                delay_until=delay_until,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds
            )
            
        logger.info(f"Added task {task.id}: {task_name} ({task_type})")
        return task
    
    def cancel_task(self, task_id):
        """
        Cancel a specific task.
        
        Args:
            task_id (int): ID of the task to cancel
            
        Returns:
            bool: True if task was cancelled, False if not found or already completed
        """
        try:
            with transaction.atomic():
                task = TaskQueue.objects.select_for_update().get(id=task_id)
                
                if task.status in ['pending', 'processing', 'retrying']:
                    task.mark_cancelled()
                    logger.info(f"Cancelled task {task_id}")
                    return True
                else:
                    logger.warning(f"Cannot cancel task {task_id} in status: {task.status}")
                    return False
                    
        except TaskQueue.DoesNotExist:
            logger.error(f"Task {task_id} not found")
            return False
    
    def get_queue_stats(self):
        """
        Get comprehensive queue statistics.
        
        Returns:
            dict: Queue statistics
        """
        # Basic task counts
        stats = {
            'pending': TaskQueue.objects.filter(status='pending').count(),
            'processing': TaskQueue.objects.filter(status='processing').count(),
            'retrying': TaskQueue.objects.filter(status='retrying').count(),
            'completed': TaskQueue.objects.filter(status='completed').count(),
            'failed': TaskQueue.objects.filter(status='failed').count(),
            'cancelled': TaskQueue.objects.filter(status='cancelled').count(),
            'total': TaskQueue.objects.count(),
        }
        
        # Task type breakdown
        task_type_stats = {}
        for task_type in TaskQueue.objects.values('task_type').distinct():
            type_name = task_type['task_type']
            task_type_stats[type_name] = {
                'total': TaskQueue.objects.filter(task_type=type_name).count(),
                'pending': TaskQueue.objects.filter(task_type=type_name, status='pending').count(),
                'processing': TaskQueue.objects.filter(task_type=type_name, status='processing').count(),
                'completed': TaskQueue.objects.filter(task_type=type_name, status='completed').count(),
                'failed': TaskQueue.objects.filter(task_type=type_name, status='failed').count(),
            }
        
        stats['by_type'] = task_type_stats
        
        # Recent activity
        recent_time = timezone.now() - timedelta(hours=24)
        stats['recent'] = {
            'completed_last_24h': TaskQueue.objects.filter(
                status='completed', completed_at__gte=recent_time
            ).count(),
            'failed_last_24h': TaskQueue.objects.filter(
                status='failed', completed_at__gte=recent_time
            ).count(),
        }
        
        # Performance metrics
        if self.stats['start_time']:
            runtime = (timezone.now() - self.stats['start_time']).total_seconds()
            stats['performance'] = {
                'runtime_seconds': runtime,
                'runtime_formatted': str(timedelta(seconds=int(runtime))),
                'tasks_processed': self.stats['tasks_processed'],
                'tasks_completed': self.stats['tasks_completed'],
                'tasks_failed': self.stats['tasks_failed'],
                'success_rate': (self.stats['tasks_completed'] / max(1, self.stats['tasks_processed'])) * 100,
                'throughput_per_hour': (self.stats['tasks_processed'] / max(1, runtime / 3600))
            }
        
        # Manager status
        stats['manager'] = {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'workers_count': len(self.worker_threads),
            'sleep_interval': self.sleep_interval,
            'idle_cycles': self.stats['idle_cycles']
        }
        
        return stats
    
    def _load_task_types(self):
        """Load active task types from the registry."""
        self.task_types = {}
        for task_type in TaskTypeRegistry.objects.filter(is_active=True):
            self.task_types[task_type.task_type] = task_type
        
        logger.info(f"Loaded {len(self.task_types)} active task types")
    
    def _worker_loop(self):
        """Main worker thread loop."""
        worker_name = threading.current_thread().name
        logger.info(f"Worker {worker_name} started")
        
        idle_cycles = 0
        
        while self.is_running:
            try:
                # Check if paused
                if self.is_paused:
                    logger.debug(f"Worker {worker_name} paused")
                    time.sleep(self.sleep_interval)
                    continue
                
                # Get next task
                task = self._get_next_task()
                
                if task:
                    idle_cycles = 0
                    self.stats['last_activity'] = timezone.now()
                    self.stats['tasks_processed'] += 1
                    
                    logger.info(f"Worker {worker_name} processing task {task.id}")
                    
                    try:
                        # Get handler and execute task
                        handler = TaskHandlerRegistry.get_handler(task.task_type, task)
                        handler.run()
                        
                        self.stats['tasks_completed'] += 1
                        logger.info(f"Worker {worker_name} completed task {task.id}")
                        
                    except Exception as e:
                        self.stats['tasks_failed'] += 1
                        logger.error(f"Worker {worker_name} failed task {task.id}: {e}")
                        
                else:
                    # No tasks available
                    idle_cycles += 1
                    
                    # Adaptive sleep: sleep longer when idle
                    if idle_cycles > 5:
                        sleep_time = min(self.sleep_interval * 2, 10)
                    else:
                        sleep_time = self.sleep_interval
                    
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Worker {worker_name} loop error: {e}")
                time.sleep(self.sleep_interval)
        
        logger.info(f"Worker {worker_name} stopped")
    
    def _monitor_loop(self):
        """Monitoring thread for statistics and cleanup."""
        logger.info("Monitor thread started")
        
        while self.is_running:
            try:
                # Check for expired tasks
                self._check_expired_tasks()
                
                # Check for stuck tasks
                self._check_stuck_tasks()
                
                # Update idle cycles counter
                if self.stats['last_activity']:
                    idle_time = (timezone.now() - self.stats['last_activity']).total_seconds()
                    if idle_time > self.sleep_interval * 2:
                        self.stats['idle_cycles'] += 1
                    else:
                        self.stats['idle_cycles'] = 0
                
                # Log periodic statistics
                if self.stats['tasks_processed'] > 0 and self.stats['tasks_processed'] % 10 == 0:
                    stats = self.get_queue_stats()
                    logger.info(f"Queue stats: {stats['performance']}")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(30)
        
        logger.info("Monitor thread stopped")
    
    def _get_next_task(self):
        """
        Get the next available task for processing.
        
        Returns:
            TaskQueue or None: Next task to process
        """
        with transaction.atomic():
            # Check for delayed tasks that are now ready
            now = timezone.now()
            
            # Use select_for_update with skip_locked to avoid race conditions
            task = TaskQueue.objects.select_for_update(skip_locked=True).filter(
                status__in=['pending', 'retrying']
            ).filter(
                models.Q(delay_until__isnull=True) | models.Q(delay_until__lte=now)
            ).order_by('-priority', 'created_at').first()
            
            if task:
                # Additional checks
                if not task.is_ready_to_process():
                    return None
                
                # Check concurrency limits for task type
                task_type_config = self.task_types.get(task.task_type)
                if task_type_config:
                    current_processing = TaskQueue.objects.filter(
                        task_type=task.task_type,
                        status='processing'
                    ).count()
                    
                    if current_processing >= task_type_config.max_concurrent:
                        logger.debug(f"Max concurrent tasks reached for {task.task_type}")
                        return None
            
            return task
    
    def _check_expired_tasks(self):
        """Check for tasks that have exceeded their timeout."""
        expired_tasks = TaskQueue.objects.filter(
            status='processing',
            started_at__lt=timezone.now() - timedelta(minutes=30)  # Default 30 min timeout
        )
        
        for task in expired_tasks:
            # Check if task has specific timeout
            timeout_minutes = 30
            task_type_config = self.task_types.get(task.task_type)
            if task_type_config and task_type_config.default_timeout:
                timeout_minutes = task_type_config.default_timeout // 60
            
            if task.is_expired():
                error_msg = f"Task expired after running for {task.get_duration():.2f}s"
                logger.warning(f"Task {task.id} expired: {error_msg}")
                
                # Mark as failed and schedule for retry if applicable
                task.mark_failed(error_msg, retry=True)
                self.stats['tasks_failed'] += 1
    
    def _check_stuck_tasks(self):
        """Check for tasks that have been processing for too long without timeout."""
        # This could be enhanced with specific business logic
        pass


# Global queue manager instance
queue_manager = QueueManager(workers_count=1)


# Convenience functions for common operations
def add_video_conversion_task(video_file_id, user=None, priority=0):
    """Convenience function to add a video conversion task."""
    return queue_manager.add_task(
        task_name=f"Convert video file {video_file_id}",
        task_type='video_conversion',
        task_params={'video_file_id': video_file_id},
        user=user,
        priority=priority
    )


def add_pdf_processing_task(pdf_file_id, user=None, priority=0):
    """Convenience function to add a PDF processing task."""
    return queue_manager.add_task(
        task_name=f"Process PDF file {pdf_file_id}",
        task_type='pdf_processing',
        task_params={'pdf_file_id': pdf_file_id},
        user=user,
        priority=priority
    )


def add_image_processing_task(image_file_id, processing_type, user=None, priority=0):
    """Convenience function to add an image processing task."""
    return queue_manager.add_task(
        task_name=f"Process image file {image_file_id} ({processing_type})",
        task_type='image_processing',
        task_params={
            'image_file_id': image_file_id,
            'processing_type': processing_type
        },
        user=user,
        priority=priority
    )