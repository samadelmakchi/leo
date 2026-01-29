#!/usr/bin/env python3
"""
Task 11: Build Customer Images
جایگزین task انسیبل: 11-build-customer-images.yml
"""

import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.task_base import BaseTask
from deployment.tasks.task_03_define_projects import get_projects_list

logger = logging.getLogger(__name__)


class BuildCustomerImagesTask(BaseTask):
    """Build کردن imageهای customer-specific"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="build_customer_images", config=config)
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'project_path',
            'inventory_hostname'
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
    
    def build_project_image(self, project: Dict) -> Dict:
        """
        Build کردن image برای یک پروژه
        
        Args:
            project: اطلاعات پروژه
            
        Returns:
            نتیجه عملیات build
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            force_rebuild = self.config.get('force_rebuild', False)
            
            # مسیر docker-compose
            compose_dir = Path(project_path) / inventory_hostname / project['folder'] / 'docker'
            
            if not compose_dir.exists():
                return {
                    'success': False,
                    'error': f"Docker directory not found: {compose_dir}",
                    'project': project['name']
                }
            
            # ساختن docker compose command
            cmd = ['docker', 'compose', '-f', 'docker-compose.yml', 'build', '--pull']
            
            if force_rebuild:
                cmd.append('--no-cache')
            
            logger.info(f"Building image for {project['name']} in {compose_dir}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # اجرای command
            process = subprocess.Popen(
                cmd,
                cwd=str(compose_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # خواندن خروجی real-time
            while True:
                stdout_line = process.stdout.readline()
                stderr_line = process.stderr.readline()
                
                if stdout_line:
                    stdout_lines.append(stdout_line.strip())
                    logger.debug(f"[{project['name']} stdout] {stdout_line.strip()}")
                
                if stderr_line:
                    stderr_lines.append(stderr_line.strip())
                    logger.debug(f"[{project['name']} stderr] {stderr_line.strip()}")
                
                # بررسی پایان process
                if stdout_line == '' and stderr_line == '' and process.poll() is not None:
                    break
            
            # جمع‌آوری باقی مانده output
            remaining_stdout, remaining_stderr = process.communicate()
            if remaining_stdout:
                stdout_lines.extend(remaining_stdout.strip().split('\n'))
            if remaining_stderr:
                stderr_lines.extend(remaining_stderr.strip().split('\n'))
            
            returncode = process.returncode
            
            # بررسی اگر build انجام شده یا نه
            stdout_text = '\n'.join(stdout_lines)
            stderr_text = '\n'.join(stderr_lines)
            
            changed = False
            if returncode == 0:
                # بررسی اگر در خروجی کلمه "Building" یا "Built" وجود دارد
                if 'Building' in stdout_text or 'Built' in stdout_text:
                    changed = True
                    message = f"Image built successfully for {project['name']}"
                else:
                    message = f"Image already built for {project['name']}"
            else:
                message = f"Build failed for {project['name']}"
            
            result = {
                'success': returncode == 0,
                'changed': changed,
                'project': project['name'],
                'returncode': returncode,
                'message': message,
                'stdout': stdout_text,
                'stderr': stderr_text
            }
            
            if result['success']:
                if changed:
                    logger.info(f"Successfully built image for {project['name']}")
                else:
                    logger.debug(f"Image already built for {project['name']}")
            else:
                logger.error(f"Failed to build image for {project['name']}: {stderr_text}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error building image for {project.get('name', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'project': project.get('name', 'unknown'),
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
            
            # دریافت لیست پروژه‌ها
            projects = get_projects_list(self.config)
            
            if not projects:
                logger.warning("No projects found to build images for")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "No projects found"
                })
            
            logger.info(f"Building images for {len(projects)} projects")
            
            # Build image برای هر پروژه
            results = []
            built_count = 0
            failed_count = 0
            
            for project in projects:
                logger.info(f"Building image for project: {project['name']}")
                result = self.build_project_image(project)
                results.append({
                    'project': project['name'],
                    'result': result
                })
                
                if result['success']:
                    if result.get('changed', False):
                        built_count += 1
                else:
                    failed_count += 1
            
            # خلاصه نتایج
            all_success = failed_count == 0
            any_changed = built_count > 0
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'total_projects': len(projects),
                'built': built_count,
                'failed': failed_count,
                'force_rebuild': self.config.get('force_rebuild', False),
                'results': results,
                'message': f"Built {built_count} images, {failed_count} failed"
            }
            
            if all_success:
                logger.info(f"Customer images build completed: {final_result['message']}")
                return self.complete_task(final_result)
            else:
                failed_projects = [
                    r['project'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed to build images for projects: {', '.join(failed_projects)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in build customer images task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})