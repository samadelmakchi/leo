#!/usr/bin/env python3
"""
Task 00: Create Docker Network
جایگزین task انسیبل: ایجاد شبکه Docker برای Traefik reverse proxy
"""

import logging
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

# اضافه کردن مسیر پروژه به sys.path برای import ماژول‌ها
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.docker_manager import DockerManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class NetworkTask(BaseTask):
    """
    کلاس مدیریت شبکه‌های Docker
    جایگزین: community.docker.docker_network ماژول Ansible
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه task شبکه
        
        Args:
            config: تنظیمات task از inventory یا playbook
        """
        super().__init__(task_name="create_network", config=config)
        
        # پارامترهای پیش‌فرض
        self.default_params = {
            'network_name': 'traefik_reverse_proxy',
            'driver': 'bridge',
            'state': 'present',
            'attachable': True,
            'ipam_driver': 'default',
            'check_duplicate': True,
            'tags': ['network', 'always']
        }
        
        # Initialize Docker manager
        self.docker_mgr = DockerManager()
        
        # Merge config with defaults
        if config:
            self.params = {**self.default_params, **config}
        else:
            self.params = self.default_params
    
    def validate_parameters(self) -> Dict:
        """
        اعتبارسنجی پارامترهای ورودی
        
        Returns:
            Dict: نتیجه اعتبارسنجی
        """
        errors = []
        warnings = []
        
        # بررسی نام شبکه
        network_name = self.params.get('network_name')
        if not network_name:
            errors.append("Network name is required")
        elif len(network_name) > 128:
            errors.append("Network name must be less than 128 characters")
        elif not network_name.replace('_', '').replace('-', '').isalnum():
            warnings.append(f"Network name '{network_name}' contains special characters")
        
        # بررسی driver
        valid_drivers = ['bridge', 'overlay', 'macvlan', 'ipvlan', 'host', 'none']
        driver = self.params.get('driver', 'bridge')
        if driver not in valid_drivers:
            errors.append(f"Driver '{driver}' is not valid. Valid drivers: {valid_drivers}")
        
        # بررسی state
        state = self.params.get('state', 'present')
        if state not in ['present', 'absent']:
            errors.append(f"State '{state}' is not valid. Must be 'present' or 'absent'")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def create_network(self) -> Dict:
        """
        ایجاد شبکه Docker (معادل Ansible: state=present)
        
        Returns:
            Dict: نتیجه عملیات
        """
        try:
            network_name = self.params['network_name']
            driver = self.params['driver']
            attachable = self.params.get('attachable', True)
            check_duplicate = self.params.get('check_duplicate', True)
            
            # بررسی وجود شبکه
            existing_networks = self.docker_mgr.list_networks()
            for net in existing_networks:
                if net.name == network_name:
                    logger.info(f"Network '{network_name}' already exists")
                    
                    # بررسی تنظیمات شبکه موجود
                    net_attrs = net.attrs
                    existing_driver = net_attrs.get('Driver', 'bridge')
                    
                    if existing_driver != driver:
                        logger.warning(
                            f"Existing network '{network_name}' has driver '{existing_driver}', "
                            f"but requested driver is '{driver}'"
                        )
                    
                    return {
                        'success': True,
                        'changed': False,
                        'network_name': network_name,
                        'network_id': net.id,
                        'driver': existing_driver,
                        'message': f"Network '{network_name}' already exists",
                        'network_details': net_attrs
                    }
            
            # ایجاد config شبکه
            network_config = {
                'name': network_name,
                'driver': driver,
                'attachable': attachable,
                'check_duplicate': check_duplicate
            }
            
            # اضافه کردن IPAM configuration اگر ارائه شده
            ipam_config = self.params.get('ipam_config')
            if ipam_config:
                network_config['ipam'] = ipam_config
            
            # اضافه کردن گزینه‌های driver اگر ارائه شده
            driver_options = self.params.get('driver_options')
            if driver_options:
                network_config['options'] = driver_options
            
            # اضافه کردن labels اگر ارائه شده
            labels = self.params.get('labels')
            if labels:
                network_config['labels'] = labels
            
            # ایجاد شبکه
            logger.info(f"Creating Docker network: {network_name} with driver: {driver}")
            network = self.docker_mgr.create_network(network_config)
            
            if network:
                network_attrs = network.attrs
                
                # لاگ اطلاعات شبکه ایجاد شده
                logger.info(f"Network '{network_name}' created successfully")
                logger.debug(f"Network details: {network_attrs}")
                
                return {
                    'success': True,
                    'changed': True,
                    'network_name': network_name,
                    'network_id': network.id,
                    'driver': driver,
                    'message': f"Network '{network_name}' created successfully",
                    'network_details': network_attrs
                }
            else:
                error_msg = f"Failed to create network '{network_name}'"
                logger.error(error_msg)
                return {
                    'success': False,
                    'changed': False,
                    'error': error_msg,
                    'network_name': network_name
                }
                
        except Exception as e:
            error_msg = f"Error creating network: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'changed': False,
                'error': error_msg,
                'exception_type': type(e).__name__
            }
    
    def remove_network(self) -> Dict:
        """
        حذف شبکه Docker (معادل Ansible: state=absent)
        
        Returns:
            Dict: نتیجه عملیات
        """
        try:
            network_name = self.params['network_name']
            force = self.params.get('force', False)
            
            # بررسی وجود شبکه
            existing_networks = self.docker_mgr.list_networks()
            network_exists = any(net.name == network_name for net in existing_networks)
            
            if not network_exists:
                logger.info(f"Network '{network_name}' does not exist, nothing to remove")
                return {
                    'success': True,
                    'changed': False,
                    'network_name': network_name,
                    'message': f"Network '{network_name}' does not exist"
                }
            
            # حذف شبکه
            logger.info(f"Removing Docker network: {network_name}")
            result = self.docker_mgr.remove_network(network_name, force)
            
            if result:
                logger.info(f"Network '{network_name}' removed successfully")
                return {
                    'success': True,
                    'changed': True,
                    'network_name': network_name,
                    'message': f"Network '{network_name}' removed successfully"
                }
            else:
                error_msg = f"Failed to remove network '{network_name}'"
                logger.error(error_msg)
                return {
                    'success': False,
                    'changed': False,
                    'error': error_msg,
                    'network_name': network_name
                }
                
        except Exception as e:
            error_msg = f"Error removing network: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'changed': False,
                'error': error_msg,
                'exception_type': type(e).__name__
            }
    
    def ensure_network(self) -> Dict:
        """
        اطمینان از وجود شبکه (حالت ترکیبی)
        اگر state=present باشد ایجاد می‌کند، اگر absent باشد حذف می‌کند
        
        Returns:
            Dict: نتیجه عملیات
        """
        state = self.params.get('state', 'present')
        
        if state == 'present':
            return self.create_network()
        elif state == 'absent':
            return self.remove_network()
        else:
            error_msg = f"Invalid state: {state}. Must be 'present' or 'absent'"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def execute(self, **kwargs) -> Dict:
        """
        اجرای اصلی task (متدی که از BaseTask ارث‌بری شده)
        
        Args:
            **kwargs: پارامترهای اضافی که ممکن است از orchestrator بیایند
            
        Returns:
            Dict: نتیجه اجرای task
        """
        # به‌روزرسانی پارامترها با kwargs
        if kwargs:
            self.params.update(kwargs)
        
        # شروع task
        self.start_task()
        
        try:
            # اعتبارسنجی پارامترها
            validation_result = self.validate_parameters()
            if not validation_result['valid']:
                error_msg = f"Parameter validation failed: {validation_result['errors']}"
                logger.error(error_msg)
                return self.fail_task(error_msg, validation_result)
            
            # نمایش warnings
            if validation_result['warnings']:
                for warning in validation_result['warnings']:
                    logger.warning(warning)
            
            # اجرای task اصلی
            result = self.ensure_network()
            
            # افزودن metadata به نتیجه
            result.update({
                'task_name': self.task_name,
                'task_id': self.task_id,
                'parameters_used': self.params,
                'validation_warnings': validation_result['warnings']
            })
            
            # پایان task
            if result['success']:
                return self.complete_task(result)
            else:
                return self.fail_task(result.get('error', 'Unknown error'), result)
                
        except Exception as e:
            error_msg = f"Unexpected error in network task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})
    
    def get_network_info(self, network_name: str = None) -> Dict:
        """
        دریافت اطلاعات یک شبکه خاص
        
        Args:
            network_name: نام شبکه (اگر None باشد از پارامترها می‌گیرد)
            
        Returns:
            Dict: اطلاعات شبکه
        """
        try:
            network_name = network_name or self.params.get('network_name')
            if not network_name:
                return {'success': False, 'error': 'Network name is required'}
            
            networks = self.docker_mgr.list_networks()
            for net in networks:
                if net.name == network_name:
                    return {
                        'success': True,
                        'exists': True,
                        'network_name': network_name,
                        'network_id': net.id,
                        'driver': net.attrs.get('Driver'),
                        'created': net.attrs.get('Created'),
                        'scope': net.attrs.get('Scope'),
                        'containers': net.attrs.get('Containers', {}),
                        'options': net.attrs.get('Options', {}),
                        'labels': net.attrs.get('Labels', {}),
                        'details': net.attrs
                    }
            
            return {
                'success': True,
                'exists': False,
                'network_name': network_name,
                'message': f"Network '{network_name}' not found"
            }
            
        except Exception as e:
            logger.error(f"Error getting network info: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def list_all_networks(self) -> Dict:
        """
        لیست تمام شبکه‌های Docker
        
        Returns:
            Dict: لیست شبکه‌ها
        """
        try:
            networks = self.docker_mgr.list_networks()
            
            network_list = []
            for net in networks:
                network_list.append({
                    'name': net.name,
                    'id': net.id[:12],  # فقط ۱۲ کاراکتر اول
                    'driver': net.attrs.get('Driver'),
                    'scope': net.attrs.get('Scope'),
                    'created': net.attrs.get('Created'),
                    'containers_count': len(net.attrs.get('Containers', {})),
                    'labels': net.attrs.get('Labels', {})
                })
            
            return {
                'success': True,
                'count': len(network_list),
                'networks': network_list
            }
            
        except Exception as e:
            logger.error(f"Error listing networks: {str(e)}")
            return {'success': False, 'error': str(e)}


# تابع helper برای backward compatibility
def create_traefik_network_task(config: Dict = None) -> Dict:
    """
    تابع helper برای ایجاد شبکه Traefik (برای استفاده مستقیم)
    
    Args:
        config: تنظیمات اضافی
        
    Returns:
        Dict: نتیجه اجرای task
    """
    default_config = {
        'network_name': 'traefik_reverse_proxy',
        'driver': 'bridge',
        'state': 'present',
        'attachable': True,
        'tags': ['network', 'always']
    }
    
    if config:
        default_config.update(config)
    
    task = NetworkTask(default_config)
    return task.execute()


# برای اجرای مستقل
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create Docker Network Task")
    parser.add_argument('--network-name', default='traefik_reverse_proxy',
                       help='نام شبکه Docker')
    parser.add_argument('--driver', default='bridge',
                       help='درایور شبکه (bridge, overlay, etc.)')
    parser.add_argument('--state', default='present',
                       choices=['present', 'absent'],
                       help='state: present (ایجاد) یا absent (حذف)')
    parser.add_argument('--attachable', action='store_true', default=True,
                       help='آیا شبکه attachable باشد؟')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='نمایش لاگ‌های verbose')
    
    args = parser.parse_args()
    
    # تنظیم logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # اجرای task
    config = {
        'network_name': args.network_name,
        'driver': args.driver,
        'state': args.state,
        'attachable': args.attachable
    }
    
    task = NetworkTask(config)
    result = task.execute()
    
    # نمایش نتیجه
    print("\n" + "="*50)
    print("Network Task Result:")
    print("="*50)
    print(f"Success: {result.get('success')}")
    print(f"Changed: {result.get('changed')}")
    print(f"Task ID: {result.get('task_id')}")
    
    if result.get('success'):
        if result.get('changed'):
            print(f"✓ {result.get('message')}")
        else:
            print(f"ⓘ {result.get('message')}")
    else:
        print(f"✗ Error: {result.get('error')}")
    
    if args.verbose and result.get('network_details'):
        print("\nNetwork Details:")
        import json
        print(json.dumps(result.get('network_details'), indent=2))
    
    # خروج با کد مناسب
    sys.exit(0 if result.get('success') else 1)