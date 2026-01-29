#!/usr/bin/env python3
"""
Task 04: Ensure Project Directories
جایگزین task انسیبل: 04-ensure-project-dirs.yml
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.task_base import BaseTask
from deployment.tasks.task_03_define_projects import get_projects_list

logger = logging.getLogger(__name__)


class EnsureProjectDirsTask(BaseTask):
    """اطمینان از وجود دایرکتوری‌های پروژه"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="ensure_project_dirs", config=config)
        
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
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
    
    def ensure_all_project_dirs(self) -> Dict:
        """
        ایجاد دایرکتوری‌های همه پروژه‌ها
        معادل: Ensure ALL required project directories exist
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            # دریافت لیست پروژه‌ها
            projects = get_projects_list(self.config)
            
            # لیست folderهای مورد نیاز (حتی اگر project در config نباشد)
            required_folders = [
                {'folder': 'gateway'},
                {'folder': 'portal'},
                {'folder': 'portal-frontend'},
                {'folder': 'file'},
                {'folder': 'lms'}
            ]
            
            results = []
            created_count = 0
            
            for folder_info in required_folders:
                folder = folder_info['folder']
                dir_path = Path(project_path) / inventory_hostname / folder
                
                try:
                    result = self.file_mgr.create_directory(
                        str(dir_path),
                        mode=0o755,
                        force=True
                    )
                    
                    results.append({
                        'folder': folder,
                        'directory': str(dir_path),
                        'result': result
                    })
                    
                    if result.get('created'):
                        created_count += 1
                        logger.info(f"Created project directory: {dir_path}")
                    else:
                        logger.debug(f"Project directory already exists: {dir_path}")
                        
                except Exception as e:
                    logger.error(f"Error creating directory {dir_path}: {str(e)}")
                    results.append({
                        'folder': folder,
                        'directory': str(dir_path),
                        'error': str(e)
                    })
            
            final_result = {
                'success': all('result' in r and r['result']['success'] for r in results),
                'changed': created_count > 0,
                'folders_processed': len(required_folders),
                'folders_created': created_count,
                'results': results
            }
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error ensuring project directories: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def ensure_deep_gateway_dirs(self) -> Dict:
        """
        ایجاد دایرکتوری‌های عمیق gateway
        معادل: Ensure deep gateway directories (config + uploads)
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            # دایرکتوری‌های عمیق gateway
            deep_dirs = [
                'admin/application/config',
                'admin/uploads',
                'admin/captcha_images'
            ]
            
            results = []
            created_count = 0
            
            for sub_path in deep_dirs:
                dir_path = Path(project_path) / inventory_hostname / 'gateway' / sub_path
                
                try:
                    result = self.file_mgr.create_directory(
                        str(dir_path),
                        mode=0o755,
                        force=True,
                        recurse=True
                    )
                    
                    results.append({
                        'sub_path': sub_path,
                        'directory': str(dir_path),
                        'result': result
                    })
                    
                    if result.get('created'):
                        created_count += 1
                        logger.info(f"Created deep gateway directory: {dir_path}")
                    else:
                        logger.debug(f"Deep gateway directory already exists: {dir_path}")
                        
                except Exception as e:
                    logger.error(f"Error creating deep directory {dir_path}: {str(e)}")
                    results.append({
                        'sub_path': sub_path,
                        'directory': str(dir_path),
                        'error': str(e)
                    })
            
            final_result = {
                'success': all('result' in r and r['result']['success'] for r in results),
                'changed': created_count > 0,
                'directories_processed': len(deep_dirs),
                'directories_created': created_count,
                'results': results
            }
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error ensuring deep gateway directories: {str(e)}"
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
            
            # بررسی customer_state
            if self.config.get('customer_state') != 'up':
                logger.info("Customer state is not 'up', skipping project directories")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                })
            
            # اجرای مراحل
            results = []
            
            # 1. ایجاد دایرکتوری‌های همه پروژه‌ها
            project_dirs_result = self.ensure_all_project_dirs()
            results.append({
                'step': 'ensure_all_project_dirs',
                'result': project_dirs_result
            })
            
            # 2. ایجاد دایرکتوری‌های عمیق gateway
            gateway_dirs_result = self.ensure_deep_gateway_dirs()
            results.append({
                'step': 'ensure_deep_gateway_dirs',
                'result': gateway_dirs_result
            })
            
            # خلاصه نتایج
            all_success = all(r['result']['success'] for r in results)
            any_changed = any(r['result'].get('changed', False) for r in results)
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'steps': results,
                'customer_state': self.config.get('customer_state'),
                'project_path': self.config.get('project_path'),
                'inventory_hostname': self.config.get('inventory_hostname')
            }
            
            if all_success:
                logger.info("Project directories ensured successfully")
                return self.complete_task(final_result)
            else:
                failed_steps = [
                    r['step'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed steps: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in ensure project directories task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})