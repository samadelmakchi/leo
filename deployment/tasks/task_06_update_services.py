#!/usr/bin/env python3
"""
Task 06: Update Services
جایگزین task انسیبل: 06-update-services.yml
"""

import logging
import sys
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.task_base import BaseTask
from deployment.tasks.task_03_define_projects import get_projects_list
from deployment.tasks.update_service import update_single_service

logger = logging.getLogger(__name__)


class UpdateServicesTask(BaseTask):
    """به‌روزرسانی سرویس‌های انتخاب شده"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="update_services", config=config)
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'project_path',
            'inventory_hostname',
            'customer_containers'
        ]
        
        # Flag برای tracking
        self.any_service_updated = False
    
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
    
    def update_selected_services(self) -> Dict:
        """
        به‌روزرسانی سرویس‌های انتخاب شده
        """
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                }
            
            # دریافت لیست پروژه‌ها
            projects = get_projects_list(self.config)
            
            # فیلتر پروژه‌هایی که update flag دارند
            projects_to_update = [
                p for p in projects 
                if p.get('update', False)
            ]
            
            if not projects_to_update:
                logger.info("No services to update (update flags are false)")
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "No services to update"
                }
            
            logger.info(f"Updating {len(projects_to_update)} services: {[p['name'] for p in projects_to_update]}")
            
            # به‌روزرسانی هر سرویس
            results = []
            updated_count = 0
            
            for project in projects_to_update:
                logger.info(f"Updating service: {project['name']}")
                
                # تنظیم پارامترهای update_service
                service_config = {
                    'project': project,
                    'project_path': self.config['project_path'],
                    'inventory_hostname': self.config['inventory_hostname'],
                    'customer_containers': self.config['customer_containers'],
                    'host_vars': self.config.get('host_vars', {}),
                    'ssh_key_path': self.config.get('ssh_key_path', 'deployment/resources/ssh/id_rsa')
                }
                
                # اجرای update service
                result = update_single_service(**service_config)
                
                results.append({
                    'service': project['name'],
                    'result': result
                })
                
                if result['success'] and result.get('git_changed', False):
                    updated_count += 1
                    self.any_service_updated = True
                    logger.info(f"Service {project['name']} updated (git changed)")
                elif result['success']:
                    logger.info(f"Service {project['name']} already up to date")
                else:
                    logger.error(f"Failed to update service {project['name']}: {result.get('error')}")
            
            # خلاصه نتایج
            success_count = sum(1 for r in results if r['result']['success'])
            failed_count = len(results) - success_count
            
            final_result = {
                'success': failed_count == 0,
                'changed': updated_count > 0,
                'any_service_updated': self.any_service_updated,
                'total_services': len(projects_to_update),
                'updated_services': updated_count,
                'successful_updates': success_count,
                'failed_updates': failed_count,
                'results': results,
                'message': f"Updated {updated_count} out of {len(projects_to_update)} services"
            }
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error updating services: {str(e)}"
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
            
            # Reset flag
            self.any_service_updated = False
            
            # اجرای task اصلی
            result = self.update_selected_services()
            
            # اضافه کردن metadata
            result.update({
                'task_name': self.task_name,
                'task_id': self.task_id,
                'parameters_used': {
                    'customer_state': self.config.get('customer_state'),
                    'project_path': self.config.get('project_path'),
                    'inventory_hostname': self.config.get('inventory_hostname'),
                    'customer_containers': self.config.get('customer_containers')
                },
                'any_service_updated': self.any_service_updated
            })
            
            # ذخیره flag در config برای taskهای بعدی
            self.config['any_service_updated'] = self.any_service_updated
            
            if result['success']:
                logger.info(f"Update services completed: {result['message']}")
                return self.complete_task(result)
            else:
                return self.fail_task(result.get('error', 'Unknown error'), result)
                
        except Exception as e:
            error_msg = f"Unexpected error in update services task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})


# تابع helper
def update_all_services(
    customer_state: str,
    project_path: str,
    inventory_hostname: str,
    customer_containers: str,
    host_vars: Dict = None
) -> Dict:
    """
    به‌روزرسانی تمام سرویس‌ها
    
    Returns:
        نتیجه اجرا
    """
    config = {
        'customer_state': customer_state,
        'project_path': project_path,
        'inventory_hostname': inventory_hostname,
        'customer_containers': customer_containers,
        'host_vars': host_vars or {}
    }
    
    task = UpdateServicesTask(config)
    return task.execute()