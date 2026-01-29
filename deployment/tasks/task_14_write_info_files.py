#!/usr/bin/env python3
"""
Task 14: Write Info Files
جایگزین task انسیبل: 14-write-info-files.yml
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class WriteInfoFilesTask(BaseTask):
    """نوشتن فایل‌های اطلاعاتی"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="write_info_files", config=config)
        
        self.file_mgr = FileManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'info_path',
            'inventory_hostname'
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        errors = []
        
        for param in self.required_params:
            if param not in self.config:
                errors.append(f"Missing required parameter: {param}")
        
        # بررسی متغیرهای مورد نیاز برای content
        required_vars = [
            'portal_mysql_db_name', 'portal_mysql_user', 'portal_mysql_password',
            'gateway_mysql_db_name', 'gateway_mysql_user', 'gateway_mysql_password',
            'lms_mysql_db_name', 'lms_mysql_user', 'lms_mysql_password',
            'file_mysql_db_name', 'file_mysql_user', 'file_mysql_password'
        ]
        
        missing_vars = []
        host_vars = self.config.get('host_vars', {})
        for var in required_vars:
            if var not in host_vars:
                missing_vars.append(var)
        
        if missing_vars:
            warnings = [f"Missing variable for info files: {', '.join(missing_vars)}"]
        else:
            warnings = []
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def write_volumes_info(self) -> Dict:
        """نوشتن فایل اطلاعات volumes"""
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                }
            
            info_path = self.config['info_path']
            inventory_hostname = self.config['inventory_hostname']
            
            file_path = Path(info_path) / 'volumes' / f"{inventory_hostname}.txt"
            
            # محتوای فایل volumes
            content = """# Gateway (CodeIgniter)
gateway/admin/uploads
gateway/admin/captcha_images
gateway/admin

# Portal + Portal-Frontend
portal
portal-frontend

# LMS (Laravel)
lms/storage/app/public
lms/storage/app/private
lms/storage/logs
lms/.env

# File Storage (Laravel)
file/storage/app/public
file/storage/app/private
file/storage/logs
file/.env
"""
            
            result = self.file_mgr.write_file(
                str(file_path),
                content,
                mode=0o644,
                force=True
            )
            
            if result['success']:
                logger.info(f"Wrote volumes info file: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error writing volumes info file: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def write_databases_info(self) -> Dict:
        """نوشتن فایل اطلاعات databases"""
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                }
            
            info_path = self.config['info_path']
            inventory_hostname = self.config['inventory_hostname']
            customer_containers = self.config.get('customer_containers', inventory_hostname)
            host_vars = self.config.get('host_vars', {})
            
            file_path = Path(info_path) / 'databases' / f"{inventory_hostname}.txt"
            
            # آماده کردن مقادیر با fallback
            portal_db = host_vars.get('portal_mysql_db_name', 'portal_db')
            portal_user = host_vars.get('portal_mysql_user', 'portal_user')
            portal_pass = host_vars.get('portal_mysql_password', 'password')
            
            gateway_db = host_vars.get('gateway_mysql_db_name', 'gateway_db')
            gateway_user = host_vars.get('gateway_mysql_user', 'gateway_user')
            gateway_pass = host_vars.get('gateway_mysql_password', 'password')
            
            lms_db = host_vars.get('lms_mysql_db_name', 'lms_db')
            lms_user = host_vars.get('lms_mysql_user', 'lms_user')
            lms_pass = host_vars.get('lms_mysql_password', '1234')
            
            file_db = host_vars.get('file_mysql_db_name', 'file_db')
            file_user = host_vars.get('file_mysql_user', 'file_user')
            file_pass = host_vars.get('file_mysql_password', '1234')
            
            # محتوای فایل databases
            content = f"""# Portal (Symfony)
mysql,{portal_db},{portal_user},{portal_pass},{customer_containers}-portal-db

# Gateway (CodeIgniter)
mysql,{gateway_db},{gateway_user},{gateway_pass},{customer_containers}-gateway-db

# LMS (Laravel)
mysql,{lms_db},{lms_user},{lms_pass},{customer_containers}-lms-db

# File Storage (Laravel)
mysql,{file_db},{file_user},{file_pass},{customer_containers}-file-db
"""
            
            result = self.file_mgr.write_file(
                str(file_path),
                content,
                mode=0o644,
                force=True
            )
            
            if result['success']:
                logger.info(f"Wrote databases info file: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error writing databases info file: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
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
            
            # نمایش warnings
            if validation['warnings']:
                for warning in validation['warnings']:
                    logger.warning(warning)
            
            # اجرای مراحل
            results = []
            
            # 1. نوشتن فایل volumes info
            volumes_result = self.write_volumes_info()
            results.append({
                'step': 'write_volumes_info',
                'result': volumes_result
            })
            
            # 2. نوشتن فایل databases info
            databases_result = self.write_databases_info()
            results.append({
                'step': 'write_databases_info',
                'result': databases_result
            })
            
            # خلاصه نتایج
            all_success = all(
                r['result']['success'] or r['result'].get('skipped', False)
                for r in results
            )
            any_changed = any(
                r['result'].get('changed', False) 
                for r in results
            )
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'steps': results,
                'customer_state': self.config.get('customer_state'),
                'info_path': self.config.get('info_path'),
                'inventory_hostname': self.config.get('inventory_hostname')
            }
            
            if all_success:
                logger.info("Info files written successfully")
                return self.complete_task(final_result)
            else:
                failed_steps = [
                    r['step'] for r in results 
                    if not r['result']['success'] and not r['result'].get('skipped', False)
                ]
                error_msg = f"Failed steps: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in write info files task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})