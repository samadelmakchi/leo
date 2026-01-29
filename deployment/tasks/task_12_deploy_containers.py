#!/usr/bin/env python3
"""
Task 12: Deploy Containers
جایگزین task انسیبل: 12-deploy-containers.yml
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.docker_manager import DockerManager
from deployment.core.task_base import BaseTask
from deployment.tasks.task_03_define_projects import get_projects_list

logger = logging.getLogger(__name__)


class DeployContainersTask(BaseTask):
    """Deploy کردن containerها"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="deploy_containers", config=config)
        
        self.docker_mgr = DockerManager()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'project_path',
            'inventory_hostname',
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
    
    def deploy_project_containers(self, project: Dict) -> Dict:
        """
        Deploy کردن containerهای یک پروژه
        
        Args:
            project: اطلاعات پروژه
            
        Returns:
            نتیجه عملیات deploy
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            customer_containers = self.config['customer_containers']
            
            # نام پروژه Docker Compose
            project_name = f"{customer_containers}-{project['name']}"
            
            # مسیر docker-compose
            compose_dir = Path(project_path) / inventory_hostname / project['folder'] / 'docker'
            compose_file = compose_dir / 'docker-compose.yml'
            
            if not compose_file.exists():
                return {
                    'success': False,
                    'error': f"Docker compose file not found: {compose_file}",
                    'project': project['name']
                }
            
            logger.info(f"Deploying containers for {project['name']} (project: {project_name})")
            
            # استفاده از docker compose v2 via CLI
            # ما می‌توانیم از docker-py استفاده کنیم، اما برای compatibility با Ansible
            # از CLI استفاده می‌کنیم
            
            import subprocess
            import yaml
            
            # خواندن فایل compose برای بررسی
            with open(compose_file, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            # اجرای docker compose up
            cmd = [
                'docker', 'compose',
                '-p', project_name,
                '-f', str(compose_file),
                'up', '-d',
                '--remove-orphans',
                '--force-recreate',
                '--pull', 'always'
            ]
            
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                cwd=str(compose_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 دقیقه timeout
            )
            
            if process.returncode == 0:
                # بررسی containerهای ایجاد شده
                containers = self.docker_mgr.list_containers(
                    filters={'label': [f'com.docker.compose.project={project_name}']}
                )
                
                result = {
                    'success': True,
                    'changed': True,
                    'project': project['name'],
                    'project_name': project_name,
                    'containers_count': len(containers),
                    'containers': [c.name for c in containers],
                    'stdout': process.stdout.strip(),
                    'message': f"Successfully deployed {len(containers)} containers for {project['name']}"
                }
                
                logger.info(f"Deployed {len(containers)} containers for {project['name']}")
                return result
            else:
                error_msg = f"Failed to deploy containers for {project['name']}: {process.stderr.strip()}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'project': project['name'],
                    'error': error_msg,
                    'stderr': process.stderr.strip(),
                    'returncode': process.returncode
                }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout deploying containers for {project['name']}"
            logger.error(error_msg)
            return {
                'success': False,
                'project': project['name'],
                'error': error_msg,
                'timeout': True
            }
            
        except Exception as e:
            error_msg = f"Error deploying containers for {project.get('name', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'project': project.get('name', 'unknown'),
                'error': error_msg
            }
    
    def retry_deploy(self, project: Dict, max_retries: int = 3, delay: int = 10) -> Dict:
        """
        تلاش مجدد برای deploy با retry
        
        Args:
            project: اطلاعات پروژه
            max_retries: حداکثر تعداد تلاش‌ها
            delay: تاخیر بین تلاش‌ها (ثانیه)
            
        Returns:
            نتیجه نهایی
        """
        for attempt in range(1, max_retries + 1):
            logger.info(f"Deploy attempt {attempt}/{max_retries} for {project['name']}")
            
            result = self.deploy_project_containers(project)
            
            if result['success']:
                result['attempts'] = attempt
                return result
            
            if attempt < max_retries:
                logger.warning(f"Deploy failed for {project['name']}, retrying in {delay} seconds...")
                time.sleep(delay)
        
        # اگر بعد از همه retryها موفق نشد
        result['attempts'] = max_retries
        result['max_retries_reached'] = True
        return result
    
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
                logger.info("Customer state is not 'up', skipping container deployment")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Customer state is not 'up'"
                })
            
            # دریافت لیست پروژه‌ها
            projects = get_projects_list(self.config)
            
            if not projects:
                logger.warning("No projects found to deploy")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "No projects found"
                })
            
            logger.info(f"Deploying containers for {len(projects)} projects")
            
            # Deploy containerهای هر پروژه
            results = []
            deployed_count = 0
            failed_count = 0
            
            for project in projects:
                logger.info(f"Deploying project: {project['name']}")
                
                # اجرای deploy با retry
                result = self.retry_deploy(
                    project,
                    max_retries=self.config.get('max_retries', 3),
                    delay=self.config.get('retry_delay', 10)
                )
                
                results.append({
                    'project': project['name'],
                    'result': result
                })
                
                if result['success']:
                    deployed_count += 1
                else:
                    failed_count += 1
            
            # خلاصه نتایج
            all_success = failed_count == 0
            any_changed = deployed_count > 0
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'total_projects': len(projects),
                'deployed': deployed_count,
                'failed': failed_count,
                'customer_state': self.config.get('customer_state'),
                'customer_containers': self.config.get('customer_containers'),
                'results': results,
                'message': f"Deployed {deployed_count} projects, {failed_count} failed"
            }
            
            if all_success:
                logger.info(f"Container deployment completed: {final_result['message']}")
                return self.complete_task(final_result)
            else:
                failed_projects = [
                    r['project'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed to deploy containers for projects: {', '.join(failed_projects)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in deploy containers task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})