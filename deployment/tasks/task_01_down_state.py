#!/usr/bin/env python3
"""
Task 01: Down State - Stop and remove everything when state=down
جایگزین task انسیبل: 01-down-state.yml
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.docker_manager import DockerManager
from deployment.core.cron_manager import CronManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class DownStateTask(BaseTask):
    """مدیریت حالت down برای مشتری"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="down_state", config=config)
        
        self.docker_mgr = DockerManager()
        self.cron_mgr = CronManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'customer_containers',
            'inventory_hostname'
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        errors = []
        
        for param in self.required_params:
            if param not in self.config:
                errors.append(f"Missing required parameter: {param}")
        
        # بررسی customer_state
        customer_state = self.config.get('customer_state')
        if customer_state not in ['up', 'down']:
            errors.append(f"Invalid customer_state: {customer_state}. Must be 'up' or 'down'")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }
    
    def stop_and_remove_containers(self) -> Dict:
        """
        متوقف و حذف کردن تمام containerهای مشتری
        معادل: docker ps -a --filter "name={{ customer_containers }}" -q | xargs -r docker stop
        """
        try:
            customer_containers = self.config['customer_containers']
            
            logger.info(f"Stopping and removing containers for: {customer_containers}")
            
            # لیست containerهای مشتری
            containers = self.docker_mgr.list_containers(
                filters={'name': customer_containers}
            )
            
            if not containers:
                logger.info(f"No containers found for {customer_containers}")
                return {
                    'success': True,
                    'changed': False,
                    'stopped': 0,
                    'removed': 0,
                    'message': 'No containers to stop/remove'
                }
            
            # متوقف کردن containerها
            stopped_count = 0
            for container in containers:
                try:
                    if container.status == 'running':
                        container.stop()
                        stopped_count += 1
                        logger.debug(f"Stopped container: {container.name}")
                except Exception as e:
                    logger.warning(f"Error stopping container {container.name}: {str(e)}")
            
            # حذف containerها
            removed_count = 0
            for container in containers:
                try:
                    container.remove(force=True)
                    removed_count += 1
                    logger.debug(f"Removed container: {container.name}")
                except Exception as e:
                    logger.warning(f"Error removing container {container.name}: {str(e)}")
            
            result = {
                'success': True,
                'changed': stopped_count > 0 or removed_count > 0,
                'total_containers': len(containers),
                'stopped': stopped_count,
                'removed': removed_count,
                'message': f"Stopped {stopped_count} and removed {removed_count} containers"
            }
            
            logger.info(f"Down state completed: {result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"Error in stop_and_remove_containers: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def remove_cron_jobs(self) -> Dict:
        """
        حذف cron jobهای backup
        معادل: ansible.builtin.cron با state: absent
        """
        try:
            inventory_hostname = self.config.get('inventory_hostname')
            cron_names = [
                f"Backup Volumes ({inventory_hostname})",
                f"Backup Databases ({inventory_hostname})"
            ]
            
            removed_count = 0
            for cron_name in cron_names:
                try:
                    if self.cron_mgr.remove_job(cron_name):
                        removed_count += 1
                        logger.info(f"Removed cron job: {cron_name}")
                except Exception as e:
                    logger.warning(f"Error removing cron job {cron_name}: {str(e)}")
            
            result = {
                'success': True,
                'changed': removed_count > 0,
                'removed_count': removed_count,
                'message': f"Removed {removed_count} cron jobs"
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Error removing cron jobs: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def execute(self, **kwargs) -> Dict:
        """اجرای اصلی task"""
        # به‌روزرسانی config
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
            
            # فقط اگر customer_state == "down" باشد اجرا شود
            if self.config.get('customer_state') != 'down':
                logger.info("Customer state is not 'down', skipping down state tasks")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'down'"
                })
            
            # اجرای مراحل
            results = []
            
            # 1. متوقف و حذف containerها
            container_result = self.stop_and_remove_containers()
            results.append({
                'step': 'stop_remove_containers',
                'result': container_result
            })
            
            # 2. حذف cron jobها
            cron_result = self.remove_cron_jobs()
            results.append({
                'step': 'remove_cron_jobs',
                'result': cron_result
            })
            
            # خلاصه نتایج
            all_success = all(r['result']['success'] for r in results)
            any_changed = any(r['result'].get('changed', False) for r in results)
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'steps': results,
                'customer_state': 'down',
                'customer_containers': self.config['customer_containers'],
                'inventory_hostname': self.config['inventory_hostname']
            }
            
            if all_success:
                logger.info(f"Down state completed successfully for {self.config['customer_containers']}")
                return self.complete_task(final_result)
            else:
                failed_steps = [
                    r['step'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed steps: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in down state task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})


def main():
    """تابع اصلی برای اجرای مستقل"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Down State Task")
    parser.add_argument('--customer-state', required=True,
                       choices=['up', 'down'],
                       help='Customer state')
    parser.add_argument('--customer-containers', required=True,
                       help='Customer containers name pattern')
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
    config = {
        'customer_state': args.customer_state,
        'customer_containers': args.customer_containers,
        'inventory_hostname': args.inventory_hostname
    }
    
    task = DownStateTask(config)
    result = task.execute()
    
    # نمایش نتیجه
    print(json.dumps(result, indent=2, default=str))
    
    # خروجی مناسب
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()