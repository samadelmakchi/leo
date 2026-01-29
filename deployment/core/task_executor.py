#!/usr/bin/env python3
"""
Task Executor
اجرای taskها با قابلیت‌های پیشرفته
"""

import logging
import sys
import threading
import queue
import time
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class TaskExecutor:
    """اجرای taskها با مدیریت پیشرفته"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه Task Executor
        
        Args:
            config: تنظیمات اجرا
        """
        self.config = config or {}
        self.max_workers = self.config.get('max_workers', 10)
        self.default_timeout = self.config.get('default_timeout', 300)  # 5 دقیقه
        self.task_queue = queue.Queue()
        self.running_tasks = {}
        self.task_history = []
        self.max_history_size = self.config.get('max_history_size', 1000)
        
        # Thread pool
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        
        logger.info(f"Task Executor initialized with {self.max_workers} workers")
    
    def execute_task(self, task_func: Callable, task_id: str = None, 
                    task_name: str = None, timeout: int = None, 
                    **kwargs) -> Dict:
        """
        اجرای یک task
        
        Args:
            task_func: تابع task
            task_id: ID task (اگر None باشد ساخته می‌شود)
            task_name: نام task
            timeout: timeout اجرا
            **kwargs: پارامترهای task
            
        Returns:
            نتیجه اجرا
        """
        try:
            task_id = task_id or f"task_{int(time.time())}_{hash(task_func) % 10000}"
            task_name = task_name or task_func.__name__
            timeout = timeout or self.default_timeout
            
            logger.info(f"Executing task: {task_name} (ID: {task_id})")
            
            # ثبت task در history
            task_record = {
                'task_id': task_id,
                'task_name': task_name,
                'status': 'running',
                'start_time': datetime.now().isoformat(),
                'parameters': kwargs,
                'timeout': timeout
            }
            
            self.running_tasks[task_id] = task_record
            self._add_to_history(task_record)
            
            # اجرای task با timeout
            start_time = time.time()
            
            try:
                # اجرای task در thread pool
                future = self.thread_pool.submit(task_func, **kwargs)
                result = future.result(timeout=timeout)
                execution_time = time.time() - start_time
                
                if isinstance(result, dict):
                    task_result = result
                else:
                    task_result = {
                        'success': True,
                        'result': result,
                        'execution_time': execution_time
                    }
                
                # آپدیت task record
                task_record.update({
                    'status': 'completed',
                    'end_time': datetime.now().isoformat(),
                    'execution_time': execution_time,
                    'result': task_result
                })
                
                logger.info(f"Task {task_name} completed in {execution_time:.2f} seconds")
                
                return {
                    'success': True,
                    'task_id': task_id,
                    'task_name': task_name,
                    'execution_time': execution_time,
                    'result': task_result,
                    'status': 'completed'
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"Task {task_name} failed: {str(e)}"
                
                task_record.update({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'execution_time': execution_time,
                    'error': error_msg,
                    'traceback': traceback.format_exc()
                })
                
                logger.error(f"Task {task_name} failed after {execution_time:.2f} seconds: {str(e)}")
                
                return {
                    'success': False,
                    'task_id': task_id,
                    'task_name': task_name,
                    'execution_time': execution_time,
                    'error': error_msg,
                    'status': 'failed'
                }
                
            finally:
                # حذف از running tasks
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
            
        except Exception as e:
            error_msg = f"Error executing task {task_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                'success': False,
                'task_id': task_id,
                'task_name': task_name,
                'error': error_msg,
                'status': 'failed'
            }
    
    def execute_tasks_parallel(self, tasks: List[Dict], max_parallel: int = None) -> Dict:
        """
        اجرای موازی چندین task
        
        Args:
            tasks: لیست taskها
            max_parallel: حداکثر taskهای موازی
            
        Returns:
            نتایج اجرا
        """
        try:
            max_parallel = max_parallel or self.max_workers
            total_tasks = len(tasks)
            
            logger.info(f"Executing {total_tasks} tasks in parallel (max: {max_parallel})")
            
            # آماده‌سازی tasks
            task_futures = []
            task_info = {}
            
            for task_config in tasks:
                task_func = task_config.get('function')
                task_id = task_config.get('id', f"task_{int(time.time())}_{hash(task_func) % 10000}")
                task_name = task_config.get('name', task_func.__name__)
                timeout = task_config.get('timeout', self.default_timeout)
                params = task_config.get('parameters', {})
                
                # ثبت task
                task_record = {
                    'task_id': task_id,
                    'task_name': task_name,
                    'status': 'pending',
                    'parameters': params
                }
                
                self._add_to_history(task_record)
                task_info[task_id] = task_record
                
                # ارسال task برای اجرا
                future = self.thread_pool.submit(
                    self._execute_single_task,
                    task_func, task_id, task_name, timeout, params
                )
                
                task_futures.append((future, task_id))
            
            # جمع‌آوری نتایج
            results = []
            completed = 0
            failed = 0
            
            for future, task_id in task_futures:
                try:
                    result = future.result()
                    results.append(result)
                    
                    # آپدیت task record
                    if task_id in task_info:
                        task_info[task_id].update({
                            'status': result['status'],
                            'end_time': datetime.now().isoformat(),
                            'execution_time': result.get('execution_time', 0),
                            'result': result.get('result'),
                            'error': result.get('error')
                        })
                    
                    if result['status'] == 'completed':
                        completed += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    error_result = {
                        'task_id': task_id,
                        'success': False,
                        'error': str(e),
                        'status': 'failed'
                    }
                    results.append(error_result)
                    failed += 1
            
            # خلاصه نتایج
            summary = {
                'success': failed == 0,
                'total_tasks': total_tasks,
                'completed': completed,
                'failed': failed,
                'results': results,
                'execution_time': sum(r.get('execution_time', 0) for r in results),
                'message': f"Parallel execution completed: {completed} successful, {failed} failed"
            }
            
            logger.info(f"Parallel execution completed: {summary['message']}")
            return summary
            
        except Exception as e:
            error_msg = f"Error executing tasks in parallel: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                'success': False,
                'error': error_msg,
                'total_tasks': len(tasks) if 'tasks' in locals() else 0
            }
    
    def _execute_single_task(self, task_func: Callable, task_id: str, 
                           task_name: str, timeout: int, params: Dict) -> Dict:
        """
        اجرای یک task (برای استفاده در execute_tasks_parallel)
        """
        return self.execute_task(
            task_func=task_func,
            task_id=task_id,
            task_name=task_name,
            timeout=timeout,
            **params
        )
    
    def execute_tasks_sequential(self, tasks: List[Dict], 
                               stop_on_failure: bool = False) -> Dict:
        """
        اجرای ترتیبی چندین task
        
        Args:
            tasks: لیست taskها
            stop_on_failure: توقف در صورت شکست
            
        Returns:
            نتایج اجرا
        """
        try:
            total_tasks = len(tasks)
            results = []
            
            logger.info(f"Executing {total_tasks} tasks sequentially")
            
            for i, task_config in enumerate(tasks, 1):
                task_func = task_config.get('function')
                task_id = task_config.get('id', f"seq_task_{i}_{int(time.time())}")
                task_name = task_config.get('name', task_func.__name__)
                timeout = task_config.get('timeout', self.default_timeout)
                params = task_config.get('parameters', {})
                
                logger.info(f"Executing sequential task {i}/{total_tasks}: {task_name}")
                
                # اجرای task
                result = self.execute_task(
                    task_func=task_func,
                    task_id=task_id,
                    task_name=task_name,
                    timeout=timeout,
                    **params
                )
                
                results.append(result)
                
                # بررسی اگر باید توقف کرد
                if stop_on_failure and not result['success']:
                    logger.warning(f"Stopping sequential execution due to failed task: {task_name}")
                    break
            
            # خلاصه نتایج
            completed = sum(1 for r in results if r.get('status') == 'completed')
            failed = sum(1 for r in results if r.get('status') == 'failed')
            
            summary = {
                'success': failed == 0,
                'total_tasks': total_tasks,
                'executed': len(results),
                'completed': completed,
                'failed': failed,
                'stopped_early': len(results) < total_tasks and stop_on_failure,
                'results': results,
                'execution_time': sum(r.get('execution_time', 0) for r in results),
                'message': f"Sequential execution completed: {completed} successful, {failed} failed"
            }
            
            logger.info(f"Sequential execution completed: {summary['message']}")
            return summary
            
        except Exception as e:
            error_msg = f"Error executing tasks sequentially: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                'success': False,
                'error': error_msg,
                'total_tasks': len(tasks) if 'tasks' in locals() else 0
            }
    
    def execute_with_retry(self, task_func: Callable, max_retries: int = 3,
                          retry_delay: int = 5, **kwargs) -> Dict:
        """
        اجرای task با قابلیت retry
        
        Args:
            task_func: تابع task
            max_retries: حداکثر تعداد retryها
            retry_delay: تاخیر بین retryها (ثانیه)
            **kwargs: پارامترهای task
            
        Returns:
            نتیجه نهایی
        """
        task_name = kwargs.pop('task_name', task_func.__name__)
        task_id = kwargs.pop('task_id', f"retry_task_{int(time.time())}")
        
        logger.info(f"Executing task with retry: {task_name} (max retries: {max_retries})")
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_retries} for task {task_name}")
                
                result = self.execute_task(
                    task_func=task_func,
                    task_id=f"{task_id}_attempt_{attempt}",
                    task_name=f"{task_name} (attempt {attempt})",
                    **kwargs
                )
                
                if result['success']:
                    result['attempts'] = attempt
                    result['max_retries'] = max_retries
                    logger.info(f"Task {task_name} succeeded on attempt {attempt}")
                    return result
                
                last_error = result.get('error')
                
                if attempt < max_retries:
                    logger.warning(f"Task {task_name} failed on attempt {attempt}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    logger.warning(f"Task {task_name} failed on attempt {attempt}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        
        # اگر بعد از همه retryها موفق نشد
        error_msg = f"Task {task_name} failed after {max_retries} attempts. Last error: {last_error}"
        logger.error(error_msg)
        
        return {
            'success': False,
            'task_name': task_name,
            'error': error_msg,
            'attempts': max_retries,
            'max_retries_reached': True,
            'status': 'failed'
        }
    
    def schedule_task(self, task_func: Callable, delay: int = 0,
                     task_id: str = None, **kwargs) -> str:
        """
        زمان‌بندی اجرای task
        
        Args:
            task_func: تابع task
            delay: تاخیر اجرا (ثانیه)
            task_id: ID task
            **kwargs: پارامترهای task
            
        Returns:
            ID task زمان‌بندی شده
        """
        try:
            task_id = task_id or f"scheduled_{int(time.time())}"
            task_name = kwargs.pop('task_name', task_func.__name__)
            
            def delayed_task():
                time.sleep(delay)
                return self.execute_task(
                    task_func=task_func,
                    task_id=task_id,
                    task_name=task_name,
                    **kwargs
                )
            
            # اجرای task در thread جداگانه
            thread = threading.Thread(
                target=delayed_task,
                name=f"ScheduledTask-{task_id}"
            )
            thread.daemon = True
            thread.start()
            
            # ثبت task زمان‌بندی شده
            scheduled_task = {
                'task_id': task_id,
                'task_name': task_name,
                'status': 'scheduled',
                'scheduled_time': datetime.now().isoformat(),
                'delay_seconds': delay,
                'execute_after': time.time() + delay
            }
            
            self._add_to_history(scheduled_task)
            
            logger.info(f"Task {task_name} scheduled to run in {delay} seconds (ID: {task_id})")
            
            return task_id
            
        except Exception as e:
            error_msg = f"Error scheduling task: {str(e)}"
            logger.error(error_msg)
            raise
    
    def cancel_task(self, task_id: str) -> bool:
        """
        لغو یک task
        
        Args:
            task_id: ID task
            
        Returns:
            True اگر لغو موفق باشد
        """
        # Note: در این پیاده‌سازی ساده، لغو taskهای در حال اجرا ممکن نیست
        # اما می‌توانیم وضعیت task را در history آپدیت کنیم
        try:
            for task in self.task_history:
                if task.get('task_id') == task_id and task.get('status') in ['pending', 'scheduled']:
                    task['status'] = 'cancelled'
                    task['cancelled_time'] = datetime.now().isoformat()
                    
                    logger.info(f"Task {task_id} cancelled")
                    return True
            
            logger.warning(f"Task {task_id} not found or cannot be cancelled")
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {str(e)}")
            return False
    
    def get_task_status(self, task_id: str = None) -> Dict:
        """
        دریافت وضعیت taskها
        
        Args:
            task_id: ID task خاص (اگر None باشد وضعیت کلی)
            
        Returns:
            وضعیت taskها
        """
        try:
            if task_id:
                # وضعیت task خاص
                for task in self.task_history:
                    if task.get('task_id') == task_id:
                        return {
                            'success': True,
                            'task_id': task_id,
                            'status': task.get('status', 'unknown'),
                            'task_info': task
                        }
                
                return {
                    'success': False,
                    'error': f"Task {task_id} not found",
                    'task_id': task_id
                }
            else:
                # وضعیت کلی
                running = len(self.running_tasks)
                total_history = len(self.task_history)
                
                # آمار وضعیت‌ها
                status_counts = {}
                for task in self.task_history:
                    status = task.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                recent_tasks = self.task_history[-10:] if self.task_history else []
                
                return {
                    'success': True,
                    'running_tasks': running,
                    'total_tasks_in_history': total_history,
                    'status_counts': status_counts,
                    'recent_tasks': recent_tasks,
                    'max_history_size': self.max_history_size,
                    'thread_pool_status': {
                        'max_workers': self.max_workers,
                        'active_threads': self.thread_pool._max_workers - self.thread_pool._work_queue.qsize()
                    }
                }
                
        except Exception as e:
            error_msg = f"Error getting task status: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def clear_history(self, older_than_days: int = None) -> Dict:
        """
        پاک‌سازی history
        
        Args:
            older_than_days: حذف taskهای قدیمی‌تر از این تعداد روز
            
        Returns:
            نتیجه پاک‌سازی
        """
        try:
            initial_count = len(self.task_history)
            
            if older_than_days:
                # حذف بر اساس سن
                cutoff_time = time.time() - (older_than_days * 24 * 3600)
                cutoff_date = datetime.fromtimestamp(cutoff_time).isoformat()
                
                self.task_history = [
                    task for task in self.task_history
                    if datetime.fromisoformat(task.get('start_time', '2000-01-01')).timestamp() > cutoff_time
                ]
            else:
                # حذف همه به جز 100 مورد اخیر
                self.task_history = self.task_history[-100:]
            
            removed_count = initial_count - len(self.task_history)
            
            result = {
                'success': True,
                'initial_count': initial_count,
                'remaining_count': len(self.task_history),
                'removed_count': removed_count,
                'older_than_days': older_than_days,
                'message': f"History cleared: removed {removed_count} tasks"
            }
            
            logger.info(f"Task history cleared: {removed_count} tasks removed")
            return result
            
        except Exception as e:
            error_msg = f"Error clearing task history: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _add_to_history(self, task_record: Dict):
        """
        اضافه کردن task به history
        
        Args:
            task_record: رکورد task
        """
        self.task_history.append(task_record)
        
        # محدود کردن سایز history
        if len(self.task_history) > self.max_history_size:
            self.task_history = self.task_history[-self.max_history_size:]
    
    def export_history(self, file_path: str = None) -> Dict:
        """
        export کردن history به فایل
        
        Args:
            file_path: مسیر فایل خروجی
            
        Returns:
            نتیجه export
        """
        try:
            import json
            from pathlib import Path
            
            if not file_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_path = f"task_history_{timestamp}.json"
            
            output_path = Path(file_path)
            
            # آماده‌سازی داده‌ها برای export
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_tasks': len(self.task_history),
                'tasks': self.task_history
            }
            
            # نوشتن به فایل
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            result = {
                'success': True,
                'file_path': str(output_path),
                'file_size': output_path.stat().st_size,
                'total_tasks': len(self.task_history),
                'message': f"Task history exported to {output_path}"
            }
            
            logger.info(f"Task history exported: {result['file_path']}")
            return result
            
        except Exception as e:
            error_msg = f"Error exporting task history: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'file_path': file_path
            }
    
    def shutdown(self, wait: bool = True, timeout: int = 30) -> Dict:
        """
        خاموش کردن Task Executor
        
        Args:
            wait: منتظر پایان taskهای در حال اجرا بمان
            timeout: timeout انتظار
            
        Returns:
            نتیجه shutdown
        """
        try:
            logger.info("Shutting down Task Executor...")
            
            running_tasks_count = len(self.running_tasks)
            
            if wait and running_tasks_count > 0:
                logger.info(f"Waiting for {running_tasks_count} running tasks to complete...")
                
                start_time = time.time()
                while self.running_tasks and (time.time() - start_time) < timeout:
                    time.sleep(1)
                
                if self.running_tasks:
                    logger.warning(f"Timeout waiting for {len(self.running_tasks)} tasks to complete")
            
            # خاموش کردن thread pool
            self.thread_pool.shutdown(wait=wait)
            
            result = {
                'success': True,
                'running_tasks_at_shutdown': running_tasks_count,
                'total_tasks_in_history': len(self.task_history),
                'wait_for_completion': wait,
                'timeout': timeout,
                'message': f"Task Executor shut down. Had {running_tasks_count} running tasks."
            }
            
            logger.info("Task Executor shut down successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error shutting down Task Executor: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def create_task_executor(config: Dict = None) -> TaskExecutor:
    """
    تابع helper برای ایجاد Task Executor
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از TaskExecutor
    """
    return TaskExecutor(config)