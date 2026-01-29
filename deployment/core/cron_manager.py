#!/usr/bin/env python3
"""
Cron Manager
مدیریت cron jobها
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


class CronManager:
    """مدیریت cron jobها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه Cron Manager
        
        Args:
            config: تنظیمات
        """
        self.config = config or {}
        self.cron_user = self.config.get('cron_user', 'root')
        
        logger.info("Cron Manager initialized")
    
    def _run_crontab_command(self, args: List[str], input_data: str = None) -> Dict:
        """
        اجرای دستور crontab
        
        Args:
            args: آرگومان‌های دستور
            input_data: داده ورودی (برای crontab -)
            
        Returns:
            نتیجه اجرا
        """
        try:
            cmd = ['crontab'] + args
            
            logger.debug(f"Running crontab command: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            result = {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip()
            }
            
            if not result['success']:
                logger.error(f"Crontab command failed: {result['stderr']}")
            
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = "Crontab command timeout"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'timeout': True
            }
        except Exception as e:
            error_msg = f"Error running crontab command: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_current_crontab(self, user: str = None) -> Dict:
        """
        دریافت crontab فعلی
        
        Args:
            user: کاربر (اگر None باشد از cron_user استفاده می‌شود)
            
        Returns:
            crontab فعلی
        """
        try:
            user = user or self.cron_user
            
            if user != 'root':
                args = ['-u', user, '-l']
            else:
                args = ['-l']
            
            result = self._run_crontab_command(args)
            
            if result['success']:
                crontab_content = result['stdout']
                jobs = self._parse_crontab(crontab_content)
                
                return {
                    'success': True,
                    'user': user,
                    'content': crontab_content,
                    'jobs': jobs,
                    'jobs_count': len(jobs)
                }
            else:
                # اگر crontab خالی باشد ممکن است خطا برگرداند
                if "no crontab for" in result['stderr'].lower():
                    return {
                        'success': True,
                        'user': user,
                        'content': '',
                        'jobs': [],
                        'jobs_count': 0,
                        'message': 'No crontab for user'
                    }
                return result
            
        except Exception as e:
            error_msg = f"Error getting crontab for user {user}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user': user
            }
    
    def _parse_crontab(self, crontab_content: str) -> List[Dict]:
        """
        پارس کردن محتوای crontab
        
        Args:
            crontab_content: محتوای crontab
            
        Returns:
            لیست jobها
        """
        jobs = []
        
        for line in crontab_content.split('\n'):
            line = line.strip()
            
            # خطوط خالی یا کامنت
            if not line or line.startswith('#'):
                continue
            
            # خطوط تنظیمات (مانند SHELL, PATH, MAILTO)
            if line.startswith(('SHELL=', 'PATH=', 'MAILTO=', 'HOME=')):
                continue
            
            # تجزیه خط cron job
            # فرمت: minute hour day month weekday command
            parts = line.split(None, 5)
            
            if len(parts) >= 6:
                minute, hour, day, month, weekday, command = parts
                
                # استخراج نام job از کامنت قبلی (اگر وجود دارد)
                job_name = None
                
                jobs.append({
                    'schedule': f"{minute} {hour} {day} {month} {weekday}",
                    'command': command,
                    'name': job_name,
                    'line': line
                })
        
        return jobs
    
    def set_job(self, name: str, command: str, minute: str = '*', hour: str = '*',
                day: str = '*', month: str = '*', weekday: str = '*', user: str = None) -> Dict:
        """
        تنظیم یک cron job
        
        Args:
            name: نام job
            command: دستور
            minute: دقیقه
            hour: ساعت
            day: روز ماه
            month: ماه
            weekday: روز هفته
            user: کاربر
            
        Returns:
            نتیجه عملیات
        """
        try:
            user = user or self.cron_user
            
            # دریافت crontab فعلی
            current_crontab = self.get_current_crontab(user)
            if not current_crontab['success']:
                return current_crontab
            
            # ساخت خط جدید cron job
            new_job_line = f"{minute} {hour} {day} {month} {weekday} {command}"
            
            # اگر job با همین نام وجود دارد، آن را حذف کن
            updated_jobs = []
            job_exists = False
            
            for job in current_crontab.get('jobs', []):
                if job.get('name') == name:
                    # job با همین نام پیدا شد، جایگزین می‌کنیم
                    updated_jobs.append({
                        'schedule': f"{minute} {hour} {day} {month} {weekday}",
                        'command': command,
                        'name': name,
                        'line': new_job_line
                    })
                    job_exists = True
                else:
                    updated_jobs.append(job)
            
            # اگر job وجود نداشت، اضافه کن
            if not job_exists:
                updated_jobs.append({
                    'schedule': f"{minute} {hour} {day} {month} {weekday}",
                    'command': command,
                    'name': name,
                    'line': new_job_line
                })
            
            # ساخت محتوای crontab جدید
            new_crontab_lines = []
            
            # اضافه کردن تنظیمات اولیه
            new_crontab_lines.append('SHELL=/bin/bash')
            new_crontab_lines.append('PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin')
            new_crontab_lines.append('MAILTO=""')
            new_crontab_lines.append('')
            
            # اضافه کردن jobها
            for job in updated_jobs:
                new_crontab_lines.append(job['line'])
            
            new_crontab = '\n'.join(new_crontab_lines) + '\n'
            
            # اعمال crontab جدید
            if user != 'root':
                args = ['-u', user, '-']
            else:
                args = ['-']
            
            result = self._run_crontab_command(args, new_crontab)
            
            if result['success']:
                logger.info(f"Cron job set: {name} for user {user}")
                return {
                    'success': True,
                    'changed': True,
                    'user': user,
                    'job_name': name,
                    'job_line': new_job_line,
                    'action': 'updated' if job_exists else 'added',
                    'message': f"Cron job {'updated' if job_exists else 'added'} successfully"
                }
            else:
                return result
            
        except Exception as e:
            error_msg = f"Error setting cron job {name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'job_name': name,
                'user': user
            }
    
    def remove_job(self, name: str, user: str = None) -> Dict:
        """
        حذف یک cron job
        
        Args:
            name: نام job
            user: کاربر
            
        Returns:
            نتیجه عملیات
        """
        try:
            user = user or self.cron_user
            
            # دریافت crontab فعلی
            current_crontab = self.get_current_crontab(user)
            if not current_crontab['success']:
                return current_crontab
            
            # فیلتر کردن job با نام داده شده
            updated_jobs = []
            job_found = False
            
            for job in current_crontab.get('jobs', []):
                if job.get('name') == name:
                    job_found = True
                else:
                    updated_jobs.append(job)
            
            if not job_found:
                return {
                    'success': True,
                    'changed': False,
                    'user': user,
                    'job_name': name,
                    'message': 'Cron job not found, nothing to remove'
                }
            
            # ساخت محتوای crontab جدید
            new_crontab_lines = []
            
            # اضافه کردن تنظیمات اولیه
            new_crontab_lines.append('SHELL=/bin/bash')
            new_crontab_lines.append('PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin')
            new_crontab_lines.append('MAILTO=""')
            new_crontab_lines.append('')
            
            # اضافه کردن jobهای باقی‌مانده
            for job in updated_jobs:
                new_crontab_lines.append(job['line'])
            
            new_crontab = '\n'.join(new_crontab_lines) + '\n'
            
            # اعمال crontab جدید
            if user != 'root':
                args = ['-u', user, '-']
            else:
                args = ['-']
            
            result = self._run_crontab_command(args, new_crontab)
            
            if result['success']:
                logger.info(f"Cron job removed: {name} for user {user}")
                return {
                    'success': True,
                    'changed': True,
                    'user': user,
                    'job_name': name,
                    'removed': True,
                    'message': 'Cron job removed successfully'
                }
            else:
                return result
            
        except Exception as e:
            error_msg = f"Error removing cron job {name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'job_name': name,
                'user': user
            }
    
    def list_jobs(self, user: str = None) -> Dict:
        """
        لیست cron jobها
        
        Args:
            user: کاربر
            
        Returns:
            لیست jobها
        """
        try:
            user = user or self.cron_user
            
            current_crontab = self.get_current_crontab(user)
            
            if not current_crontab['success']:
                return current_crontab
            
            return {
                'success': True,
                'user': user,
                'jobs': current_crontab.get('jobs', []),
                'total_jobs': len(current_crontab.get('jobs', []))
            }
            
        except Exception as e:
            error_msg = f"Error listing cron jobs for user {user}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'user': user
            }
    
    def validate_cron_schedule(self, schedule: str) -> Dict:
        """
        اعتبارسنجی cron schedule
        
        Args:
            schedule: cron schedule (مثلا "0 2 * * *")
            
        Returns:
            نتیجه اعتبارسنجی
        """
        try:
            parts = schedule.split()
            
            if len(parts) != 5:
                return {
                    'valid': False,
                    'error': f"Invalid cron schedule format. Expected 5 parts, got {len(parts)}",
                    'schedule': schedule
                }
            
            minute, hour, day, month, weekday = parts
            
            # اعتبارسنجی دقیقه (0-59)
            if not self._validate_cron_part(minute, 0, 59):
                return {
                    'valid': False,
                    'error': f"Invalid minute: {minute}",
                    'schedule': schedule
                }
            
            # اعتبارسنجی ساعت (0-23)
            if not self._validate_cron_part(hour, 0, 23):
                return {
                    'valid': False,
                    'error': f"Invalid hour: {hour}",
                    'schedule': schedule
                }
            
            # اعتبارسنجی روز ماه (1-31)
            if not self._validate_cron_part(day, 1, 31):
                return {
                    'valid': False,
                    'error': f"Invalid day: {day}",
                    'schedule': schedule
                }
            
            # اعتبارسنجی ماه (1-12)
            if not self._validate_cron_part(month, 1, 12):
                return {
                    'valid': False,
                    'error': f"Invalid month: {month}",
                    'schedule': schedule
                }
            
            # اعتبارسنجی روز هفته (0-7 که 0 و 7 هر دو یکشنبه هستند)
            if not self._validate_cron_part(weekday, 0, 7):
                return {
                    'valid': False,
                    'error': f"Invalid weekday: {weekday}",
                    'schedule': schedule
                }
            
            return {
                'valid': True,
                'schedule': schedule,
                'parts': {
                    'minute': minute,
                    'hour': hour,
                    'day': day,
                    'month': month,
                    'weekday': weekday
                }
            }
            
        except Exception as e:
            error_msg = f"Error validating cron schedule {schedule}: {str(e)}"
            logger.error(error_msg)
            return {
                'valid': False,
                'error': error_msg,
                'schedule': schedule
            }
    
    def _validate_cron_part(self, part: str, min_val: int, max_val: int) -> bool:
        """
        اعتبارسنجی یک قسمت cron
        
        Args:
            part: قسمت cron
            min_val: حداقل مقدار
            max_val: حداکثر مقدار
            
        Returns:
            True اگر معتبر باشد
        """
        if part == '*':
            return True
        
        # بررسی لیست (مثلا 1,3,5)
        if ',' in part:
            subparts = part.split(',')
            return all(self._validate_cron_part(subpart.strip(), min_val, max_val) for subpart in subparts)
        
        # بررسی بازه (مثلا 1-5)
        if '-' in part:
            try:
                start, end = part.split('-')
                start_val = int(start.strip())
                end_val = int(end.strip())
                return min_val <= start_val <= max_val and min_val <= end_val <= max_val and start_val <= end_val
            except ValueError:
                return False
        
        # بررسی step (مثلا */5)
        if '/' in part:
            try:
                if part.startswith('*/'):
                    step = int(part[2:])
                    return 1 <= step <= max_val
                else:
                    range_part, step_part = part.split('/')
                    step = int(step_part.strip())
                    
                    # اعتبارسنجی range_part
                    if '-' in range_part:
                        start, end = range_part.split('-')
                        start_val = int(start.strip())
                        end_val = int(end.strip())
                        return (min_val <= start_val <= max_val and 
                                min_val <= end_val <= max_val and 
                                start_val <= end_val and 
                                1 <= step <= (end_val - start_val + 1))
                    else:
                        value = int(range_part.strip())
                        return min_val <= value <= max_val and 1 <= step <= max_val
            except ValueError:
                return False
        
        # بررسی مقدار ساده
        try:
            value = int(part)
            return min_val <= value <= max_val
        except ValueError:
            return False


# تابع helper برای استفاده آسان
def create_cron_manager(config: Dict = None) -> CronManager:
    """
    تابع helper برای ایجاد Cron Manager
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از CronManager
    """
    return CronManager(config)


if __name__ == "__main__":
    # تست Cron Manager
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # ایجاد Cron Manager
    manager = CronManager({'cron_user': 'root'})
    
    # تست دریافت crontab فعلی
    print("Getting current crontab...")
    result = manager.get_current_crontab()
    print(json.dumps(result, indent=2))
    
    # تست اعتبارسنجی cron schedule
    print("\nValidating cron schedules...")
    test_schedules = [
        "0 2 * * *",
        "*/5 * * * *",
        "0 0 1 * *",
        "invalid schedule"
    ]
    
    for schedule in test_schedules:
        validation = manager.validate_cron_schedule(schedule)
        print(f"{schedule}: {validation['valid']}")
    
    # تست تنظیم cron job
    print("\nSetting test cron job...")
    set_result = manager.set_job(
        name="Test Backup Job",
        command="/bin/echo 'Test' >> /tmp/test-cron.log",
        minute="0",
        hour="3",
        day="*",
        month="*",
        weekday="*"
    )
    print(json.dumps(set_result, indent=2))
    
    # تست لیست jobها
    print("\nListing cron jobs...")
    list_result = manager.list_jobs()
    print(json.dumps(list_result, indent=2))
    
    # تست حذف job
    print("\nRemoving test cron job...")
    remove_result = manager.remove_job("Test Backup Job")
    print(json.dumps(remove_result, indent=2))