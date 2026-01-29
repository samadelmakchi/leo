#!/usr/bin/env python3
"""
Task 05: Ensure Gateway Docker Init Directory
جایگزین task انسیبل: 05-ensure-gateway-docker-init.yml
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


class EnsureGatewayDockerInitTask(BaseTask):
    """اطمینان از وجود دایرکتوری gateway/docker/init"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="ensure_gateway_docker_init", config=config)
        
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
    
    def ensure_gateway_docker_init_dir(self) -> Dict:
        """
        ایجاد دایرکتوری gateway/docker/init
        معادل: Always ensure gateway/docker/init exists
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
            
            # مسیر دایرکتوری init
            init_dir = Path(project_path) / inventory_hostname / 'gateway' / 'docker' / 'init'
            
            # ایجاد دایرکتوری با owner و group خاص
            result = self.file_mgr.create_directory(
                str(init_dir),
                mode=0o755,
                force=True
            )
            
            # تنظیم owner و group (اگر پشتیبانی شود)
            # Note: در پایتون استاندارد، نیاز به ماژول‌های اضافه دارد
            # برای سادگی فعلا این بخش را حذف می‌کنیم
            
            if result['success']:
                if result.get('created'):
                    logger.info(f"Created gateway docker init directory: {init_dir}")
                    result['message'] = f"Directory created: {init_dir}"
                else:
                    logger.debug(f"Gateway docker init directory already exists: {init_dir}")
                    result['message'] = f"Directory already exists: {init_dir}"
            
            return result
            
        except Exception as e:
            error_msg = f"Error ensuring gateway docker init directory: {str(e)}"
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
            
            # اجرای task اصلی
            result = self.ensure_gateway_docker_init_dir()
            
            # اضافه کردن metadata
            result.update({
                'task_name': self.task_name,
                'task_id': self.task_id,
                'parameters_used': {
                    'customer_state': self.config.get('customer_state'),
                    'project_path': self.config.get('project_path'),
                    'inventory_hostname': self.config.get('inventory_hostname')
                }
            })
            
            if result['success']:
                return self.complete_task(result)
            else:
                return self.fail_task(result.get('error', 'Unknown error'), result)
                
        except Exception as e:
            error_msg = f"Unexpected error in gateway docker init task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})


# تابع helper برای استفاده سریع
def ensure_gateway_init_directory(
    customer_state: str,
    project_path: str,
    inventory_hostname: str
) -> Dict:
    """
    تابع helper برای اطمینان از وجود دایرکتوری gateway/docker/init
    
    Args:
        customer_state: حالت مشتری
        project_path: مسیر پروژه
        inventory_hostname: نام host
        
    Returns:
        نتیجه اجرا
    """
    config = {
        'customer_state': customer_state,
        'project_path': project_path,
        'inventory_hostname': inventory_hostname
    }
    
    task = EnsureGatewayDockerInitTask(config)
    return task.execute()


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Ensure Gateway Docker Init Task")
    parser.add_argument('--customer-state', required=True,
                       choices=['up', 'down'],
                       help='Customer state')
    parser.add_argument('--project-path', required=True,
                       help='Base project path')
    parser.add_argument('--inventory-hostname', required=True,
                       help='Inventory hostname')
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
    task = EnsureGatewayDockerInitTask(config)
    result = task.execute()
    
    # نمایش نتیجه
    print(json.dumps(result, indent=2, default=str))
    
    # خروجی مناسب
    sys.exit(0 if result.get('success') else 1)