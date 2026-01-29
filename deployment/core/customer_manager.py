# deployment/core/customer_manager.py
"""
Customer Manager - مدیریت مشتریان از فایل CSV
"""

import logging
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)


class CustomerManager:
    """مدیریت مشتریان از فایل CSV"""
    
    def __init__(self, csv_path: str = None):
        """
        مقداردهی اولیه Customer Manager
        
        Args:
            csv_path: مسیر فایل CSV مشتریان
        """
        self.csv_path = Path(csv_path) if csv_path else Path(__file__).parent.parent.parent / "resources" / "customer.csv"
        self.customers = {}
        self.projects_path = self.csv_path.parent / "projects.csv"
        self.projects = []
        
        # بارگذاری داده‌ها
        self.load_customers()
        self.load_projects()
    
    def load_customers(self) -> bool:
        """
        بارگذاری مشتریان از فایل CSV
        
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            if not self.csv_path.exists():
                logger.error(f"Customer CSV file not found: {self.csv_path}")
                return False
            
            # خواندن با pandas
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            
            # تبدیل به دیکشنری
            self.customers = {}
            for _, row in df.iterrows():
                customer_name = str(row.get('customer_name', '')).strip()
                if customer_name:
                    # تبدیل تمام مقادیر
                    customer_data = {}
                    for col in df.columns:
                        value = row[col]
                        # تبدیل مقادیر خاص
                        if pd.isna(value):
                            customer_data[col] = None
                        elif isinstance(value, str):
                            # تبدیل boolean strings
                            if value.lower() in ['true', 'yes', '1']:
                                customer_data[col] = True
                            elif value.lower() in ['false', 'no', '0']:
                                customer_data[col] = False
                            else:
                                customer_data[col] = value
                        else:
                            customer_data[col] = value
                    
                    self.customers[customer_name] = customer_data
            
            logger.info(f"Loaded {len(self.customers)} customers from {self.csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading customers CSV: {str(e)}", exc_info=True)
            return False
    
    def load_projects(self) -> bool:
        """
        بارگذاری پروژه‌ها از فایل CSV
        
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            if not self.projects_path.exists():
                logger.warning(f"Projects CSV file not found: {self.projects_path}")
                return False
            
            df = pd.read_csv(self.projects_path, encoding='utf-8')
            self.projects = df.to_dict('records')
            
            logger.info(f"Loaded {len(self.projects)} projects from {self.projects_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading projects CSV: {str(e)}", exc_info=True)
            return False
    
    def get_customer(self, customer_name: str) -> Optional[Dict[str, Any]]:
        """
        دریافت اطلاعات یک مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            اطلاعات مشتری یا None
        """
        return self.customers.get(customer_name)
    
    def get_customer_by_host(self, host: str) -> Optional[Dict[str, Any]]:
        """
        دریافت مشتری بر اساس host
        
        Args:
            host: نام host
            
        Returns:
            اطلاعات مشتری یا None
        """
        for customer in self.customers.values():
            if customer.get('host') == host:
                return customer
        return None
    
    def add_customer(self, customer_data: Dict[str, Any]) -> bool:
        """
        اضافه کردن مشتری جدید
        
        Args:
            customer_data: داده‌های مشتری
            
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            customer_name = customer_data.get('customer_name')
            if not customer_name:
                logger.error("Customer name is required")
                return False
            
            if customer_name in self.customers:
                logger.warning(f"Customer '{customer_name}' already exists, updating...")
                return self.update_customer(customer_name, customer_data)
            
            # اضافه کردن به دیکشنری
            self.customers[customer_name] = customer_data
            
            # ذخیره در CSV
            return self.save_customers()
            
        except Exception as e:
            logger.error(f"Error adding customer: {str(e)}")
            return False
    
    def update_customer(self, customer_name: str, updates: Dict[str, Any]) -> bool:
        """
        به‌روزرسانی مشتری موجود
        
        Args:
            customer_name: نام مشتری
            updates: داده‌های به‌روزرسانی
            
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            if customer_name not in self.customers:
                logger.error(f"Customer '{customer_name}' not found")
                return False
            
            # به‌روزرسانی داده‌ها
            self.customers[customer_name].update(updates)
            
            # ذخیره در CSV
            return self.save_customers()
            
        except Exception as e:
            logger.error(f"Error updating customer: {str(e)}")
            return False
    
    def delete_customer(self, customer_name: str) -> bool:
        """
        حذف مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            if customer_name not in self.customers:
                logger.error(f"Customer '{customer_name}' not found")
                return False
            
            # حذف از دیکشنری
            del self.customers[customer_name]
            
            # ذخیره در CSV
            return self.save_customers()
            
        except Exception as e:
            logger.error(f"Error deleting customer: {str(e)}")
            return False
    
    def save_customers(self) -> bool:
        """
        ذخیره مشتریان در فایل CSV
        
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            if not self.customers:
                logger.warning("No customers to save")
                return False
            
            # جمع‌آوری تمام ستون‌های ممکن
            all_columns = set()
            for customer in self.customers.values():
                all_columns.update(customer.keys())
            
            # مرتب‌سازی ستون‌ها
            columns = sorted(all_columns)
            
            # نوشتن به CSV
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                
                for customer_name, customer_data in self.customers.items():
                    # اطمینان از وجود تمام ستون‌ها
                    row = {col: customer_data.get(col, '') for col in columns}
                    writer.writerow(row)
            
            logger.info(f"Saved {len(self.customers)} customers to {self.csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving customers CSV: {str(e)}")
            return False
    
    def list_customers(self, state: str = None) -> List[str]:
        """
        لیست مشتریان
        
        Args:
            state: فیلتر بر اساس state (up/down)
            
        Returns:
            لیست نام مشتریان
        """
        if not state:
            return list(self.customers.keys())
        
        return [
            name for name, data in self.customers.items()
            if data.get('customer_state') == state
        ]
    
    def get_customer_projects(self, customer_name: str) -> List[Dict[str, Any]]:
        """
        دریافت پروژه‌های یک مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            لیست پروژه‌های مشتری
        """
        customer = self.get_customer(customer_name)
        if not customer:
            return []
        
        projects = []
        for project in self.projects:
            project_copy = project.copy()
            
            # جایگزینی متغیرها با مقادیر مشتری
            for key, value in project_copy.items():
                if isinstance(value, str) and '{{' in value:
                    # استخراج نام متغیر از template
                    var_name = value.replace('{{ ', '').replace(' }}', '').strip()
                    project_copy[key] = customer.get(var_name, value)
            
            projects.append(project_copy)
        
        return projects
    
    def get_customer_containers(self, customer_name: str) -> List[str]:
        """
        دریافت لیست containerهای یک مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            لیست containerها
        """
        customer = self.get_customer(customer_name)
        if not customer:
            return []
        
        containers_str = customer.get('customer_containers', '')
        if not containers_str:
            return []
        
        # split کردن بر اساس کاما
        return [c.strip() for c in str(containers_str).split(',')]
    
    def get_active_customers(self) -> List[Dict[str, Any]]:
        """
        دریافت مشتریان فعال (state=up)
        
        Returns:
            لیست مشتریان فعال
        """
        return [
            customer for customer in self.customers.values()
            if customer.get('customer_state') == 'up'
        ]
    
    def validate_customer(self, customer_name: str) -> Dict[str, Any]:
        """
        اعتبارسنجی اطلاعات مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            نتیجه اعتبارسنجی
        """
        customer = self.get_customer(customer_name)
        if not customer:
            return {'valid': False, 'error': f'Customer {customer_name} not found'}
        
        errors = []
        warnings = []
        
        # بررسی فیلدهای ضروری
        required_fields = ['host', 'customer_domain', 'project_path']
        for field in required_fields:
            if not customer.get(field):
                errors.append(f"Missing required field: {field}")
        
        # بررسی format دامنه
        domain = customer.get('customer_domain', '')
        if domain and '.' not in domain:
            warnings.append(f"Domain '{domain}' may not be valid")
        
        # بررسی path
        project_path = customer.get('project_path', '')
        if project_path and not Path(project_path).exists():
            warnings.append(f"Project path does not exist: {project_path}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'customer': customer_name
        }
    
    def get_customer_summary(self, customer_name: str) -> Dict[str, Any]:
        """
        دریافت خلاصه اطلاعات مشتری
        
        Args:
            customer_name: نام مشتری
            
        Returns:
            خلاصه اطلاعات
        """
        customer = self.get_customer(customer_name)
        if not customer:
            return {}
        
        return {
            'name': customer_name,
            'host': customer.get('host'),
            'domain': customer.get('customer_domain'),
            'state': customer.get('customer_state'),
            'containers': self.get_customer_containers(customer_name),
            'backup_enabled': customer.get('customer_backup_enabled', False),
            'test_enabled': customer.get('customer_test_enabled', False),
            'project_count': len(self.get_customer_projects(customer_name)),
            'validation': self.validate_customer(customer_name)
        }
    
    def search_customers(self, search_term: str) -> List[Dict[str, Any]]:
        """
        جستجوی مشتریان
        
        Args:
            search_term: عبارت جستجو
            
        Returns:
            لیست مشتریان مطابق
        """
        results = []
        search_term = search_term.lower()
        
        for name, data in self.customers.items():
            # جستجو در نام، host و domain
            if (search_term in name.lower() or
                search_term in str(data.get('host', '')).lower() or
                search_term in str(data.get('customer_domain', '')).lower()):
                
                results.append({
                    'name': name,
                    'host': data.get('host'),
                    'domain': data.get('customer_domain'),
                    'state': data.get('customer_state')
                })
        
        return results


# Singleton instance
_customer_manager_instance = None


def get_customer_manager(csv_path: str = None) -> CustomerManager:
    """
    دریافت instance از CustomerManager
    
    Args:
        csv_path: مسیر فایل CSV
        
    Returns:
        CustomerManager instance
    """
    global _customer_manager_instance
    
    if _customer_manager_instance is None:
        _customer_manager_instance = CustomerManager(csv_path)
    elif csv_path and _customer_manager_instance.csv_path != Path(csv_path):
        _customer_manager_instance = CustomerManager(csv_path)
    
    return _customer_manager_instance


def reload_customers(csv_path: str = None) -> CustomerManager:
    """
    بارگذاری مجدد مشتریان
    
    Args:
        csv_path: مسیر فایل CSV
        
    Returns:
        CustomerManager instance جدید
    """
    global _customer_manager_instance
    _customer_manager_instance = CustomerManager(csv_path)
    return _customer_manager_instance