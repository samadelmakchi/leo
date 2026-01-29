#!/usr/bin/env python3
"""
Task 08: SQL and Uploads Restoration
جایگزین task انسیبل: 08-sql-and-uploads.yml
"""

import logging
import sys
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, List, Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class SqlAndUploadsTask(BaseTask):
    """بازگردانی SQL و upload فایل‌ها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="sql_and_uploads", config=config)
        
        self.file_mgr = FileManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'project_path',
            'inventory_hostname',
            'playbook_dir'
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
    
    def find_file(self, pattern: str) -> Optional[str]:
        """
        یافتن فایل با الگوی داده شده
        
        Args:
            pattern: الگوی فایل (glob)
            
        Returns:
            مسیر فایل یا None
        """
        try:
            files = list(Path(self.config['playbook_dir']).glob(pattern))
            if files:
                return str(files[0])
            return None
        except Exception as e:
            logger.warning(f"Error searching for file {pattern}: {str(e)}")
            return None
    
    def copy_file(self, src: str, dest: str, mode: int = None, force: bool = True) -> Dict:
        """
        کپی کردن فایل
        
        Args:
            src: مسیر مبدأ
            dest: مسیر مقصد
            mode: mode فایل
            force: overwrite اگر وجود دارد
            
        Returns:
            نتیجه عملیات
        """
        try:
            if not Path(src).exists():
                return {
                    'success': False,
                    'error': f"Source file does not exist: {src}",
                    'skipped': True
                }
            
            # کپی فایل
            shutil.copy2(src, dest)
            
            # تنظیم permissions اگر mode مشخص شده
            if mode:
                os.chmod(dest, mode)
            
            logger.debug(f"Copied {src} to {dest}")
            return {
                'success': True,
                'changed': True,
                'source': src,
                'destination': dest,
                'message': f"File copied successfully"
            }
            
        except Exception as e:
            error_msg = f"Error copying {src} to {dest}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def extract_archive(self, archive_path: str, dest_dir: str, exclude: List[str] = None) -> Dict:
        """
        استخراج archive
        
        Args:
            archive_path: مسیر فایل archive
            dest_dir: دایرکتوری مقصد
            exclude: لیست فایل‌های exclude
            
        Returns:
            نتیجه عملیات
        """
        try:
            if not Path(archive_path).exists():
                return {
                    'success': False,
                    'error': f"Archive file does not exist: {archive_path}",
                    'skipped': True
                }
            
            # ایجاد دایرکتوری مقصد
            Path(dest_dir).mkdir(parents=True, exist_ok=True)
            
            # تشخیص نوع archive
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    # استخراج با exclude
                    for file_info in zip_ref.infolist():
                        # بررسی exclude
                        if exclude:
                            should_exclude = any(
                                excl in file_info.filename for excl in exclude
                            )
                            if should_exclude:
                                continue
                        
                        # استخراج فایل
                        zip_ref.extract(file_info, dest_dir)
                
                logger.debug(f"Extracted ZIP {archive_path} to {dest_dir}")
                
            elif archive_path.endswith(('.tar', '.tar.gz', '.tgz')):
                mode = 'r:gz' if archive_path.endswith(('.tar.gz', '.tgz')) else 'r'
                with tarfile.open(archive_path, mode) as tar_ref:
                    # استخراج با exclude
                    members = []
                    for member in tar_ref.getmembers():
                        if exclude:
                            should_exclude = any(
                                excl in member.name for excl in exclude
                            )
                            if should_exclude:
                                continue
                        members.append(member)
                    
                    tar_ref.extractall(dest_dir, members=members)
                
                logger.debug(f"Extracted TAR {archive_path} to {dest_dir}")
                
            else:
                return {
                    'success': False,
                    'error': f"Unsupported archive format: {archive_path}"
                }
            
            return {
                'success': True,
                'changed': True,
                'archive': archive_path,
                'destination': dest_dir,
                'message': f"Archive extracted successfully"
            }
            
        except Exception as e:
            error_msg = f"Error extracting {archive_path}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def restore_gateway(self) -> Dict:
        """بازگردانی Gateway"""
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            playbook_dir = self.config['playbook_dir']
            
            results = []
            
            # 1. پیدا کردن فایل SQL
            sql_patterns = [
                f'sql/{inventory_hostname}_gateway.sql',
                'sql/default_gateway.sql'
            ]
            
            sql_source = None
            for pattern in sql_patterns:
                sql_source = self.find_file(pattern)
                if sql_source:
                    break
            
            if sql_source:
                sql_dest = Path(project_path) / inventory_hostname / 'gateway' / 'docker' / 'init' / 'install.sql'
                result = self.copy_file(sql_source, str(sql_dest), mode=0o644, force=True)
                results.append({
                    'step': 'gateway_sql_copy',
                    'result': result
                })
            else:
                logger.warning(f"No SQL file found for gateway {inventory_hostname}")
                results.append({
                    'step': 'gateway_sql_copy',
                    'result': {
                        'success': True,
                        'skipped': True,
                        'message': 'No SQL file found'
                    }
                })
            
            # 2. کپی uploads
            uploads_source = self.find_file(f'sql/{inventory_hostname}_gateway_uploads.zip')
            if uploads_source:
                # کپی به /tmp
                temp_path = f"/tmp/{inventory_hostname}_gateway_uploads.zip"
                copy_result = self.copy_file(uploads_source, temp_path, force=True)
                results.append({
                    'step': 'gateway_uploads_copy',
                    'result': copy_result
                })
                
                if copy_result['success']:
                    # استخراج uploads
                    dest_dir = Path(project_path) / inventory_hostname / 'gateway' / 'admin' / 'uploads'
                    extract_result = self.extract_archive(
                        temp_path,
                        str(dest_dir),
                        exclude=['index.html']
                    )
                    results.append({
                        'step': 'gateway_uploads_extract',
                        'result': extract_result
                    })
            else:
                logger.debug(f"No gateway uploads found for {inventory_hostname}")
                results.append({
                    'step': 'gateway_uploads',
                    'result': {
                        'success': True,
                        'skipped': True,
                        'message': 'No uploads file found'
                    }
                })
            
            # خلاصه results
            success = all(r['result']['success'] or r['result'].get('skipped', False) for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'gateway',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error restoring gateway: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'service': 'gateway'
            }
    
    def restore_portal(self) -> Dict:
        """بازگردانی Portal"""
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            results = []
            
            # پیدا کردن فایل SQL
            sql_source = self.find_file(f'sql/{inventory_hostname}_portal.sql')
            if sql_source:
                sql_dest = Path(project_path) / inventory_hostname / 'portal' / 'docker' / 'init' / 'install.sql'
                result = self.copy_file(sql_source, str(sql_dest), mode=0o644, force=True)
                results.append({
                    'step': 'portal_sql_copy',
                    'result': result
                })
            else:
                logger.debug(f"No portal SQL found for {inventory_hostname}")
                results.append({
                    'step': 'portal_sql_copy',
                    'result': {
                        'success': True,
                        'skipped': True,
                        'message': 'No SQL file found'
                    }
                })
            
            # خلاصه results
            success = all(r['result']['success'] or r['result'].get('skipped', False) for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'portal',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error restoring portal: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'service': 'portal'
            }
    
    def restore_frontend(self) -> Dict:
        """بازگردانی Frontend"""
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            results = []
            
            # پیدا کردن فایل frontend
            frontend_source = self.find_file(f'sql/{inventory_hostname}_frontend.zip')
            if frontend_source:
                # کپی به /tmp
                temp_path = f"/tmp/{inventory_hostname}_frontend.zip"
                copy_result = self.copy_file(frontend_source, temp_path, force=True)
                results.append({
                    'step': 'frontend_copy',
                    'result': copy_result
                })
                
                if copy_result['success']:
                    # استخراج frontend
                    dest_dir = Path(project_path) / inventory_hostname / 'portal-frontend'
                    extract_result = self.extract_archive(
                        temp_path,
                        str(dest_dir),
                        exclude=['node_modules', '.git']
                    )
                    results.append({
                        'step': 'frontend_extract',
                        'result': extract_result
                    })
            else:
                logger.debug(f"No frontend found for {inventory_hostname}")
                results.append({
                    'step': 'frontend',
                    'result': {
                        'success': True,
                        'skipped': True,
                        'message': 'No frontend file found'
                    }
                })
            
            # خلاصه results
            success = all(r['result']['success'] or r['result'].get('skipped', False) for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'frontend',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error restoring frontend: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'service': 'frontend'
            }
    
    def restore_lms(self) -> Dict:
        """بازگردانی LMS"""
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            results = []
            
            # 1. SQL
            sql_source = self.find_file(f'sql/{inventory_hostname}_lms.sql')
            if sql_source:
                sql_dest = Path(project_path) / inventory_hostname / 'lms' / 'docker' / 'init' / 'install.sql'
                result = self.copy_file(sql_source, str(sql_dest), mode=0o644, force=True)
                results.append({
                    'step': 'lms_sql_copy',
                    'result': result
                })
            
            # 2. Uploads
            uploads_source = self.find_file(f'sql/{inventory_hostname}_lms_uploads.zip')
            if uploads_source:
                temp_path = f"/tmp/{inventory_hostname}_lms_uploads.zip"
                copy_result = self.copy_file(uploads_source, temp_path, force=True)
                results.append({
                    'step': 'lms_uploads_copy',
                    'result': copy_result
                })
                
                if copy_result['success']:
                    dest_dir = Path(project_path) / inventory_hostname / 'lms' / 'storage' / 'app'
                    extract_result = self.extract_archive(temp_path, str(dest_dir))
                    results.append({
                        'step': 'lms_uploads_extract',
                        'result': extract_result
                    })
            
            # 3. .env
            env_source = self.find_file(f'sql/{inventory_hostname}_lms.env')
            if env_source:
                env_dest = Path(project_path) / inventory_hostname / 'lms' / '.env'
                result = self.copy_file(env_source, str(env_dest), mode=0o600, force=True)
                results.append({
                    'step': 'lms_env_copy',
                    'result': result
                })
            
            # اگر هیچ فایلی پیدا نشد
            if len(results) == 0:
                results.append({
                    'step': 'lms_restore',
                    'result': {
                        'success': True,
                        'skipped': True,
                        'message': 'No LMS files found'
                    }
                })
            
            # خلاصه results
            success = all(r['result']['success'] or r['result'].get('skipped', False) for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'lms',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error restoring lms: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'service': 'lms'
            }
    
    def restore_file(self) -> Dict:
        """بازگردانی File Storage"""
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            results = []
            
            # 1. SQL
            sql_source = self.find_file(f'sql/{inventory_hostname}_file.sql')
            if sql_source:
                sql_dest = Path(project_path) / inventory_hostname / 'file' / 'docker' / 'init' / 'install.sql'
                result = self.copy_file(sql_source, str(sql_dest), mode=0o644, force=True)
                results.append({
                    'step': 'file_sql_copy',
                    'result': result
                })
            
            # 2. Uploads
            uploads_source = self.find_file(f'sql/{inventory_hostname}_file_uploads.zip')
            if uploads_source:
                temp_path = f"/tmp/{inventory_hostname}_file_uploads.zip"
                copy_result = self.copy_file(uploads_source, temp_path, force=True)
                results.append({
                    'step': 'file_uploads_copy',
                    'result': copy_result
                })
                
                if copy_result['success']:
                    dest_dir = Path(project_path) / inventory_hostname / 'file' / 'storage' / 'app'
                    extract_result = self.extract_archive(temp_path, str(dest_dir))
                    results.append({
                        'step': 'file_uploads_extract',
                        'result': extract_result
                    })
            
            # 3. .env
            env_source = self.find_file(f'sql/{inventory_hostname}_file.env')
            if env_source:
                env_dest = Path(project_path) / inventory_hostname / 'file' / '.env'
                result = self.copy_file(env_source, str(env_dest), mode=0o600, force=True)
                results.append({
                    'step': 'file_env_copy',
                    'result': result
                })
            
            # اگر هیچ فایلی پیدا نشد
            if len(results) == 0:
                results.append({
                    'step': 'file_restore',
                    'result': {
                        'success': True,
                        'skipped': True,
                        'message': 'No file storage files found'
                    }
                })
            
            # خلاصه results
            success = all(r['result']['success'] or r['result'].get('skipped', False) for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'file',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error restoring file storage: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'service': 'file'
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
                logger.info("Customer state is not 'up', skipping SQL and uploads")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                })
            
            # اجرای restore برای هر سرویس
            services = [
                ('gateway', self.restore_gateway),
                ('portal', self.restore_portal),
                ('frontend', self.restore_frontend),
                ('lms', self.restore_lms),
                ('file', self.restore_file)
            ]
            
            results = []
            all_success = True
            any_changed = False
            
            for service_name, restore_func in services:
                logger.info(f"Restoring {service_name}...")
                result = restore_func()
                results.append({
                    'service': service_name,
                    'result': result
                })
                
                if not result['success']:
                    all_success = False
                
                if result.get('changed', False):
                    any_changed = True
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'services': results,
                'customer_state': self.config.get('customer_state'),
                'inventory_hostname': self.config.get('inventory_hostname')
            }
            
            if all_success:
                logger.info("SQL and uploads restoration completed successfully")
                return self.complete_task(final_result)
            else:
                failed_services = [
                    r['service'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed services: {', '.join(failed_services)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in SQL and uploads task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})