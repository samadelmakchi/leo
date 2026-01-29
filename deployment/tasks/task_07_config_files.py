#!/usr/bin/env python3
"""
Task 07: Deploy Config Files
جایگزین task انسیبل: 07-config-files.yml
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.template_renderer import TemplateRenderer
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class ConfigFilesTask(BaseTask):
    """Deploy کردن فایل‌های کانفیگ"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="config_files", config=config)
        
        self.file_mgr = FileManager()
        self.template_renderer = TemplateRenderer()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'project_path',
            'inventory_hostname'
        ]
        
        # تعریف فایل‌های کانفیگ
        self.config_files = [
            {
                'dest': 'portal-frontend/baseUrl.js',
                'content': """const baseUrl = 'https://{{ customer_subdomain_backendportal }}.{{ customer_domain }}';
export default baseUrl;""",
                'when_var': 'customer_portal_frontend_update',
                'mode': '0644'
            },
            {
                'dest': 'portal/.env.local',
                'content': """DATABASE_URL="mysql://{{ portal_mysql_user }}:{{ portal_mysql_password }}@{{ inventory_hostname }}-portal-db:3306/{{ portal_mysql_db_name }}?serverVersion=10.11.2-MariaDB&charset=utf8mb4"
BASE_URL="https://{{ customer_subdomain_gateway }}.{{ customer_domain }}""",
                'when_var': 'customer_portal_update',
                'mode': '0644'
            },
            {
                'dest': 'gateway/admin/application/config/my_database.php',
                'content': """<?php defined('BASEPATH') OR exit('No direct script access allowed');
$active_group = 'default'; $query_builder = TRUE;
$db['default'] = array(
  'dsn'       => '',
  'hostname'  => '{{ inventory_hostname }}-gateway-db',
  'username'  => '{{ gateway_mysql_user }}',
  'password'  => '{{ gateway_mysql_password }}',
  'database'  => '{{ gateway_mysql_db_name }}',
  'dbdriver'  => 'mysqli',
  'dbprefix'  => '',
  'pconnect'  => FALSE,
  'db_debug'  => (ENVIRONMENT !== 'production'),
  'cache_on'  => FALSE,
  'cachedir'  => '',
  'char_set'  => 'utf8',
  'dbcollat'  => 'utf8_general_ci',
  'swap_pre'  => '',
  'encrypt'   => FALSE,
  'compress'  => FALSE,
  'stricton'  => FALSE,
  'failover'  => array(),
  'save_queries' => TRUE
);""",
                'when_var': 'customer_gateway_update',
                'mode': '0644'
            },
            {
                'dest': 'gateway/admin/application/config/my_config.php',
                'content': """<?php defined('BASEPATH') OR exit('No direct script access allowed');
$config['base_url'] = "https://{{ customer_subdomain_gateway }}.{{ customer_domain }}/";""",
                'when_var': 'customer_gateway_update',
                'mode': '0644'
            },
            {
                'dest': 'gateway/docker/app.conf',
                'content': """<VirtualHost *:80>
    ServerName localhost
    DocumentRoot /var/www/html
    <Directory /var/www/html>
        AllowOverride All
        Require all granted
    </Directory>
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/socket\\.io/(.*) ws://{{ inventory_hostname }}-socketio-server:{{ customer_websocket_ports }}/socket.io/$1 [P,L]
    ProxyPass /socket.io http://{{ inventory_hostname }}-socketio-server:{{ customer_websocket_ports }}/socket.io
    ProxyPassReverse /socket.io http://{{ inventory_hostname }}-socketio-server:{{ customer_websocket_ports }}/socket.io
    ProxyPass /socketio-ping http://{{ inventory_hostname }}-socketio-server:{{ customer_websocket_ports }}/
    ProxyPassReverse /socketio-ping http://{{ inventory_hostname }}-socketio-server:{{ customer_websocket_ports }}/
</VirtualHost>""",
                'when_var': 'customer_gateway_update',
                'mode': '0644'
            },
            {
                'dest': 'gateway/admin/application/config/my_config.php',
                'content': """<?php
defined('BASEPATH') OR exit('No direct script access allowed');
$config['base_url'] = "http://localhost:{{ customer_gateway_ports }}";
$config['websocket_container_name'] = '{{ inventory_hostname }}-socketio-server';
$config['websocket_container_port'] = '{{ customer_websocket_ports }}';
$config['microservice_registery'] = [
    "lms" => "'{{ inventory_hostname }}-lms",
    "file" => "'{{ inventory_hostname }}-lms",
];""",
                'when_var': 'customer_gateway_update',
                'mode': '0644'
            },
            {
                'dest': 'lms/.env.local',
                'content': """DB_CONNECTION=mysql
DB_HOST={{ inventory_hostname }}-lms-database
DB_PORT=3306
DB_DATABASE={{ lms_mysql_db_name }}
DB_USERNAME={{ lms_mysql_user }}
DB_PASSWORD={{ lms_mysql_password }}""",
                'when_var': 'customer_lms_update',
                'mode': '0644'
            },
            {
                'dest': 'file/.env.local',
                'content': """DB_CONNECTION=mysql
DB_HOST={{ inventory_hostname }}-file-storage-database
DB_PORT=3306
DB_DATABASE={{ file_mysql_db_name }}
DB_USERNAME={{ file_mysql_user }}
DB_PASSWORD={{ file_mysql_password }}
CACHE_DRIVER=file
FILESYSTEM_DISK=private""",
                'when_var': 'customer_file_update',
                'mode': '0644'
            }
        ]
        
        # تعریف template files
        self.template_files = [
            {
                'src': 'nginx.conf.j2',
                'dest': 'portal-frontend/docker/nginx.conf',
                'when_var': 'customer_portal_frontend_update',
                'mode': '0777'
            },
            {
                'src': 'Dockerfile.j2',
                'dest': 'portal-frontend/docker/Dockerfile',
                'when_var': 'customer_portal_frontend_update',
                'mode': '0777'
            }
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
    
    def should_deploy_file(self, when_var: str) -> bool:
        """
        بررسی آیا فایل باید deploy شود یا نه
        
        Args:
            when_var: نام متغیر شرط
            
        Returns:
            bool: True اگر باید deploy شود
        """
        if not when_var:
            return True
        
        host_vars = self.config.get('host_vars', {})
        value = host_vars.get(when_var, False)
        
        # تبدیل به boolean
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', '1']
        return bool(value)
    
    def deploy_config_files(self) -> Dict:
        """
        Deploy کردن فایل‌های کانفیگ
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
            host_vars = self.config.get('host_vars', {})
            
            results = []
            deployed_count = 0
            
            for file_config in self.config_files:
                # بررسی شرط when
                if not self.should_deploy_file(file_config.get('when_var')):
                    continue
                
                # ساخت مسیر کامل
                dest_path = Path(project_path) / inventory_hostname / file_config['dest']
                
                # محتوای فایل با جایگزینی متغیرها
                content = file_config['content']
                
                # جایگزینی متغیرهای Jinja-style
                for key, value in host_vars.items():
                    placeholder = f'{{{{ {key} }}}}'
                    if placeholder in content:
                        content = content.replace(placeholder, str(value))
                
                # همچنین inventory_hostname را جایگزین کن
                content = content.replace('{{ inventory_hostname }}', inventory_hostname)
                
                # نوشتن فایل
                try:
                    result = self.file_mgr.write_file(
                        str(dest_path),
                        content,
                        mode=file_config['mode'],
                        force=True,
                        backup=True
                    )
                    
                    results.append({
                        'file': str(dest_path),
                        'result': result
                    })
                    
                    if result.get('changed'):
                        deployed_count += 1
                        logger.info(f"Deployed config file: {dest_path}")
                    else:
                        logger.debug(f"Config file already exists: {dest_path}")
                        
                except Exception as e:
                    logger.error(f"Error deploying config file {dest_path}: {str(e)}")
                    results.append({
                        'file': str(dest_path),
                        'error': str(e)
                    })
            
            # خلاصه نتایج
            success_count = sum(1 for r in results if 'result' in r and r['result']['success'])
            failed_count = len(results) - success_count
            
            final_result = {
                'success': failed_count == 0,
                'changed': deployed_count > 0,
                'files_processed': len(results),
                'files_deployed': deployed_count,
                'successful': success_count,
                'failed': failed_count,
                'results': results
            }
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error deploying config files: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def deploy_template_files(self) -> Dict:
        """
        Deploy کردن فایل‌های template
        """
        try:
            if self.config.get('customer_state') != 'up':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                }
            
            # بررسی شرط portal-frontend update
            if not self.should_deploy_file('customer_portal_frontend_update'):
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Portal-frontend update is disabled"
                }
            
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            host_vars = self.config.get('host_vars', {})
            
            results = []
            deployed_count = 0
            
            for template_config in self.template_files:
                # ساخت مسیرها
                src_path = Path('deployment/templates') / template_config['src']
                dest_path = Path(project_path) / inventory_hostname / template_config['dest']
                
                # context برای template
                context = {
                    'inventory_hostname': inventory_hostname,
                    **host_vars
                }
                
                # رندر template
                try:
                    result = self.template_renderer.render_template(
                        str(src_path),
                        str(dest_path),
                        context,
                        mode=template_config['mode'],
                        force=True
                    )
                    
                    results.append({
                        'template': template_config['src'],
                        'destination': str(dest_path),
                        'result': result
                    })
                    
                    if result.get('changed'):
                        deployed_count += 1
                        logger.info(f"Deployed template: {template_config['src']} -> {dest_path}")
                    else:
                        logger.debug(f"Template already deployed: {template_config['src']}")
                        
                except Exception as e:
                    logger.error(f"Error deploying template {template_config['src']}: {str(e)}")
                    results.append({
                        'template': template_config['src'],
                        'destination': str(dest_path),
                        'error': str(e)
                    })
            
            # خلاصه نتایج
            success_count = sum(1 for r in results if 'result' in r and r['result']['success'])
            failed_count = len(results) - success_count
            
            final_result = {
                'success': failed_count == 0,
                'changed': deployed_count > 0,
                'templates_processed': len(results),
                'templates_deployed': deployed_count,
                'successful': success_count,
                'failed': failed_count,
                'results': results
            }
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error deploying template files: {str(e)}"
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
            
            # اجرای مراحل
            results = []
            
            # 1. Deploy config files
            config_files_result = self.deploy_config_files()
            results.append({
                'step': 'deploy_config_files',
                'result': config_files_result
            })
            
            # 2. Deploy template files
            template_files_result = self.deploy_template_files()
            results.append({
                'step': 'deploy_template_files',
                'result': template_files_result
            })
            
            # خلاصه نتایج
            all_success = all(
                r['result']['success'] or r['result'].get('skipped', False)
                for r in results
            )
            any_changed = any(
                r['result'].get('changed', False) 
                for r in results
            )
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'steps': results,
                'customer_state': self.config.get('customer_state'),
                'project_path': self.config.get('project_path'),
                'inventory_hostname': self.config.get('inventory_hostname')
            }
            
            if all_success:
                logger.info("Config files deployment completed successfully")
                return self.complete_task(final_result)
            else:
                failed_steps = [
                    r['step'] for r in results 
                    if not r['result']['success'] and not r['result'].get('skipped', False)
                ]
                error_msg = f"Failed steps: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in config files task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})