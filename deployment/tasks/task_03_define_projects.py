#!/usr/bin/env python3
"""
Task 03: Define Projects List
جایگزین task انسیبل: 03-define-projects.yml
"""

import logging
import sys
from typing import Dict, Any, List

from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class DefineProjectsTask(BaseTask):
    """تعریف لیست پروژه‌ها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="define_projects", config=config)
        
        # پروژه‌های پیش‌فرض
        self.default_projects = [
            {
                'name': 'gateway',
                'folder': 'gateway',
                'repo': 'git@github.com:nasserman/calibri.git',
                'branch_var': 'customer_gateway_git_branches',
                'tag_var': 'customer_gateway_git_tags',
                'update': '{{ customer_gateway_update }}',
                'force': True
            },
            {
                'name': 'portal',
                'folder': 'portal',
                'repo': 'git@github.com:nasserman/calibri-portal.git',
                'branch_var': 'customer_portal_git_branches',
                'tag_var': 'customer_portal_git_tags',
                'update': '{{ customer_portal_update }}',
                'force': True
            },
            {
                'name': 'portal-frontend',
                'folder': 'portal-frontend',
                'repo': 'git@github.com:nasserman/calibri-portal-frontend.git',
                'branch_var': 'customer_portal_frontend_git_branches',
                'tag_var': 'customer_portal_frontend_git_tags',
                'update': '{{ customer_portal_frontend_update }}',
                'force': True
            },
            {
                'name': 'lms',
                'folder': 'lms',
                'repo': 'git@github.com:nasserman/calibri-lms',
                'branch_var': 'customer_lms_git_branches',
                'tag_var': 'customer_lms_git_tags',
                'update': '{{ customer_lms_update }}',
                'force': True
            },
            {
                'name': 'file',
                'folder': 'file',
                'repo': 'git@github.com:nasserman/calibri-file-storage',
                'branch_var': 'customer_file_git_branches',
                'tag_var': 'customer_file_git_tags',
                'update': '{{ customer_file_update }}',
                'force': True
            }
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        errors = []
        warnings = []
        
        customer_state = self.config.get('customer_state')
        if customer_state and customer_state not in ['up', 'down']:
            errors.append(f"Invalid customer_state: {customer_state}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def resolve_project_variables(self, project: Dict, host_vars: Dict) -> Dict:
        """
        حل کردن متغیرهای پروژه از host_vars
        
        Args:
            project: دیکشنری پروژه
            host_vars: متغیرهای host
            
        Returns:
            پروژه با متغیرهای حل شده
        """
        resolved_project = project.copy()
        
        # حل کردن update flag
        update_var = project.get('update', '')
        if update_var and '{{' in update_var:
            # استخراج نام متغیر
            var_name = update_var.replace('{{ ', '').replace(' }}', '').strip()
            resolved_project['update'] = host_vars.get(var_name, False)
        else:
            resolved_project['update'] = bool(update_var) if update_var else False
        
        # حل کردن branch و tag
        branch_var = project.get('branch_var')
        tag_var = project.get('tag_var')
        
        if branch_var and branch_var in host_vars:
            resolved_project['branch'] = host_vars.get(branch_var)
        
        if tag_var and tag_var in host_vars:
            resolved_project['tag'] = host_vars.get(tag_var)
        
        # تعیین نسخه (version)
        version = 'main'  # پیش‌فرض
        if resolved_project.get('tag'):
            version = resolved_project['tag']
        elif resolved_project.get('branch'):
            version = resolved_project['branch']
        
        resolved_project['version'] = version
        
        return resolved_project
    
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
            customer_state = self.config.get('customer_state')
            if customer_state != 'up':
                logger.info(f"Customer state is '{customer_state}', skipping project definition")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': f"Customer state is '{customer_state}'",
                    'projects': []
                })
            
            # دریافت host_vars از config
            host_vars = self.config.get('host_vars', {})
            
            # حل کردن متغیرهای هر پروژه
            resolved_projects = []
            for project in self.default_projects:
                resolved = self.resolve_project_variables(project, host_vars)
                resolved_projects.append(resolved)
                
                logger.debug(f"Resolved project {project['name']}: update={resolved['update']}, version={resolved['version']}")
            
            # ذخیره projects در config برای استفاده taskهای بعدی
            self.config['projects'] = resolved_projects
            
            result = {
                'success': True,
                'changed': True,  # همیشه changed است چون لیست پروژه‌ها را تنظیم می‌کند
                'projects_count': len(resolved_projects),
                'projects': resolved_projects,
                'customer_state': customer_state
            }
            
            logger.info(f"Defined {len(resolved_projects)} projects")
            return self.complete_task(result)
            
        except Exception as e:
            error_msg = f"Error defining projects: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})


# تابع helper برای استفاده در taskهای دیگر
def get_projects_list(config: Dict) -> List[Dict]:
    """
    دریافت لیست پروژه‌ها از config یا ایجاد default
    
    Args:
        config: دیکشنری config
        
    Returns:
        لیست پروژه‌ها
    """
    if 'projects' in config:
        return config['projects']
    
    # اگر projects وجود ندارد، task را اجرا کن
    task = DefineProjectsTask(config)
    result = task.execute()
    
    if result['success']:
        return result['projects']
    else:
        logger.warning(f"Failed to get projects list: {result.get('error')}")
        return []


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Define Projects Task")
    parser.add_argument('--customer-state', default='up',
                       choices=['up', 'down'],
                       help='Customer state')
    parser.add_argument('--host-vars', type=json.loads,
                       default='{}',
                       help='Host variables as JSON string')
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
        'host_vars': args.host_vars
    }
    
    task = DefineProjectsTask(config)
    result = task.execute()
    
    # نمایش نتیجه
    print(json.dumps(result, indent=2, default=str))
    
    # خروجی مناسب
    sys.exit(0 if result.get('success') else 1)