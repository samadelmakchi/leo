#!/usr/bin/env python3
"""
Task 09: Pre-deploy Backup
جایگزین task انسیبل: 09-pre-deploy-backup.yml
"""

import logging
import sys
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class PreDeployBackupTask(BaseTask):
    """اجرای backup قبل از deploy"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="pre_deploy_backup", config=config)
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'backup_path',
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
    
    def run_backup_script(self, script_name: str) -> Dict:
        """
        اجرای یک script backup
        
        Args:
            script_name: نام script (بدون پسوند .sh)
            
        Returns:
            نتیجه اجرا
        """
        try:
            backup_path = self.config['backup_path']
            inventory_hostname = self.config['inventory_hostname']
            
            script_path = Path(backup_path) / inventory_hostname / f"{script_name}.sh"
            
            if not script_path.exists():
                return {
                    'success': False,
                    'error': f"Backup script not found: {script_path}",
                    'skipped': True
                }
            
            # بررسی permissions
            if not os.access(script_path, os.X_OK):
                os.chmod(script_path, 0o755)
            
            # اجرای script
            cmd = ['bash', str(script_path)]
            
            logger.info(f"Running backup script: {script_name}")
            
            # اجرای async با timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # زمان‌بندی برای timeout
            timeout = 1800  # 30 دقیقه
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
                
                result = {
                    'success': returncode == 0,
                    'script': script_name,
                    'returncode': returncode,
                    'stdout': stdout.strip(),
                    'stderr': stderr.strip(),
                    'message': f"Backup script {script_name} completed"
                    if returncode == 0 else f"Backup script {script_name} failed"
                }
                
                if result['success']:
                    logger.info(f"Backup {script_name} completed successfully")
                else:
                    logger.warning(f"Backup {script_name} failed with returncode {returncode}")
                
                return result
                
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                
                return {
                    'success': False,
                    'script': script_name,
                    'error': f"Backup script timed out after {timeout} seconds",
                    'stdout': stdout.strip() if stdout else '',
                    'stderr': stderr.strip() if stderr else '',
                    'timeout': True
                }
            
        except Exception as e:
            error_msg = f"Error running backup script {script_name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'script': script_name,
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
            
            # بررسی customer_state
            if self.config.get('customer_state') != 'up':
                logger.info("Customer state is not 'up', skipping pre-deploy backup")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                })
            
            # بررسی backup enabled
            customer_backup_enabled = self.config.get('customer_backup_enabled', False)
            if not customer_backup_enabled:
                logger.info("Backup is disabled, skipping pre-deploy backup")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Backup is disabled"
                })
            
            # لیست scriptهای backup
            backup_scripts = ['backup_volumes', 'backup_databases']
            
            # اجرای همزمان scriptها
            results = []
            threads = []
            
            def run_script_and_store_result(script_name, results_list):
                result = self.run_backup_script(script_name)
                results_list.append({
                    'script': script_name,
                    'result': result
                })
            
            for script in backup_scripts:
                thread = threading.Thread(
                    target=run_script_and_store_result,
                    args=(script, results)
                )
                threads.append(thread)
                thread.start()
                logger.debug(f"Started backup thread for {script}")
            
            # منتظر تمام شدن همه threadها بمان
            for thread in threads:
                thread.join()
            
            # خلاصه نتایج
            success_count = sum(1 for r in results if r['result']['success'] or r['result'].get('skipped', False))
            failed_count = len(results) - success_count
            any_changed = any(r['result'].get('changed', False) for r in results)
            
            final_result = {
                'success': failed_count == 0,
                'changed': any_changed,
                'scripts_executed': len(backup_scripts),
                'successful': success_count,
                'failed': failed_count,
                'results': results,
                'customer_state': self.config.get('customer_state'),
                'backup_enabled': customer_backup_enabled,
                'inventory_hostname': self.config.get('inventory_hostname'),
                'message': f"Executed {len(backup_scripts)} backup scripts, {success_count} successful"
            }
            
            if final_result['success']:
                logger.info("Pre-deploy backup completed successfully")
                return self.complete_task(final_result)
            else:
                failed_scripts = [
                    r['script'] for r in results 
                    if not r['result']['success'] and not r['result'].get('skipped', False)
                ]
                error_msg = f"Failed backup scripts: {', '.join(failed_scripts)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in pre-deploy backup task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})