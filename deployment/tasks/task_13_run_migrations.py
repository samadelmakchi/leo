#!/usr/bin/env python3
"""
Task 13: Run Migrations
جایگزین task انسیبل: 13-run-migrations.yml
"""

import logging
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.docker_manager import DockerManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class RunMigrationsTask(BaseTask):
    """اجرای migrations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="run_migrations", config=config)
        
        self.docker_mgr = DockerManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'customer_containers'
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
    
    def check_service_updated(self, service_name: str) -> bool:
        """
        بررسی آیا سرویس به‌روز شده است
        
        Args:
            service_name: نام سرویس
            
        Returns:
            True اگر به‌روز شده باشد
        """
        update_var = f'customer_{service_name}_update'
        return self.config.get(update_var, False)
    
    def ensure_containers_up(self, service_name: str) -> Dict:
        """
        اطمینان از بالا بودن containerهای سرویس
        """
        try:
            customer_containers = self.config['customer_containers']
            
            # فیلتر containerهای سرویس
            filters = {'name': f'{customer_containers}-{service_name}'}
            containers = self.docker_mgr.list_containers(filters=filters)
            
            if not containers:
                return {
                    'success': False,
                    'error': f"No containers found for {service_name}",
                    'service': service_name
                }
            
            # بررسی وضعیت containerها
            running_containers = [c for c in containers if c.status == 'running']
            
            if len(running_containers) < len(containers):
                logger.warning(f"Some containers for {service_name} are not running")
                # می‌توانیم containerها را start کنیم
                # اما فعلا فقط warning می‌دهیم
            
            result = {
                'success': True,
                'service': service_name,
                'total_containers': len(containers),
                'running_containers': len(running_containers),
                'container_names': [c.name for c in containers]
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Error checking containers for {service_name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'service': service_name,
                'error': error_msg
            }
    
    def run_container_command(self, container_name: str, command: str, timeout: int = 300) -> Dict:
        """
        اجرای یک command در container
        
        Args:
            container_name: نام container
            command: دستور برای اجرا
            timeout: timeout به ثانیه
            
        Returns:
            نتیجه اجرا
        """
        try:
            cmd = ['docker', 'exec', container_name, 'sh', '-c', command]
            
            logger.debug(f"Running command in container {container_name}: {command}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            result = {
                'success': process.returncode == 0,
                'container': container_name,
                'command': command,
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'message': f"Command executed in {container_name}"
            }
            
            if result['success']:
                logger.debug(f"Command succeeded in {container_name}")
            else:
                logger.warning(f"Command failed in {container_name}: {process.stderr.strip()}")
            
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timeout in container {container_name}"
            logger.error(error_msg)
            return {
                'success': False,
                'container': container_name,
                'command': command,
                'error': error_msg,
                'timeout': True
            }
            
        except Exception as e:
            error_msg = f"Error running command in container {container_name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'container': container_name,
                'command': command,
                'error': error_msg
            }
    
    def run_portal_migrations(self) -> Dict:
        """اجرای migrations برای Portal"""
        try:
            if not self.check_service_updated('portal'):
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'service': 'portal',
                    'message': 'Portal update not enabled'
                }
            
            # بررسی containerها
            container_check = self.ensure_containers_up('portal')
            if not container_check['success']:
                return container_check
            
            container_names = container_check['container_names']
            results = []
            
            # Composer install
            for container in container_names:
                result = self.run_container_command(
                    container,
                    'composer install --no-dev --optimize-autoloader --no-interaction',
                    timeout=300
                )
                results.append({
                    'step': 'composer_install',
                    'container': container,
                    'result': result
                })
            
            # Doctrine migrations
            for container in container_names:
                result = self.run_container_command(
                    container,
                    'php bin/console doctrine:migrations:migrate --no-interaction --env=prod',
                    timeout=300
                )
                results.append({
                    'step': 'doctrine_migrations',
                    'container': container,
                    'result': result
                })
            
            # خلاصه results
            success = all(r['result']['success'] for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'portal',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error running portal migrations: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'service': 'portal',
                'error': error_msg
            }
    
    def run_gateway_migrations(self) -> Dict:
        """اجرای migrations برای Gateway"""
        try:
            if not self.check_service_updated('gateway'):
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'service': 'gateway',
                    'message': 'Gateway update not enabled'
                }
            
            container_check = self.ensure_containers_up('gateway')
            if not container_check['success']:
                return container_check
            
            container_names = container_check['container_names']
            results = []
            
            # Gateway migration (CodeIgniter)
            for container in container_names:
                result = self.run_container_command(
                    container,
                    'php index.php migrate index false',
                    timeout=300
                )
                results.append({
                    'step': 'codeigniter_migration',
                    'container': container,
                    'result': result
                })
            
            success = all(r['result']['success'] for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'gateway',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error running gateway migrations: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'service': 'gateway',
                'error': error_msg
            }
    
    def run_lms_migrations(self) -> Dict:
        """اجرای migrations برای LMS"""
        try:
            if not self.check_service_updated('lms'):
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'service': 'lms',
                    'message': 'LMS update not enabled'
                }
            
            container_check = self.ensure_containers_up('lms')
            if not container_check['success']:
                return container_check
            
            container_names = container_check['container_names']
            results = []
            
            # Laravel migrations
            for container in container_names:
                # Composer install
                composer_result = self.run_container_command(
                    container,
                    'composer install --no-dev --optimize-autoloader --no-interaction',
                    timeout=300
                )
                results.append({
                    'step': 'composer_install',
                    'container': container,
                    'result': composer_result
                })
                
                if not composer_result['success']:
                    continue
                
                # Cache clear
                cache_commands = [
                    'php artisan config:clear',
                    'php artisan config:cache',
                    'php artisan route:cache',
                    'php artisan view:cache'
                ]
                
                for cache_cmd in cache_commands:
                    cache_result = self.run_container_command(
                        container,
                        cache_cmd,
                        timeout=60
                    )
                    results.append({
                        'step': f'cache_{cache_cmd.split()[2]}',
                        'container': container,
                        'result': cache_result
                    })
                
                # Migrate
                migrate_result = self.run_container_command(
                    container,
                    'php artisan migrate --force',
                    timeout=300
                )
                results.append({
                    'step': 'laravel_migrate',
                    'container': container,
                    'result': migrate_result
                })
            
            success = all(r['result']['success'] for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'lms',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error running LMS migrations: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'service': 'lms',
                'error': error_msg
            }
    
    def run_file_migrations(self) -> Dict:
        """اجرای migrations برای File Storage"""
        try:
            if not self.check_service_updated('file'):
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'service': 'file',
                    'message': 'File storage update not enabled'
                }
            
            container_check = self.ensure_containers_up('file')
            if not container_check['success']:
                return container_check
            
            container_names = container_check['container_names']
            results = []
            
            # Laravel migrations (مشابه LMS)
            for container in container_names:
                # Composer install
                composer_result = self.run_container_command(
                    container,
                    'composer install --no-dev --optimize-autoloader --no-interaction',
                    timeout=300
                )
                results.append({
                    'step': 'composer_install',
                    'container': container,
                    'result': composer_result
                })
                
                if not composer_result['success']:
                    continue
                
                # Cache clear
                cache_commands = [
                    'php artisan config:clear',
                    'php artisan config:cache',
                    'php artisan route:cache',
                    'php artisan view:cache'
                ]
                
                for cache_cmd in cache_commands:
                    cache_result = self.run_container_command(
                        container,
                        cache_cmd,
                        timeout=60
                    )
                    results.append({
                        'step': f'cache_{cache_cmd.split()[2]}',
                        'container': container,
                        'result': cache_result
                    })
                
                # Migrate
                migrate_result = self.run_container_command(
                    container,
                    'php artisan migrate --force',
                    timeout=300
                )
                results.append({
                    'step': 'laravel_migrate',
                    'container': container,
                    'result': migrate_result
                })
            
            success = all(r['result']['success'] for r in results)
            changed = any(r['result'].get('changed', False) for r in results)
            
            return {
                'success': success,
                'changed': changed,
                'service': 'file',
                'steps': results
            }
            
        except Exception as e:
            error_msg = f"Error running file storage migrations: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'service': 'file',
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
                logger.info("Customer state is not 'up', skipping migrations")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                })
            
            # بررسی any_service_updated
            any_service_updated = self.config.get('any_service_updated', False)
            if not any_service_updated:
                logger.info("No services were updated, skipping migrations")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "No services were updated"
                })
            
            logger.info("Running migrations for updated services")
            
            # اجرای migrations برای هر سرویس
            services = [
                ('portal', self.run_portal_migrations),
                ('gateway', self.run_gateway_migrations),
                ('lms', self.run_lms_migrations),
                ('file', self.run_file_migrations)
            ]
            
            results = []
            all_success = True
            any_changed = False
            
            for service_name, migration_func in services:
                logger.info(f"Running migrations for {service_name}...")
                result = migration_func()
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
                'any_service_updated': any_service_updated,
                'services': results,
                'customer_state': self.config.get('customer_state'),
                'message': f"Ran migrations for {len([r for r in results if not r['result'].get('skipped', False)])} services"
            }
            
            if all_success:
                logger.info("Migrations completed successfully")
                return self.complete_task(final_result)
            else:
                failed_services = [
                    r['service'] for r in results 
                    if not r['result']['success'] and not r['result'].get('skipped', False)
                ]
                error_msg = f"Failed migrations for services: {', '.join(failed_services)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in run migrations task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})