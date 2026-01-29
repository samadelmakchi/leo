#!/usr/bin/env python3
"""
Task 15: Copy Backup Scripts
جایگزین task انسیبل: 15-copy-backup-scripts.yml
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.template_renderer import TemplateRenderer
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class CopyBackupScriptsTask(BaseTask):
    """کپی کردن scriptهای backup"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="copy_backup_scripts", config=config)
        
        self.file_mgr = FileManager()
        self.template_renderer = TemplateRenderer()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'backup_path',
            'inventory_hostname'
        ]
        
        # لیست scriptهای backup
        self.backup_scripts = ['backup_volumes', 'backup_databases']
    
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
    
    def should_deploy_backup_scripts(self) -> bool:
        """بررسی آیا باید scriptهای backup را deploy کرد"""
        customer_backup_enabled = self.config.get('customer_backup_enabled', False)
        return bool(customer_backup_enabled)
    
    def copy_backup_script(self, script_name: str) -> Dict:
        """
        کپی کردن یک script backup
        
        Args:
            script_name: نام script
            
        Returns:
            نتیجه عملیات
        """
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'script': script_name,
                    'message': "Customer state is not 'up'"
                }
            
            # بررسی backup enabled
            if not self.should_deploy_backup_scripts():
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'script': script_name,
                    'message': "Backup is disabled"
                }
            
            backup_path = self.config['backup_path']
            inventory_hostname = self.config['inventory_hostname']
            host_vars = self.config.get('host_vars', {})
            
            # مسیرهای source و destination
            src_template = Path('deployment/resources/backup_scripts') / f"{script_name}.sh.j2"
            dest_file = Path(backup_path) / inventory_hostname / f"{script_name}.sh"
            
            if not src_template.exists():
                # اگر template وجود نداشت، از backup_scripts اصلی استفاده کن
                src_template = Path('backup_scripts') / f"{script_name}.sh.j2"
            
            if not src_template.exists():
                return {
                    'success': False,
                    'error': f"Backup script template not found: {src_template}",
                    'script': script_name
                }
            
            # context برای template
            context = {
                'inventory_hostname': inventory_hostname,
                'customer_containers': self.config.get('customer_containers', inventory_hostname),
                **host_vars
            }
            
            # رندر template
            result = self.template_renderer.render_template(
                str(src_template),
                str(dest_file),
                context,
                mode=0o755,
                force=True
            )
            
            if result['success']:
                logger.info(f"Deployed backup script: {script_name} -> {dest_file}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error copying backup script {script_name}: {str(e)}"
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
            
            logger.info(f"Copying {len(self.backup_scripts)} backup scripts")
            
            # کپی کردن تمام scriptها
            results = []
            deployed_count = 0
            skipped_count = 0
            failed_count = 0
            
            for script in self.backup_scripts:
                result = self.copy_backup_script(script)
                results.append({
                    'script': script,
                    'result': result
                })
                
                if result['success']:
                    if result.get('changed', False):
                        deployed_count += 1
                    elif result.get('skipped', False):
                        skipped_count += 1
                else:
                    failed_count += 1
            
            # خلاصه نتایج
            all_success = failed_count == 0
            any_changed = deployed_count > 0
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'total_scripts': len(self.backup_scripts),
                'deployed': deployed_count,
                'skipped': skipped_count,
                'failed': failed_count,
                'customer_state': self.config.get('customer_state'),
                'backup_enabled': self.should_deploy_backup_scripts(),
                'results': results,
                'message': f"Deployed {deployed_count} backup scripts, {skipped_count} skipped, {failed_count} failed"
            }
            
            if all_success:
                logger.info(f"Backup scripts copy completed: {final_result['message']}")
                return self.complete_task(final_result)
            else:
                failed_scripts = [
                    r['script'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed to copy backup scripts: {', '.join(failed_scripts)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in copy backup scripts task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})