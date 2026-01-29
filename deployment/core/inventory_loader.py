#!/usr/bin/env python3
"""
Inventory Loader Module - پشتیبانی از CSV و YAML
بارگذاری و مدیریت فایل inventory از CSV و YAML
"""

import logging
import yaml
import json
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
import re

logger = logging.getLogger(__name__)


class InventoryLoader:
    """کلاس بارگذاری inventory از CSV و YAML"""
    
    SUPPORTED_FORMATS = ['.yml', '.yaml', '.csv', '.json']
    
    def __init__(self, inventory_path: str = None):
        """
        مقداردهی اولیه loader
        
        Args:
            inventory_path: مسیر فایل inventory
        """
        self.inventory_path = Path(inventory_path) if inventory_path else None
        self.inventory_data = {}
        self.hosts = {}
        self.groups = {}
        self.all_vars = {}
        self.file_format = None
        
        if inventory_path:
            self.load_inventory(inventory_path)
    
    def detect_format(self, file_path: Path) -> str:
        """
        تشخیص فرمت فایل
        
        Args:
            file_path: مسیر فایل
            
        Returns:
            فرمت فایل
        """
        suffix = file_path.suffix.lower()
        
        if suffix in ['.yml', '.yaml']:
            return 'yaml'
        elif suffix == '.csv':
            return 'csv'
        elif suffix == '.json':
            return 'json'
        else:
            # سعی می‌کنیم با محتوا تشخیص دهیم
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024)
                
                if content.strip().startswith('{') or content.strip().startswith('['):
                    return 'json'
                elif '---' in content or ': ' in content:
                    return 'yaml'
                elif ',' in content or ';' in content:
                    return 'csv'
                else:
                    raise ValueError(f"فرمت فایل نامشخص: {file_path}")
            except Exception:
                raise ValueError(f"فرمت فایل نامشخص: {file_path}")
    
    def load_inventory(self, inventory_path: Union[str, Path]) -> bool:
        """
        بارگذاری فایل inventory از فرمت‌های مختلف
        
        Args:
            inventory_path: مسیر فایل inventory
            
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            self.inventory_path = Path(inventory_path)
            
            if not self.inventory_path.exists():
                logger.error(f"Inventory file not found: {inventory_path}")
                return False
            
            # تشخیص فرمت
            self.file_format = self.detect_format(self.inventory_path)
            logger.info(f"Loading inventory from {self.file_format.upper()} file: {inventory_path}")
            
            # بارگذاری بر اساس فرمت
            if self.file_format == 'yaml':
                self._load_yaml_inventory()
            elif self.file_format == 'csv':
                self._load_csv_inventory()
            elif self.file_format == 'json':
                self._load_json_inventory()
            else:
                raise ValueError(f"فرمت پشتیبانی نشده: {self.file_format}")
            
            # پردازش ساختار inventory
            self._process_inventory()
            
            logger.info(f"Inventory loaded successfully: {inventory_path}")
            logger.info(f"Total hosts: {len(self.hosts)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading inventory: {str(e)}", exc_info=True)
            return False
    
    def _load_yaml_inventory(self):
        """بارگذاری فایل YAML"""
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.inventory_data = yaml.safe_load(content)
    
    def _load_csv_inventory(self):
        """بارگذاری فایل CSV"""
        try:
            # ابتدا با pandas امتحان می‌کنیم
            try:
                df = pd.read_csv(self.inventory_path, encoding='utf-8')
                self.inventory_data = df.to_dict('records')
                return
            except Exception as e:
                logger.debug(f"Pandas CSV load failed, trying standard CSV: {str(e)}")
            
            # روش استاندارد CSV
            with open(self.inventory_path, 'r', encoding='utf-8') as f:
                # تشخیص delimiter
                sample = f.read(1024)
                f.seek(0)
                
                delimiter = ','
                if ';' in sample and ',' not in sample:
                    delimiter = ';'
                elif '\t' in sample and ',' not in sample and ';' not in sample:
                    delimiter = '\t'
                
                reader = csv.DictReader(f, delimiter=delimiter)
                self.inventory_data = list(reader)
                
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            raise
    
    def _load_json_inventory(self):
        """بارگذاری فایل JSON"""
        with open(self.inventory_path, 'r', encoding='utf-8') as f:
            self.inventory_data = json.load(f)
    
    def _process_inventory(self):
        """پردازش داده‌های inventory"""
        try:
            if self.file_format == 'yaml':
                self._process_yaml_inventory()
            elif self.file_format == 'csv':
                self._process_csv_inventory()
            elif self.file_format == 'json':
                self._process_json_inventory()
            
            # اعمال inheritance متغیرها
            self._apply_variable_inheritance()
            
        except Exception as e:
            logger.error(f"Error processing inventory: {str(e)}")
            raise
    
    def _process_yaml_inventory(self):
        """پردازش inventory YAML"""
        # استخراج hosts و groups
        if 'all' in self.inventory_data:
            all_data = self.inventory_data['all']
            
            # استخراج hosts از all
            if 'hosts' in all_data:
                self.hosts = all_data['hosts']
            
            # استخراج vars از all
            if 'vars' in all_data:
                self.all_vars = all_data['vars']
            else:
                self.all_vars = {}
            
            # پردازش groupها
            self._process_yaml_groups(all_data)
        
        # همچنین ممکن است hosts در ریشه باشند
        elif 'hosts' in self.inventory_data:
            self.hosts = self.inventory_data['hosts']
    
    def _process_yaml_groups(self, all_data: Dict):
        """پردازش groupهای YAML"""
        if 'children' in all_data:
            def process_group(groups_data: Dict, parent_path: str = ''):
                for group_name, group_data in groups_data.items():
                    full_path = f"{parent_path}.{group_name}" if parent_path else group_name
                    
                    # ذخیره group
                    self.groups[full_path] = {
                        'name': group_name,
                        'full_path': full_path,
                        'parent': parent_path,
                        'data': group_data
                    }
                    
                    # استخراج hosts این group
                    if 'hosts' in group_data:
                        group_hosts = group_data['hosts']
                        if isinstance(group_hosts, dict):
                            for host_name, host_vars in group_hosts.items():
                                if host_name not in self.hosts:
                                    self.hosts[host_name] = {}
                                self.hosts[host_name].update(host_vars)
                                if 'groups' not in self.hosts[host_name]:
                                    self.hosts[host_name]['groups'] = []
                                self.hosts[host_name]['groups'].append(full_path)
                    
                    # پردازش children اگر وجود دارد
                    if 'children' in group_data:
                        process_group(group_data['children'], full_path)
            
            process_group(all_data['children'])
    
    def _process_csv_inventory(self):
        """پردازش inventory CSV"""
        if not self.inventory_data:
            return
        
        # فرض می‌کنیم هر ردیف یک host است
        # ستون 'host' یا مشابه آن شناسه host است
        host_id_column = None
        
        # پیدا کردن ستون شناسه host
        first_row = self.inventory_data[0] if isinstance(self.inventory_data, list) else self.inventory_data
        if isinstance(first_row, dict):
            possible_host_columns = ['host', 'hostname', 'server', 'name', 'customer', 'customer_name']
            for col in possible_host_columns:
                if col in first_row:
                    host_id_column = col
                    break
            
            if not host_id_column:
                # از اولین ستون غیرخالی استفاده کن
                for col in first_row.keys():
                    if first_row[col] and str(first_row[col]).strip():
                        host_id_column = col
                        break
            
            if not host_id_column:
                raise ValueError("ستون شناسه host در فایل CSV یافت نشد")
            
            # تبدیل ردیف‌ها به hosts
            for row in self.inventory_data:
                host_name = str(row.get(host_id_column, '')).strip()
                if not host_name:
                    continue
                
                # تبدیل مقادیر
                host_vars = {}
                for key, value in row.items():
                    if key != host_id_column:
                        # تبدیل مقادیر به نوع مناسب
                        processed_value = self._convert_value(value)
                        host_vars[key] = processed_value
                
                self.hosts[host_name] = host_vars
        
        # استخراج all_vars از ردیف‌های خاص یا فایل جداگانه
        self._extract_csv_global_vars()
    
    def _convert_value(self, value):
        """تبدیل مقدار CSV به نوع مناسب"""
        if value is None:
            return None
        
        str_value = str(value).strip()
        
        if str_value == '':
            return None
        
        # بررسی boolean
        if str_value.lower() in ['true', 'yes', '1', 'on']:
            return True
        elif str_value.lower() in ['false', 'no', '0', 'off']:
            return False
        
        # بررسی عدد
        try:
            if '.' in str_value:
                return float(str_value)
            else:
                return int(str_value)
        except ValueError:
            pass
        
        # بررسی لیست (مقادیر جدا شده با کاما)
        if ',' in str_value and '{{' not in str_value:
            items = [item.strip() for item in str_value.split(',')]
            # سعی کن به عدد تبدیل کن
            converted_items = []
            for item in items:
                try:
                    converted_items.append(int(item))
                except ValueError:
                    try:
                        converted_items.append(float(item))
                    except ValueError:
                        converted_items.append(item)
            return converted_items
        
        return str_value
    
    def _extract_csv_global_vars(self):
        """استخراج متغیرهای global از CSV"""
        # می‌توانیم از ستون‌های خاصی به عنوان global vars استفاده کنیم
        # یا از فایل جداگانه ای بخوانیم
        # در اینجا فرض می‌کنیم ستون‌هایی که برای همه hosts یکسان هستند global هستند
        
        if not self.hosts:
            return
        
        # پیدا کردن ستون‌های با مقدار یکسان در همه hosts
        first_host = next(iter(self.hosts.values()))
        global_candidates = {}
        
        for key in first_host.keys():
            values = set()
            for host_vars in self.hosts.values():
                values.add(str(host_vars.get(key, '')))
            
            if len(values) == 1:
                # مقدار یکسان برای همه hosts
                global_candidates[key] = first_host[key]
        
        # حذف این مقادیر از host vars و اضافه به all_vars
        for key, value in global_candidates.items():
            self.all_vars[key] = value
            for host_vars in self.hosts.values():
                if key in host_vars:
                    del host_vars[key]
    
    def _process_json_inventory(self):
        """پردازش inventory JSON"""
        # ساختار JSON می‌تواند مشابه YAML باشد
        if isinstance(self.inventory_data, dict):
            if 'all' in self.inventory_data:
                self._process_yaml_inventory()  # از همان منطق YAML استفاده کن
            elif 'hosts' in self.inventory_data:
                self.hosts = self.inventory_data['hosts']
        elif isinstance(self.inventory_data, list):
            # لیست hosts
            for i, host_data in enumerate(self.inventory_data):
                host_name = host_data.get('host', f'host_{i}')
                self.hosts[host_name] = host_data
    
    def _apply_variable_inheritance(self):
        """اعمال inheritance متغیرها از groups به hosts"""
        for host_name, host_data in self.hosts.items():
            # دریافت groupهای این host
            host_groups = host_data.get('groups', [])
            
            # جمع‌آوری متغیرها از همه groupها
            all_group_vars = {}
            
            for group_path in host_groups:
                group = self.groups.get(group_path)
                if group and 'data' in group:
                    group_data = group['data']
                    if 'vars' in group_data:
                        all_group_vars.update(group_data['vars'])
            
            # اعمال متغیرهای group به host (با اولویت host vars)
            host_data.update(all_group_vars)
            
            # اعمال all_vars (با کمترین اولویت)
            host_data.update(self.all_vars)
    
    def get_host(self, hostname: str) -> Optional[Dict]:
        """
        دریافت اطلاعات یک host
        
        Args:
            hostname: نام host
            
        Returns:
            اطلاعات host یا None
        """
        return self.hosts.get(hostname)
    
    def get_host_vars(self, hostname: str) -> Dict:
        """
        دریافت متغیرهای یک host
        
        Args:
            hostname: نام host
            
        Returns:
            دیکشنری متغیرهای host
        """
        host_data = self.get_host(hostname)
        if host_data:
            # حذف فیلدهای غیرمتغیر
            vars_data = host_data.copy()
            vars_data.pop('groups', None)
            return vars_data
        return {}
    
    def get_group(self, group_name: str) -> Optional[Dict]:
        """
        دریافت اطلاعات یک group
        
        Args:
            group_name: نام group
            
        Returns:
            اطلاعات group یا None
        """
        return self.groups.get(group_name)
    
    def get_group_hosts(self, group_name: str) -> List[str]:
        """
        دریافت لیست hosts یک group
        
        Args:
            group_name: نام group
            
        Returns:
            لیست نام hosts
        """
        hosts_in_group = []
        
        for host_name, host_data in self.hosts.items():
            if 'groups' in host_data and group_name in host_data['groups']:
                hosts_in_group.append(host_name)
        
        return hosts_in_group
    
    def list_hosts(self) -> List[str]:
        """لیست تمام hosts"""
        return list(self.hosts.keys())
    
    def list_groups(self) -> List[str]:
        """لیست تمام groups"""
        return list(self.groups.keys())
    
    def search_hosts(self, pattern: str) -> List[str]:
        """
        جستجوی hosts با الگو
        
        Args:
            pattern: الگوی جستجو (regex)
            
        Returns:
            لیست hosts مطابق
        """
        import re
        regex = re.compile(pattern)
        return [host for host in self.hosts.keys() if regex.search(host)]
    
    def get_all_variables(self) -> Dict:
        """دریافت تمام متغیرهای سیستم"""
        all_vars = self.all_vars.copy()
        
        for host_name, host_vars in self.hosts.items():
            # اضافه کردن host vars با prefix
            for key, value in host_vars.items():
                if key != 'groups':
                    all_vars[f"{host_name}_{key}"] = value
        
        return all_vars
    
    def resolve_variable(self, hostname: str, var_name: str, default: Any = None) -> Any:
        """
        resolve کردن یک متغیر برای host خاص
        
        Args:
            hostname: نام host
            var_name: نام متغیر
            default: مقدار پیش‌فرض
            
        Returns:
            مقدار متغیر
        """
        # اول host vars را بررسی کن
        host_vars = self.get_host_vars(hostname)
        if var_name in host_vars:
            return host_vars[var_name]
        
        # سپس group vars را بررسی کن
        host_data = self.get_host(hostname)
        if host_data and 'groups' in host_data:
            for group_name in host_data['groups']:
                group = self.get_group(group_name)
                if group and 'data' in group and 'vars' in group['data']:
                    if var_name in group['data']['vars']:
                        return group['data']['vars'][var_name]
        
        # سپس all_vars را بررسی کن
        if var_name in self.all_vars:
            return self.all_vars[var_name]
        
        # اگر پیدا نشد، default را برگردان
        return default
    
    def expand_variables(self, hostname: str, template: str) -> str:
        """
        expand کردن متغیرها در یک template
        
        Args:
            hostname: نام host
            template: template با متغیرها
            
        Returns:
            template expand شده
        """
        result = template
        
        # جمع‌آوری تمام متغیرها
        all_vars = {}
        all_vars.update(self.all_vars)
        
        host_data = self.get_host(hostname)
        if host_data:
            # اضافه کردن host vars
            for key, value in host_data.items():
                if key != 'groups':
                    all_vars[key] = value
            
            # اضافه کردن group vars
            if 'groups' in host_data:
                for group_name in host_data['groups']:
                    group = self.get_group(group_name)
                    if group and 'data' in group and 'vars' in group['data']:
                        all_vars.update(group['data']['vars'])
        
        # جایگزینی متغیرها
        for var_name, var_value in all_vars.items():
            placeholder = f"{{{{ {var_name} }}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))
        
        # همچنین inventory_hostname را اضافه کن
        if "{{ inventory_hostname }}" in result:
            result = result.replace("{{ inventory_hostname }}", hostname)
        
        return result
    
    def validate_inventory(self) -> Dict:
        """
        اعتبارسنجی inventory
        
        Returns:
            نتایج اعتبارسنجی
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'hosts_count': len(self.hosts),
            'groups_count': len(self.groups),
            'file_format': self.file_format
        }
        
        # بررسی hosts تکراری
        seen_hosts = set()
        for host in self.hosts.keys():
            if host in seen_hosts:
                validation_results['warnings'].append(f"Duplicate host entry: {host}")
            seen_hosts.add(host)
        
        # بررسی groupهای بدون host
        for group_name, group_data in self.groups.items():
            hosts_in_group = self.get_group_hosts(group_name)
            if not hosts_in_group:
                validation_results['warnings'].append(f"Group {group_name} has no hosts")
        
        # بررسی referenceهای ناموجود
        for host_name, host_data in self.hosts.items():
            if 'groups' in host_data:
                for group_name in host_data['groups']:
                    if group_name not in self.groups:
                        validation_results['errors'].append(
                            f"Host {host_name} references non-existent group: {group_name}"
                        )
        
        # بررسی ستون‌های ضروری برای CSV
        if self.file_format == 'csv' and self.hosts:
            first_host = next(iter(self.hosts.values()))
            required_columns = ['customer_state', 'customer_containers']
            for column in required_columns:
                if column not in first_host:
                    validation_results['warnings'].append(f"Missing recommended column: {column}")
        
        validation_results['valid'] = len(validation_results['errors']) == 0
        
        return validation_results
    
    def save_inventory(self, output_path: Union[str, Path], format: str = None) -> bool:
        """
        ذخیره inventory به فایل
        
        Args:
            output_path: مسیر خروجی
            format: فرمت خروجی (yaml, csv, json)
            
        Returns:
            True اگر موفقیت‌آمیز باشد
        """
        try:
            output_path = Path(output_path)
            
            if not format:
                format = self.file_format or 'yaml'
            
            if format == 'yaml':
                return self._save_yaml_inventory(output_path)
            elif format == 'csv':
                return self._save_csv_inventory(output_path)
            elif format == 'json':
                return self._save_json_inventory(output_path)
            else:
                raise ValueError(f"فرمت پشتیبانی نشده: {format}")
            
        except Exception as e:
            logger.error(f"Error saving inventory: {str(e)}")
            return False
    
    def _save_yaml_inventory(self, output_path: Path) -> bool:
        """ذخیره به YAML"""
        output_data = {}
        
        if self.all_vars or self.groups or self.hosts:
            output_data['all'] = {}
            
            if self.all_vars:
                output_data['all']['vars'] = self.all_vars
            
            if self.hosts:
                # سازماندهی hosts بر اساس groupها
                hosts_by_group = {}
                for host_name, host_data in self.hosts.items():
                    groups = host_data.get('groups', [])
                    if groups:
                        for group in groups:
                            if group not in hosts_by_group:
                                hosts_by_group[group] = {}
                            # فقط host vars را ذخیره کن (بدون groups)
                            host_vars = {k: v for k, v in host_data.items() if k != 'groups'}
                            hosts_by_group[group][host_name] = host_vars
                    else:
                        # hosts بدون group
                        if 'ungrouped' not in hosts_by_group:
                            hosts_by_group['ungrouped'] = {}
                        host_vars = {k: v for k, v in host_data.items() if k != 'groups'}
                        hosts_by_group['ungrouped'][host_name] = host_vars
                
                # ساختار groupها
                if hosts_by_group:
                    output_data['all']['children'] = {}
                    
                    for group_name, group_hosts in hosts_by_group.items():
                        if group_name == 'ungrouped':
                            # مستقیماً به all اضافه کن
                            output_data['all']['hosts'] = group_hosts
                        else:
                            output_data['all']['children'][group_name] = {
                                'hosts': group_hosts
                            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(output_data, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Inventory saved as YAML: {output_path}")
        return True
    
    def _save_csv_inventory(self, output_path: Path) -> bool:
        """ذخیره به CSV"""
        if not self.hosts:
            logger.warning("No hosts to save as CSV")
            return False
        
        # جمع‌آوری تمام ستون‌ها
        all_columns = set()
        for host_data in self.hosts.values():
            all_columns.update(host_data.keys())
        
        # حذف ستون groups
        all_columns.discard('groups')
        
        # ستون host را اول قرار بده
        columns = ['host'] + sorted([col for col in all_columns if col != 'host'])
        
        # اضافه کردن all_vars به عنوان ردیف جداگانه
        rows = []
        
        # ابتدا ردیف all_vars
        if self.all_vars:
            all_vars_row = {'host': '_all_vars'}
            for col in columns:
                if col == 'host':
                    continue
                all_vars_row[col] = self.all_vars.get(col, '')
            rows.append(all_vars_row)
        
        # سپس hosts
        for host_name, host_data in self.hosts.items():
            row = {'host': host_name}
            for col in columns:
                if col == 'host':
                    continue
                row[col] = host_data.get(col, '')
            rows.append(row)
        
        # نوشتن به CSV
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Inventory saved as CSV: {output_path}")
        return True
    
    def _save_json_inventory(self, output_path: Path) -> bool:
        """ذخیره به JSON"""
        output_data = {
            'hosts': self.hosts,
            'all_vars': self.all_vars,
            'groups': self.groups,
            'file_format': self.file_format
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Inventory saved as JSON: {output_path}")
        return True
    
    def to_dict(self) -> Dict:
        """تبدیل inventory به دیکشنری"""
        return {
            'inventory_path': str(self.inventory_path) if self.inventory_path else None,
            'file_format': self.file_format,
            'hosts': self.hosts,
            'groups': self.groups,
            'all_vars': self.all_vars
        }
    
    def to_json(self) -> str:
        """تبدیل inventory به JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    def print_summary(self):
        """چاپ خلاصه inventory"""
        print("=" * 60)
        print("INVENTORY SUMMARY")
        print("=" * 60)
        print(f"Path: {self.inventory_path}")
        print(f"Format: {self.file_format.upper() if self.file_format else 'N/A'}")
        print(f"Total Hosts: {len(self.hosts)}")
        print(f"Total Groups: {len(self.groups)}")
        print()
        
        print("HOSTS:")
        print("-" * 30)
        for host_name in sorted(self.hosts.keys())[:5]:  # نمایش 5 host اول
            host_data = self.hosts[host_name]
            groups = host_data.get('groups', [])
            print(f"  {host_name}")
            if groups:
                print(f"    Groups: {', '.join(groups)}")
            # نمایش چند متغیر مهم
            important_vars = ['customer_state', 'customer_containers', 'customer_domain']
            for var in important_vars:
                if var in host_data:
                    print(f"    {var}: {host_data[var]}")
            print()
        
        if len(self.hosts) > 5:
            print(f"  ... and {len(self.hosts) - 5} more hosts")
            print()
        
        if self.groups:
            print("GROUPS:")
            print("-" * 30)
            for group_name, group_data in sorted(self.groups.items())[:3]:  # نمایش 3 group اول
                hosts_count = len(self.get_group_hosts(group_name))
                print(f"  {group_name}")
                print(f"    Parent: {group_data.get('parent', 'None')}")
                print(f"    Hosts: {hosts_count}")
                print()
        
        print("=" * 60)


# تابع helper برای استفاده سریع
def load_inventory_file(inventory_path: str) -> Optional[InventoryLoader]:
    """
    بارگذاری فایل inventory
    
    Args:
        inventory_path: مسیر فایل inventory
        
    Returns:
        InventoryLoader instance یا None
    """
    try:
        loader = InventoryLoader(inventory_path)
        if loader.hosts:
            return loader
        return None
    except Exception as e:
        logger.error(f"Failed to load inventory: {str(e)}")
        return None


def convert_inventory_format(input_path: str, output_path: str, output_format: str = None) -> bool:
    """
    تبدیل فرمت inventory
    
    Args:
        input_path: مسیر فایل ورودی
        output_path: مسیر فایل خروجی
        output_format: فرمت خروجی (yaml, csv, json)
        
    Returns:
        True اگر موفقیت‌آمیز باشد
    """
    try:
        loader = InventoryLoader(input_path)
        if not loader.hosts:
            logger.error(f"No hosts found in {input_path}")
            return False
        
        if not output_format:
            output_format = Path(output_path).suffix[1:]  # حذف نقطه
        
        return loader.save_inventory(output_path, output_format)
        
    except Exception as e:
        logger.error(f"Error converting inventory: {str(e)}")
        return False


# برای backward compatibility
def get_host_variables(inventory_path: str, hostname: str) -> Dict:
    """
    دریافت متغیرهای یک host
    
    Args:
        inventory_path: مسیر فایل inventory
        hostname: نام host
        
    Returns:
        دیکشنری متغیرهای host
    """
    loader = load_inventory_file(inventory_path)
    if loader:
        return loader.get_host_vars(hostname)
    return {}


def resolve_template(inventory_path: str, hostname: str, template: str) -> str:
    """
    resolve کردن template با متغیرهای host
    
    Args:
        inventory_path: مسیر inventory
        hostname: نام host
        template: template
        
    Returns:
        template resolve شده
    """
    loader = load_inventory_file(inventory_path)
    if loader:
        return loader.expand_variables(hostname, template)
    return template


if __name__ == "__main__":
    # مثال استفاده
    import argparse
    
    parser = argparse.ArgumentParser(description="Inventory Loader CLI - پشتیبانی از CSV و YAML")
    parser.add_argument('--inventory', '-i', required=True,
                       help='Path to inventory file (YAML, CSV, or JSON)')
    parser.add_argument('--host', help='Get specific host info')
    parser.add_argument('--group', help='Get specific group info')
    parser.add_argument('--list-hosts', action='store_true',
                       help='List all hosts')
    parser.add_argument('--list-groups', action='store_true',
                       help='List all groups')
    parser.add_argument('--validate', action='store_true',
                       help='Validate inventory')
    parser.add_argument('--summary', action='store_true',
                       help='Print inventory summary')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')
    parser.add_argument('--convert', help='Convert to different format (yaml, csv, json)')
    parser.add_argument('--output', '-o', help='Output file for conversion')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # تنظیم logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # اگر convert درخواست شده
    if args.convert:
        if not args.output:
            print("Error: Output file required for conversion")
            sys.exit(1)
        
        success = convert_inventory_format(args.inventory, args.output, args.convert)
        sys.exit(0 if success else 1)
    
    # بارگذاری inventory
    loader = InventoryLoader(args.inventory)
    
    if not loader.hosts:
        print(f"Error: No hosts found in inventory {args.inventory}")
        sys.exit(1)
    
    # اجرای دستورات
    if args.host:
        host_vars = loader.get_host_vars(args.host)
        if args.json:
            print(json.dumps(host_vars, indent=2, default=str))
        else:
            print(f"Variables for host '{args.host}':")
            for key, value in host_vars.items():
                print(f"  {key}: {value}")
    
    elif args.group:
        group_info = loader.get_group(args.group)
        if group_info:
            if args.json:
                print(json.dumps(group_info, indent=2, default=str))
            else:
                print(f"Group '{args.group}':")
                for key, value in group_info.items():
                    print(f"  {key}: {value}")
        else:
            print(f"Group '{args.group}' not found")
    
    elif args.list_hosts:
        hosts = loader.list_hosts()
        if args.json:
            print(json.dumps(hosts, indent=2))
        else:
            print("Hosts:")
            for host in hosts:
                print(f"  - {host}")
    
    elif args.list_groups:
        groups = loader.list_groups()
        if args.json:
            print(json.dumps(groups, indent=2))
        else:
            print("Groups:")
            for group in groups:
                print(f"  - {group}")
    
    elif args.validate:
        results = loader.validate_inventory()
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print("Validation Results:")
            print(f"  Valid: {results['valid']}")
            print(f"  Format: {results.get('file_format', 'N/A')}")
            print(f"  Hosts: {results['hosts_count']}")
            print(f"  Groups: {results['groups_count']}")
            
            if results['errors']:
                print("  Errors:")
                for error in results['errors']:
                    print(f"    - {error}")
            
            if results['warnings']:
                print("  Warnings:")
                for warning in results['warnings']:
                    print(f"    - {warning}")
    
    elif args.summary:
        loader.print_summary()
    
    elif args.json:
        # خروجی کامل به JSON
        print(loader.to_json())
    
    else:
        # حالت پیش‌فرض: نمایش خلاصه
        loader.print_summary()