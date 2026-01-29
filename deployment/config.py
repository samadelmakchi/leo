# deployment/config.py (اصلاح شده)
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

from deployment.core.inventory_loader import InventoryLoader
from deployment.core.customer_manager import get_customer_manager

logger = logging.getLogger(__name__)


class DeploymentConfig:
    """کلاس تنظیمات deployment"""
    
    def __init__(self, config_path: str = None, customer_csv_path: str = None):
        """
        مقداردهی اولیه config
        
        Args:
            config_path: مسیر فایل config (اختیاری)
            customer_csv_path: مسیر فایل CSV مشتریان
        """
        self.base_dir = Path(__file__).parent.parent
        self.project_root = self.base_dir.parent
        
        # بارگذاری config از فایل
        self.config_data = self._load_config(config_path) if config_path else {}
        
        # تنظیم مسیرها
        self._setup_paths()
        
        # Customer Manager
        self.customer_manager = get_customer_manager(customer_csv_path)
        
        # بارگذاری inventory (برای backward compatibility)
        self.inventory_loader = None
        self.inventory_path = None
        
        # تنظیمات Docker
        self.docker_settings = {
            'socket': os.getenv('DOCKER_SOCKET', 'unix://var/run/docker.sock'),
            'timeout': int(os.getenv('DOCKER_TIMEOUT', '300')),
            'compose_version': 'v2'
        }
        
        # تنظیمات SSH
        self.ssh_settings = {
            'private_key': self.resources_dir / "ssh" / "id_rsa",
            'public_key': self.resources_dir / "ssh" / "id_rsa.pub",
            'username': os.getenv('SSH_USERNAME', 'root'),
            'timeout': int(os.getenv('SSH_TIMEOUT', '30'))
        }
        
        # تنظیمات Backup
        self.backup_settings = {
            'enabled': os.getenv('BACKUP_ENABLED', 'true').lower() == 'true',
            'path': Path(os.getenv('BACKUP_PATH', '/backup')),
            'retention_days': int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        }
        
        logger.info("Deployment configuration initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """بارگذاری config از فایل"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {str(e)}")
            return {}
    
    def _setup_paths(self):
        """تنظیم مسیرهای سیستم"""
        # دایرکتوری‌های اصلی
        self.resources_dir = self.base_dir / "resources"
        self.templates_dir = self.base_dir / "templates"
        self.tasks_dir = self.base_dir / "tasks"
        
        # دایرکتوری‌های داخل resources
        self.backup_scripts_dir = self.resources_dir / "backup_scripts"
        self.sql_scripts_dir = self.resources_dir / "sql"
        self.ssh_keys_dir = self.resources_dir / "ssh"
        
        # اطمینان از وجود دایرکتوری‌ها
        for directory in [self.resources_dir, self.backup_scripts_dir, 
                         self.sql_scripts_dir, self.ssh_keys_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_customer(self, customer_name: str) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات مشتری"""
        return self.customer_manager.get_customer(customer_name)
    
    def add_customer(self, customer_data: Dict[str, Any]) -> bool:
        """اضافه کردن مشتری جدید"""
        return self.customer_manager.add_customer(customer_data)
    
    def list_customers(self) -> List[str]:
        """لیست مشتریان"""
        return self.customer_manager.list_customers()
    
    def get_customer_by_host(self, host: str) -> Optional[Dict[str, Any]]:
        """دریافت مشتری بر اساس host"""
        return self.customer_manager.get_customer_by_host(host)
    
    def get_customer_projects(self, customer_name: str) -> List[Dict[str, Any]]:
        """دریافت پروژه‌های مشتری"""
        return self.customer_manager.get_customer_projects(customer_name)
    
    def validate_customer(self, customer_name: str) -> Dict[str, Any]:
        """اعتبارسنجی مشتری"""
        return self.customer_manager.validate_customer(customer_name)
    
    # ==================== Inventory Compatibility Methods ====================
    
    def get_host_config(self, hostname: str) -> Dict[str, Any]:
        """
        دریافت تنظیمات یک host خاص (برای backward compatibility)
        
        Args:
            hostname: نام host
            
        Returns:
            دیکشنری تنظیمات host
        """
        customer = self.get_customer_by_host(hostname)
        if customer:
            return customer
        return {}
    
    def get_all_hosts(self) -> Dict[str, Dict[str, Any]]:
        """دریافت تمام hosts (برای backward compatibility)"""
        # تبدیل مشتریان به hosts
        hosts = {}
        for customer_name, customer_data in self.customer_manager.customers.items():
            hostname = customer_data.get('host')
            if hostname:
                hosts[hostname] = customer_data
        return hosts
    
    def list_hosts(self) -> List[str]:
        """لیست تمام hosts (برای backward compatibility)"""
        hosts = []
        for customer_data in self.customer_manager.customers.values():
            hostname = customer_data.get('host')
            if hostname and hostname not in hosts:
                hosts.append(hostname)
        return hosts
    
    def resolve_variable(self, hostname: str, var_name: str, default: Any = None) -> Any:
        """
        resolve کردن یک متغیر برای host خاص (برای backward compatibility)
        
        Args:
            hostname: نام host
            var_name: نام متغیر
            default: مقدار پیش‌فرض
            
        Returns:
            مقدار متغیر
        """
        customer = self.get_customer_by_host(hostname)
        if customer:
            return customer.get(var_name, default)
        return default
    
    def expand_template(self, hostname: str, template: str) -> str:
        """
        expand کردن template با متغیرهای host (برای backward compatibility)
        
        Args:
            hostname: نام host
            template: template
            
        Returns:
            template expand شده
        """
        customer = self.get_customer_by_host(hostname)
        if not customer:
            return template
        
        result = template
        for key, value in customer.items():
            if isinstance(value, (str, int, float, bool)):
                placeholder = f"{{{{ {key} }}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(value))
        
        # همچنین inventory_hostname را اضافه کن
        if "{{ inventory_hostname }}" in result:
            result = result.replace("{{ inventory_hostname }}", hostname)
        
        return result
    
    def validate_inventory(self) -> Dict[str, Any]:
        """اعتبارسنجی inventory (برای backward compatibility)"""
        # اعتبارسنجی تمام مشتریان
        errors = []
        warnings = []
        
        for customer_name in self.list_customers():
            validation = self.validate_customer(customer_name)
            if not validation['valid']:
                errors.extend([f"{customer_name}: {error}" for error in validation['errors']])
            if validation['warnings']:
                warnings.extend([f"{customer_name}: {warning}" for warning in validation['warnings']])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'hosts_count': len(self.list_hosts()),
            'customers_count': len(self.list_customers())
        }
    
    # ==================== Task Configuration ====================
    
    def get_task_config(self, task_name: str, hostname: str = None, customer_name: str = None) -> Dict[str, Any]:
        """
        دریافت config برای یک task
        
        Args:
            task_name: نام task
            hostname: نام host (اختیاری)
            customer_name: نام مشتری (اختیاری)
            
        Returns:
            config task
        """
        config = {
            'task_name': task_name,
            'config_dir': str(self.base_dir),
            'project_root': str(self.project_root),
            'docker_settings': self.docker_settings,
            'ssh_settings': self.ssh_settings,
            'backup_settings': self.backup_settings,
            'paths': {
                'resources': str(self.resources_dir),
                'templates': str(self.templates_dir),
                'backup_scripts': str(self.backup_scripts_dir),
                'sql_scripts': str(self.sql_scripts_dir)
            }
        }
        
        # پیدا کردن customer
        customer = None
        if customer_name:
            customer = self.get_customer(customer_name)
        elif hostname:
            customer = self.get_customer_by_host(hostname)
        
        # اضافه کردن customer vars اگر customer پیدا شد
        if customer:
            config['customer_vars'] = customer
            config['customer_name'] = customer.get('customer_name')
            config['hostname'] = customer.get('host')
            
            # اضافه کردن مسیرهای مهم
            important_paths = ['project_path', 'backup_path', 'log_path', 'info_path']
            for path_name in important_paths:
                if path_name in customer:
                    config[path_name] = customer[path_name]
            
            # اضافه کردن customer-specific settings
            config['customer_settings'] = {
                'domain': customer.get('customer_domain'),
                'state': customer.get('customer_state'),
                'backup_enabled': customer.get('customer_backup_enabled', False),
                'test_enabled': customer.get('customer_test_enabled', False),
                'containers': self.customer_manager.get_customer_containers(
                    customer.get('customer_name')
                )
            }
        
        return config
    
    def save_config(self, output_path: str = None) -> bool:
        """
        ذخیره تنظیمات
        
        Args:
            output_path: مسیر خروجی
            
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            if not output_path:
                output_path = self.base_dir / "config.yml"
            
            config_data = {
                'docker_settings': self.docker_settings,
                'ssh_settings': {
                    'private_key': str(self.ssh_settings['private_key']),
                    'username': self.ssh_settings['username']
                },
                'backup_settings': self.backup_settings,
                'paths': {
                    'resources_dir': str(self.resources_dir),
                    'templates_dir': str(self.templates_dir),
                    'backup_scripts_dir': str(self.backup_scripts_dir),
                    'sql_scripts_dir': str(self.sql_scripts_dir)
                },
                'customer_count': len(self.list_customers()),
                'host_count': len(self.list_hosts())
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            logger.info(f"Configuration saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def __str__(self) -> str:
        """نمایش اطلاعات config"""
        info = [
            "Deployment Configuration:",
            f"  Base Directory: {self.base_dir}",
            f"  Customers: {len(self.list_customers())}",
            f"  Hosts: {len(self.list_hosts())}",
            f"  Docker Socket: {self.docker_settings['socket']}",
            f"  Backup Enabled: {self.backup_settings['enabled']}"
        ]
        return "\n".join(info)


# Singleton instance برای استفاده آسان
_config_instance: Optional[DeploymentConfig] = None


def get_config(customer_csv_path: str = None) -> DeploymentConfig:
    """
    دریافت instance از DeploymentConfig
    
    Args:
        customer_csv_path: مسیر فایل CSV مشتریان
        
    Returns:
        DeploymentConfig instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = DeploymentConfig(customer_csv_path=customer_csv_path)
    elif customer_csv_path and _config_instance.customer_manager.csv_path != Path(customer_csv_path):
        # اگر CSV جدیدی خواسته شد، instance جدید بساز
        _config_instance = DeploymentConfig(customer_csv_path=customer_csv_path)
    
    return _config_instance


def reload_config(customer_csv_path: str = None) -> DeploymentConfig:
    """
    بارگذاری مجدد config
    
    Args:
        customer_csv_path: مسیر فایل CSV مشتریان
        
    Returns:
        DeploymentConfig instance جدید
    """
    global _config_instance
    _config_instance = DeploymentConfig(customer_csv_path=customer_csv_path)
    return _config_instance


# برای backward compatibility
def load_inventory_config(customer_csv_path: str = None) -> Dict[str, Any]:
    """
    تابع helper برای بارگذاری config از CSV
    
    Args:
        customer_csv_path: مسیر فایل CSV مشتریان
        
    Returns:
        دیکشنری config
    """
    config = get_config(customer_csv_path)
    return config.get_task_config('default')