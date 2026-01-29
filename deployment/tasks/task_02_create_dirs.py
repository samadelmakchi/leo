#!/usr/bin/env python3
"""
Task 02: Create Directories
جایگزین task انسیبل: 02-create-dirs.yml
"""

import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class CreateDirsTask(BaseTask):
    """ایجاد دایرکتوری‌های مورد نیاز"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="create_dirs", config=config)
        
        self.file_mgr = FileManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'project_path',
            'inventory_hostname'
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        errors = []
        
        for param in self.required_params:
            if param not in self.config:
                errors.append(f"Missing required parameter: {param}")
        
        # بررسی مسیرها
        project_path = self.config.get('project_path')
        if project_path and not isinstance(project_path, str):
            errors.append("project_path must be a string")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
    
    def create_base_project_dir(self) -> Dict:
        """
        ایجاد دایرکتوری اصلی پروژه
        معادل: Ensure base project directory exists
        """
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                }
            
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            base_dir = Path(project_path) / inventory_hostname
            mode = 0o755
            
            result = self.file_mgr.create_directory(
                str(base_dir),
                mode=mode,
                force=True
            )
            
            if result['success']:
                if result['created']:
                    logger.info(f"Created base project directory: {base_dir}")
                else:
                    logger.debug(f"Base project directory already exists: {base_dir}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error creating base project directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def create_global_directories(self) -> Dict:
        """
        ایجاد دایرکتوری‌های global
        معادل: Ensure other global directories
        """
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                }
            
            # دریافت پارامترها
            backup_path = self.config.get('backup_path', '/backup')
            log_path = self.config.get('log_path', '/var/log')
            info_path = self.config.get('info_path', '/info')
            inventory_hostname = self.config['inventory_hostname']
            
            # لیست دایرکتوری‌ها
            directories = [
                Path(backup_path) / inventory_hostname,
                Path(log_path) / 'backup',
                Path(log_path) / 'test-reports' / inventory_hostname,
                Path(info_path) / 'volumes',
                Path(info_path) / 'databases'
            ]
            
            results = []
            created_count = 0
            
            for dir_path in directories:
                try:
                    result = self.file_mgr.create_directory(
                        str(dir_path),
                        mode=0o755,
                        force=True,
                        recurse=True
                    )
                    
                    results.append({
                        'directory': str(dir_path),
                        'result': result
                    })
                    
                    if result.get('created'):
                        created_count += 1
                        logger.info(f"Created directory: {dir_path}")
                    else:
                        logger.debug(f"Directory already exists: {dir_path}")
                        
                except Exception as e:
                    logger.error(f"Error creating directory {dir_path}: {str(e)}")
                    results.append({
                        'directory': str(dir_path),
                        'error': str(e)
                    })
            
            # خلاصه نتایج
            success_results = [r for r in results if 'result' in r and r['result']['success']]
            failed_results = [r for r in results if 'error' in r]
            
            final_result = {
                'success': len(failed_results) == 0,
                'changed': created_count > 0,
                'directories_processed': len(directories),
                'directories_created': created_count,
                'results': results
            }
            
            if final_result['success']:
                logger.info(f"Created {created_count} global directories")
            else:
                logger.warning(f"Failed to create {len(failed_results)} directories")
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error creating global directories: {str(e)}"
            logger.error(error_msg, exc_info=True)
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
            
            # اجرای مراحل
            results = []
            
            # 1. ایجاد دایرکتوری اصلی پروژه
            base_dir_result = self.create_base_project_dir()
            results.append({
                'step': 'create_base_project_dir',
                'result': base_dir_result
            })
            
            # 2. ایجاد دایرکتوری‌های global
            global_dirs_result = self.create_global_directories()
            results.append({
                'step': 'create_global_directories',
                'result': global_dirs_result
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
                'project_path': self.config.get('project_path'),
                'inventory_hostname': self.config.get('inventory_hostname')
            }
            
            if all_success:
                logger.info("Directory creation completed successfully")
                return self.complete_task(final_result)
            else:
                failed_steps = [
                    r['step'] for r in results 
                    if not r['result']['success'] and not r['result'].get('skipped', False)
                ]
                error_msg = f"Failed steps: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in create directories task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})


# تابع helper برای اجرای سریع
def create_project_directories(
    customer_state: str,
    project_path: str,
    inventory_hostname: str,
    **kwargs
) -> Dict:
    """
    تابع helper برای ایجاد دایرکتوری‌های پروژه
    
    Args:
        customer_state: حالت مشتری ('up' یا 'down')
        project_path: مسیر اصلی پروژه
        inventory_hostname: نام host در inventory
        **kwargs: پارامترهای اضافی
        
    Returns:
        نتیجه اجرا
    """
    config = {
        'customer_state': customer_state,
        'project_path': project_path,
        'inventory_hostname': inventory_hostname,
        **kwargs
    }
    
    task = CreateDirsTask(config)
    return task.execute()


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Create Directories Task")
    parser.add_argument('--customer-state', required=True,
                       choices=['up', 'down'],
                       help='Customer state')
    parser.add_argument('--project-path', required=True,
                       help='Base project path')
    parser.add_argument('--inventory-hostname', required=True,
                       help='Inventory hostname')
    parser.add_argument('--backup-path', default='/backup',
                       help='Backup path (default: /backup)')
    parser.add_argument('--log-path', default='/var/log',
                       help='Log path (default: /var/log)')
    parser.add_argument('--info-path', default='/info',
                       help='Info path (default: /info)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    # تنظیم logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # اجرای task
    config = vars(args)
    task = CreateDirsTask(config)
    result = task.execute()
    
    # نمایش نتیجه
    print(json.dumps(result, indent=2, default=str))
    
    # خروجی مناسب
    sys.exit(0 if result.get('success') else 1)