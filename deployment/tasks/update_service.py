#!/usr/bin/env python3
"""
Update Service Module
جایگزین task انسیبل: update_service.yml
"""

import logging
import sys
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import git
import stat

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.file_manager import FileManager
from deployment.core.template_renderer import TemplateRenderer
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class UpdateServiceTask(BaseTask):
    """به‌روزرسانی یک سرویس (git clone/pull + deploy compose)"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="update_service", config=config)
        
        self.file_mgr = FileManager()
        self.template_renderer = TemplateRenderer()
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'project',
            'project_path',
            'inventory_hostname',
            'customer_containers'
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        errors = []
        warnings = []
        
        for param in self.required_params:
            if param not in self.config:
                errors.append(f"Missing required parameter: {param}")
        
        # بررسی project dict
        project = self.config.get('project', {})
        required_project_keys = ['name', 'folder', 'repo']
        for key in required_project_keys:
            if key not in project:
                errors.append(f"Missing project.{key}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def check_git_repo(self, repo_path: str) -> Tuple[bool, Optional[git.Repo]]:
        """
        بررسی وجود repository git معتبر
        
        Args:
            repo_path: مسیر repository
            
        Returns:
            Tuple[bool, Optional[git.Repo]]: (is_valid, repo_object)
        """
        try:
            git_dir = Path(repo_path) / '.git'
            if not git_dir.exists() or not git_dir.is_dir():
                return False, None
            
            repo = git.Repo(repo_path)
            return True, repo
            
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False, None
        except Exception as e:
            logger.error(f"Error checking git repo {repo_path}: {str(e)}")
            return False, None
    
    def remove_broken_repo(self, repo_path: str) -> bool:
        """
        حذف repository خراب یا ناقص
        """
        try:
            if os.path.exists(repo_path):
                logger.warning(f"Removing broken/incomplete repo: {repo_path}")
                
                # حذف فایل‌های read-only
                def remove_readonly(func, path, excinfo):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                shutil.rmtree(repo_path, onerror=remove_readonly)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing repo {repo_path}: {str(e)}")
            return False
    
    def ensure_parent_directory(self, dir_path: str) -> bool:
        """
        اطمینان از وجود دایرکتوری والد
        """
        try:
            parent_dir = Path(dir_path).parent
            result = self.file_mgr.create_directory(
                str(parent_dir),
                mode=0o755
            )
            return result['success']
            
        except Exception as e:
            logger.error(f"Error creating parent directory {dir_path}: {str(e)}")
            return False
    
    def clone_or_update_repo(self, project: Dict, host_vars: Dict) -> Dict:
        """
        Clone یا update کردن repository
        
        Args:
            project: اطلاعات پروژه
            host_vars: متغیرهای host
            
        Returns:
            نتیجه عملیات git
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            repo_dir = Path(project_path) / inventory_hostname / project['folder']
            repo_url = project['repo']
            ssh_key_path = self.config.get('ssh_key_path', 'deployment/resources/ssh/id_rsa')
            
            # تعیین نسخه (tag > branch > main)
            version = 'main'  # پیش‌فرض
            tag_var = project.get('tag_var')
            branch_var = project.get('branch_var')
            
            if tag_var and tag_var in host_vars and host_vars[tag_var]:
                version = host_vars[tag_var]
            elif branch_var and branch_var in host_vars and host_vars[branch_var]:
                version = host_vars[branch_var]
            
            logger.info(f"Updating {project['name']} to version: {version}")
            
            # بررسی وجود repository
            is_valid, existing_repo = self.check_git_repo(str(repo_dir))
            
            if not is_valid:
                # حذف repository خراب
                self.remove_broken_repo(str(repo_dir))
                
                # ایجاد دایرکتوری والد
                if not self.ensure_parent_directory(str(repo_dir)):
                    return {
                        'success': False,
                        'error': f"Failed to create parent directory for {project['name']}"
                    }
                
                # Clone جدید
                logger.info(f"Cloning {project['name']} from {repo_url}")
                
                # تنظیم GIT_SSH_COMMAND برای استفاده از key خاص
                env = os.environ.copy()
                if os.path.exists(ssh_key_path):
                    env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
                
                # Clone repository
                try:
                    repo = git.Repo.clone_from(
                        repo_url,
                        str(repo_dir),
                        branch=version if version != 'main' else None,
                        env=env
                    )
                    
                    # اگر branch خاصی خواسته شده و main نیست
                    if version != 'main':
                        try:
                            repo.git.checkout(version)
                        except:
                            # اگر branch موجود نبود، tag را امتحان کن
                            try:
                                repo.git.checkout(f'tags/{version}')
                            except:
                                logger.warning(f"Version {version} not found, using default branch")
                    
                    git_result = {
                        'success': True,
                        'changed': True,
                        'action': 'cloned',
                        'before': None,
                        'after': repo.head.commit.hexsha[:7],
                        'version': version,
                        'message': f"Cloned {project['name']} at {version}"
                    }
                    
                except Exception as e:
                    error_msg = f"Failed to clone {project['name']}: {str(e)}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }
                    
            else:
                # Update repository موجود
                repo = existing_repo
                
                # ذخیره commit فعلی
                before_commit = repo.head.commit.hexsha[:7]
                
                try:
                    # Fetch تغییرات
                    origin = repo.remote('origin')
                    origin.fetch()
                    
                    # Checkout به version مورد نظر
                    current_branch = repo.active_branch.name if not repo.head.is_detached else 'detached'
                    
                    try:
                        # سعی کن به version مورد نظر checkout کن
                        repo.git.checkout(version)
                        after_commit = repo.head.commit.hexsha[:7]
                        
                        # اگر commit تغییر کرد
                        changed = before_commit != after_commit
                        
                        git_result = {
                            'success': True,
                            'changed': changed,
                            'action': 'updated' if changed else 'already_up_to_date',
                            'before': before_commit,
                            'after': after_commit,
                            'version': version,
                            'message': f"Updated {project['name']} from {before_commit} to {after_commit} at {version}"
                            if changed else f"{project['name']} already at {version} ({after_commit})"
                        }
                        
                    except Exception as e:
                        logger.warning(f"Cannot checkout to {version}: {str(e)}, pulling current branch")
                        
                        # Pull روی branch فعلی
                        origin.pull()
                        after_commit = repo.head.commit.hexsha[:7]
                        changed = before_commit != after_commit
                        
                        git_result = {
                            'success': True,
                            'changed': changed,
                            'action': 'pulled' if changed else 'already_up_to_date',
                            'before': before_commit,
                            'after': after_commit,
                            'version': current_branch,
                            'message': f"Pulled {project['name']} on {current_branch} from {before_commit} to {after_commit}"
                            if changed else f"{project['name']} already up to date on {current_branch} ({after_commit})"
                        }
                        
                except Exception as e:
                    error_msg = f"Failed to update {project['name']}: {str(e)}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }
            
            logger.info(f"Git operation for {project['name']}: {git_result['message']}")
            return git_result
            
        except Exception as e:
            error_msg = f"Error in clone_or_update_repo for {project.get('name', 'unknown')}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def ensure_docker_directory(self, project: Dict) -> Dict:
        """
        اطمینان از وجود دایرکتوری docker
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            docker_dir = Path(project_path) / inventory_hostname / project['folder'] / 'docker'
            
            result = self.file_mgr.create_directory(
                str(docker_dir),
                mode=0o755
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error ensuring docker directory for {project['name']}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def ensure_gateway_init_directory(self, project: Dict) -> Dict:
        """
        اطمینان از وجود دایرکتوری docker/init برای gateway
        """
        try:
            if project['name'] != 'gateway':
                return {
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': f"Not a gateway project: {project['name']}"
                }
            
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            
            init_dir = Path(project_path) / inventory_hostname / project['folder'] / 'docker' / 'init'
            
            result = self.file_mgr.create_directory(
                str(init_dir),
                mode=0o755
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error ensuring gateway init directory: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def deploy_compose_template(self, project: Dict) -> Dict:
        """
        deploy کردن docker-compose.yml از template
        """
        try:
            project_path = self.config['project_path']
            inventory_hostname = self.config['inventory_hostname']
            customer_containers = self.config['customer_containers']
            
            # تعیین template file
            if project['folder'] == 'portal-frontend':
                template_name = 'compose-portal-frontend.yml.j2'
            else:
                template_name = f"compose-{project['folder']}.yml.j2"
            
            template_path = Path('deployment/templates') / template_name
            dest_path = Path(project_path) / inventory_hostname / project['folder'] / 'docker' / 'docker-compose.yml'
            
            # context برای template
            context = {
                'inventory_hostname': inventory_hostname,
                'customer_containers': customer_containers,
                **self.config.get('host_vars', {})
            }
            
            # رندر template
            result = self.template_renderer.render_template(
                str(template_path),
                str(dest_path),
                context,
                mode=0o644,
                backup=True,
                force=True
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error deploying compose template for {project['name']}: {str(e)}"
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
            
            project = self.config['project']
            host_vars = self.config.get('host_vars', {})
            
            # بررسی update flag
            update = project.get('update', False)
            if not update:
                logger.info(f"Skipping {project['name']} - update flag is false")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'project': project['name'],
                    'message': f"Update flag is false for {project['name']}"
                })
            
            # اجرای مراحل
            steps = []
            
            # 1. Clone/Update git repo
            git_result = self.clone_or_update_repo(project, host_vars)
            steps.append({
                'step': 'git_operation',
                'result': git_result
            })
            
            if not git_result['success']:
                return self.fail_task(
                    f"Git operation failed for {project['name']}: {git_result.get('error')}",
                    {'steps': steps}
                )
            
            # 2. Ensure docker directory
            docker_dir_result = self.ensure_docker_directory(project)
            steps.append({
                'step': 'ensure_docker_directory',
                'result': docker_dir_result
            })
            
            # 3. Ensure gateway init directory (فقط برای gateway)
            if project['name'] == 'gateway':
                init_dir_result = self.ensure_gateway_init_directory(project)
                steps.append({
                    'step': 'ensure_gateway_init_directory',
                    'result': init_dir_result
                })
            
            # 4. Deploy compose template
            compose_result = self.deploy_compose_template(project)
            steps.append({
                'step': 'deploy_compose_template',
                'result': compose_result
            })
            
            # خلاصه نتایج
            all_success = all(r['result']['success'] for r in steps)
            any_changed = any(r['result'].get('changed', False) for r in steps)
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'git_changed': git_result.get('changed', False),
                'project': project['name'],
                'git_result': git_result,
                'steps': steps,
                'message': f"Updated service {project['name']} successfully"
                if all_success else f"Failed to update service {project['name']}"
            }
            
            if all_success:
                logger.info(f"Successfully updated service: {project['name']}")
                return self.complete_task(final_result)
            else:
                failed_steps = [r['step'] for r in steps if not r['result']['success']]
                error_msg = f"Failed steps for {project['name']}: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in update service task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})


# تابع helper برای استفاده مستقیم
def update_single_service(
    project: Dict,
    project_path: str,
    inventory_hostname: str,
    customer_containers: str,
    host_vars: Dict = None,
    ssh_key_path: str = None
) -> Dict:
    """
    به‌روزرسانی یک سرویس
    
    Args:
        project: اطلاعات پروژه
        project_path: مسیر پروژه
        inventory_hostname: نام host
        customer_containers: نام containerها
        host_vars: متغیرهای host
        ssh_key_path: مسیر SSH key
        
    Returns:
        نتیجه اجرا
    """
    config = {
        'project': project,
        'project_path': project_path,
        'inventory_hostname': inventory_hostname,
        'customer_containers': customer_containers,
        'host_vars': host_vars or {},
        'ssh_key_path': ssh_key_path or 'deployment/resources/ssh/id_rsa'
    }
    
    task = UpdateServiceTask(config)
    return task.execute()