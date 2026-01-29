# deployment/core/task_base.py
"""
کلاس پایه برای تمام task ها
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseTask(ABC):
    """کلاس پایه abstract برای تمام task های استقرار"""
    
    def __init__(self, task_name: str, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه task
        
        Args:
            task_name: نام task
            config: تنظیمات task
        """
        self.task_name = task_name
        self.config = config or {}
        self.task_id = str(uuid.uuid4())[:8]
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.result = None
        
        logger.debug(f"Initialized task: {task_name} (ID: {self.task_id})")
    
    def start_task(self) -> None:
        """علامت‌گذاری شروع task"""
        self.start_time = datetime.now()
        logger.info(f"Starting task: {self.task_name} (ID: {self.task_id})")
    
    def complete_task(self, result: Dict) -> Dict:
        """
        تکمیل موفق task
        
        Args:
            result: نتیجه task
            
        Returns:
            Dict: نتیجه کامل شده
        """
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.result = result
        
        # اضافه کردن metadata
        result.update({
            'task_id': self.task_id,
            'task_name': self.task_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': self.duration,
            'status': 'completed'
        })
        
        logger.info(
            f"Task {self.task_name} completed in {self.duration:.2f} seconds "
            f"(ID: {self.task_id})"
        )
        
        return result
    
    def fail_task(self, error_message: str, error_details: Dict = None) -> Dict:
        """
        شکست task
        
        Args:
            error_message: پیام خطا
            error_details: جزئیات خطا
            
        Returns:
            Dict: نتیجه شکست
        """
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        
        error_details = error_details or {}
        
        result = {
            'success': False,
            'error': error_message,
            'task_id': self.task_id,
            'task_name': self.task_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat(),
            'duration_seconds': self.duration,
            'status': 'failed',
            'error_details': error_details
        }
        
        self.result = result
        
        logger.error(
            f"Task {self.task_name} failed after {self.duration:.2f} seconds "
            f"(ID: {self.task_id}): {error_message}"
        )
        
        return result
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict:
        """
        اجرای اصلی task (متد abstract)
        
        Args:
            **kwargs: پارامترهای اضافی
            
        Returns:
            Dict: نتیجه اجرا
        """
        pass
    
    def get_task_summary(self) -> Dict:
        """
        دریافت خلاصه task
        
        Returns:
            Dict: خلاصه task
        """
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration,
            'status': 'running' if self.start_time and not self.end_time else
                     'completed' if self.result and self.result.get('success') else
                     'failed' if self.result and not self.result.get('success') else
                     'pending'
        }