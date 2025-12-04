from django.apps import AppConfig
import os
import logging

logger = logging.getLogger(__name__)


class FileProcessorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'file_processor'
    
    def ready(self):
        """
        Django应用启动时初始化队列系统。
        """
        # 只在主进程中启动队列，避免在迁移命令中启动
        # RUN_MAIN环境变量由Django开发服务器设置
        # Gunicorn等生产服务器需要其他方式处理
        
        run_main = os.environ.get('RUN_MAIN')
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        
        # 检查是否应该启动队列
        should_start = (
            run_main == 'true' or  # Django开发服务器主进程
            (run_main is None and django_settings and 'migrate' not in os.sys.argv and 'makemigrations' not in os.sys.argv)
        )
        
        if should_start:
            try:
                # 导入队列系统以初始化所有组件
                from .queue import initialization
                
                # 确保任务处理器已注册
                logger.info("Task handlers registered successfully")
                
                # 获取队列管理器
                queue_manager = initialization.queue_manager
                
                # 延迟启动，确保Django完全加载
                import threading
                
                def delayed_queue_start():
                    import time
                    time.sleep(2)  # 等待2秒确保Django完全启动
                    try:
                        queue_manager.start()
                        logger.info("Queue manager started successfully")
                    except Exception as e:
                        logger.error(f"Failed to start queue manager: {e}")
                
                # 在单独线程中启动，避免阻塞Django启动
                start_thread = threading.Thread(target=delayed_queue_start, daemon=True)
                start_thread.start()
                
            except ImportError as e:
                # 如果队列模块不可用，记录警告但不阻止应用启动
                logger.warning(f"Queue system not available: {e}")
            except Exception as e:
                # 其他错误也记录但不阻止应用启动
                logger.error(f"Error initializing queue system: {e}")
        
        logger.info(f"FileProcessor app ready (queue startup: {'yes' if should_start else 'no'})")
