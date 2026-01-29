#!/usr/bin/env python3
"""
Task 16: Setup Cron Jobs
جایگزین task انسیبل: 16-setup-cron.yml
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.cron_manager import CronManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class SetupCronTask(BaseTask):
    """تنظیم cron jobها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="setup_cron", config=config)
        
        self.cron_mgr = CronManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'backup_path',
            'log_path',
            'inventory_hostname'
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        errors = []
        
        for param in self.required_params:
            if param not in self.config:
                errors.append(f"Missing required parameter: {param}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
    
    def should_setup_cron(self) -> bool:
        """بررسی آیا باید cron jobs را setup کرد"""
        customer_backup_enabled = self.config.get('customer_backup_enabled', False)
        return bool(customer_backup_enabled)
    
    def setup_cron_job(self, job_config: Dict) -> Dict:
        """
        تنظیم یک cron job
        
        Args:
            job_config: تنظیمات job
            
        Returns:
            نتیجه عملیات
        """
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'job': job_config['name'],
                    'message': "Customer state is not 'up'"
                }
            
            # بررسی backup enabled
            if not self.should_setup_cron():
                # اگر backup disabled است، cron jobها را حذف کن
                return self.remove_cron_job(job_config)
            
            backup_path = self.config['backup_path']
            log_path = self.config['log_path']
            inventory_hostname = self.config['inventory_hostname']
            host_vars = self.config.get('host_vars', {})
            
            job_name = f"{job_config['name']} ({inventory_hostname})"
            cron_schedule = host_vars.get(job_config['cron_var'])
            
            if not cron_schedule:
                logger.warning(f"No cron schedule found for {job_config['name']}, using default")
                cron_schedule = job_config.get('default_cron', '0 2 * * *')
            
            # تجزیه cron schedule
            cron_parts = cron_schedule.split()
            if len(cron_parts) < 5:
                cron_parts = cron_parts + ['*'] * (5 - len(cron_parts))
            
            minute, hour, day, month, weekday = cron_parts[:5]
            
            # ساختن command
            script_name = job_config['script']
            script_path = Path(backup_path) / inventory_hostname / f"{script_name}.sh"
            log_file = Path(log_path) / 'backup' / 'cron.log'
            
            # اطمینان از وجود دایرکتوری log
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            command = f"/bin/bash {script_path} >> {log_file} 2>&1"
            
            # تنظیم cron job
            result = self.cron_mgr.set_job(
                name=job_name,
                command=command,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                weekday=weekday,
                user='root'
            )
            
            if result['success']:
                logger.info(f"Setup cron job: {job_name} with schedule {cron_schedule}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error setting up cron job {job_config.get('name', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'job': job_config.get('name', 'unknown'),
                'error': error_msg
            }
    
    def remove_cron_job(self, job_config: Dict) -> Dict:
        """
        حذف یک cron job
        
        Args:
            job_config: تنظیمات job
            
        Returns:
            نتیجه عملیات
        """
        try:
            inventory_hostname = self.config['inventory_hostname']
            job_name = f"{job_config['name']} ({inventory_hostname})"
            
            result = self.cron_mgr.remove_job(job_name)
            
            if result['success']:
                if result.get('removed', False):
                    logger.info(f"Removed cron job: {job_name}")
                else:
                    logger.debug(f"Cron job not found: {job_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error removing cron job {job_config.get('name', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'job': job_config.get('name', 'unknown'),
                'error': error_msg
            }
    
    def execute(self, **kwargs) -> Dict:
        """اجرای اصلی task"""
        if kwargs:
            self.config.update(kwargs)
        
        self.start_task()
        
        try:
            # اعتبارسنجی
            validation = self.validate_parameters()
            if not validation['valid']:
                return self.fail_task(
                    f"Validation failed: {validation['errors']}",
                    validation
                )
            
            # تعریف cron jobها
            cron_jobs = [
                {
                    'name': 'Backup Volumes',
                    'script': 'backup_volumes',
                    'cron_var': 'customer_backup_cron_volumes',
                    'default_cron': '0 2 * * *'
                },
                {
                    'name': 'Backup Databases',
                    'script': 'backup_databases',
                    'cron_var': 'customer_backup_cron_databases',
                    'default_cron': '30 2 * * *'
                }
            ]
            
            logger.info(f"Setting up {len(cron_jobs)} cron jobs")
            
            # تنظیم یا حذف cron jobها
            results = []
            setup_count = 0
            removed_count = 0
            skipped_count = 0
            failed_count = 0
            
            for job_config in cron_jobs:
                if self.should_setup_cron():
                    result = self.setup_cron_job(job_config)
                else:
                    result = self.remove_cron_job(job_config)
                
                results.append({
                    'job': job_config['name'],
                    'result': result
                })
                
                if result['success']:
                    if result.get('changed', False):
                        if self.should_setup_cron():
                            setup_count += 1
                        else:
                            removed_count += 1
                    elif result.get('skipped', False):
                        skipped_count += 1
                else:
                    failed_count += 1
            
            # خلاصه نتایج
            all_success = failed_count == 0
            any_changed = setup_count > 0 or removed_count > 0
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'total_jobs': len(cron_jobs),
                'setup': setup_count,
                'removed': removed_count,
                'skipped': skipped_count,
                'failed': failed_count,
                'backup_enabled': self.should_setup_cron(),
                'customer_state': self.config.get('customer_state'),
                'results': results,
                'message': f"Setup {setup_count}, removed {removed_count} cron jobs"
                if self.should_setup_cron() else f"Removed {removed_count} cron jobs"
            }
            
            if all_success:
                logger.info(f"Cron setup completed: {final_result['message']}")
                return self.complete_task(final_result)
            else:
                failed_jobs = [
                    r['job'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed to process cron jobs: {', '.join(failed_jobs)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in setup cron task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})