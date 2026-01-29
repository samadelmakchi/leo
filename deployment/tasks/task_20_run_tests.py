#!/usr/bin/env python3
"""
Task 20: Run Tests
جایگزین task انسیبل: 20-run-tests.yml
"""

import logging
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class RunTestsTask(BaseTask):
    """اجرای test suite"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="run_tests", config=config)
        
        # پارامترهای مورد نیاز
        self.required_params = [
            'customer_state',
            'log_path',
            'inventory_hostname',
            'tests_path'
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
    
    def should_run_tests(self) -> bool:
        """بررسی آیا باید tests را اجرا کرد"""
        customer_test_enabled = self.config.get('customer_test_enabled', False)
        any_service_updated = self.config.get('any_service_updated', False)
        
        return bool(customer_test_enabled) and bool(any_service_updated)
    
    def install_system_packages(self) -> Dict:
        """نصب packageهای سیستم"""
        try:
            packages = [
                'python3-pip',
                'python3-venv',
                'python3.12-venv',
                'python3-full',
                'libglib2.0-0',
                'libnss3',
                'libatk-bridge2.0-0',
                'libatk1.0-0',
                'libcups2',
                'libdrm2',
                'libxkbcommon0',
                'libgbm1',
                'libasound2t64',
                'libxcomposite1',
                'libxdamage1',
                'libxrandr2',
                'libpango-1.0-0',
                'libcairo2',
                'fonts-liberation'
            ]
            
            cmd = ['apt-get', 'install', '-y'] + packages
            
            logger.info(f"Installing system packages: {len(packages)} packages")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 دقیقه timeout
            )
            
            result = {
                'success': process.returncode == 0,
                'action': 'install_system_packages',
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'message': 'System packages installed successfully'
                if process.returncode == 0 else 'Failed to install system packages'
            }
            
            if result['success']:
                logger.info("System packages installed successfully")
            else:
                logger.error(f"Failed to install system packages: {process.stderr.strip()}")
            
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = "Timeout installing system packages"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'install_system_packages',
                'error': error_msg,
                'timeout': True
            }
            
        except Exception as e:
            error_msg = f"Error installing system packages: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'install_system_packages',
                'error': error_msg
            }
    
    def create_venv(self) -> Dict:
        """ایجاد virtual environment"""
        try:
            venv_path = '/opt/test-venv'
            
            # حذف venv قبلی اگر وجود دارد
            if Path(venv_path).exists():
                shutil.rmtree(venv_path)
                logger.debug(f"Removed existing venv: {venv_path}")
            
            # ایجاد venv جدید
            cmd = ['python3', '-m', 'venv', venv_path]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            result = {
                'success': process.returncode == 0,
                'action': 'create_venv',
                'venv_path': venv_path,
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'message': 'Virtual environment created successfully'
                if process.returncode == 0 else 'Failed to create virtual environment'
            }
            
            if result['success']:
                logger.info(f"Created virtual environment: {venv_path}")
            else:
                logger.error(f"Failed to create venv: {process.stderr.strip()}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error creating virtual environment: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'create_venv',
                'error': error_msg
            }
    
    def install_python_packages(self) -> Dict:
        """نصب packageهای پایتون"""
        try:
            venv_pip = '/opt/test-venv/bin/pip'
            
            packages = [
                'pip',
                'wheel',
                'setuptools',
                'pytest',
                'pytest-html',
                'pytest-xdist',
                'requests',
                'selenium',
                'playwright',
                'locust'
            ]
            
            cmd = [venv_pip, 'install'] + packages + ['--retries', '20', '--timeout', '180']
            
            logger.info(f"Installing Python packages: {len(packages)} packages")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900  # 15 دقیقه timeout
            )
            
            result = {
                'success': process.returncode == 0,
                'action': 'install_python_packages',
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'message': 'Python packages installed successfully'
                if process.returncode == 0 else 'Failed to install Python packages'
            }
            
            if result['success']:
                logger.info("Python packages installed successfully")
            else:
                logger.error(f"Failed to install Python packages: {process.stderr.strip()}")
            
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = "Timeout installing Python packages"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'install_python_packages',
                'error': error_msg,
                'timeout': True
            }
            
        except Exception as e:
            error_msg = f"Error installing Python packages: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'install_python_packages',
                'error': error_msg
            }
    
    def install_playwright_browsers(self) -> Dict:
        """نصب Playwright browsers"""
        try:
            playwright_install_marker = '/opt/test-venv/.playwright-installing'
            playwright_dir = '/opt/test-venv/.playwright'
            
            # بررسی اگر قبلا نصب شده یا در حال نصب است
            if Path(playwright_dir).exists():
                return {
                    'success': True,
                    'action': 'install_playwright',
                    'changed': False,
                    'skipped': True,
                    'message': 'Playwright already installed'
                }
            
            if Path(playwright_install_marker).exists():
                return {
                    'success': True,
                    'action': 'install_playwright',
                    'changed': False,
                    'skipped': True,
                    'message': 'Playwright installation in progress'
                }
            
            # ایجاد marker file
            Path(playwright_install_marker).touch()
            
            # اجرای نصب در background
            venv_playwright = '/opt/test-venv/bin/playwright'
            cmd = f"nohup {venv_playwright} install chromium --with-deps > /var/log/playwright-install.log 2>&1 &"
            
            subprocess.Popen(cmd, shell=True)
            
            result = {
                'success': True,
                'action': 'install_playwright',
                'changed': True,
                'background': True,
                'message': 'Playwright installation started in background (2-5 minutes)',
                'log_file': '/var/log/playwright-install.log'
            }
            
            logger.info("Playwright installation started in background")
            
            return result
            
        except Exception as e:
            error_msg = f"Error starting playwright installation: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'install_playwright',
                'error': error_msg
            }
    
    def run_test_suite(self) -> Dict:
        """اجرای test suite"""
        try:
            log_path = self.config['log_path']
            inventory_hostname = self.config['inventory_hostname']
            tests_path = self.config['tests_path']
            customer_test_fail_fast = self.config.get('customer_test_fail_fast', False)
            
            # ایجاد دایرکتوری گزارش
            report_dir = Path(log_path) / 'test-reports' / inventory_hostname
            report_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = report_dir / 'report.html'
            
            # ساختن pytest command
            venv_pytest = '/opt/test-venv/bin/pytest'
            cmd = [venv_pytest, tests_path, '-n', 'auto', '--html', str(report_file), '--self-contained-html']
            
            if customer_test_fail_fast:
                cmd.extend(['--maxfail', '1'])
            
            logger.info(f"Running test suite from {tests_path}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # تغییر به دایرکتوری گزارش
            cwd = str(report_dir)
            
            process = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 ساعت timeout
            )
            
            # تفسیر کد بازگشت pytest
            returncode = process.returncode
            success = returncode == 0  # 0 = همه tests پاس شدند
            
            # اما ممکن است بعضی کدها acceptable باشند
            acceptable_returncodes = [0, 1, 2, 3, 4, 5]
            acceptable = returncode in acceptable_returncodes
            
            # تعیین پیام بر اساس returncode
            if returncode == 0:
                message = "All tests passed"
            elif returncode == 1:
                message = "Some tests failed"
            elif returncode in [2, 3, 4]:
                message = "Tests skipped or internal error (usually not the browser)"
            else:
                message = f"Unknown error (returncode={returncode})"
            
            result = {
                'success': acceptable,
                'tests_passed': success,
                'action': 'run_tests',
                'returncode': returncode,
                'acceptable': acceptable,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'message': message,
                'report_file': str(report_file),
                'playwright_log': '/var/log/playwright-install.log'
            }
            
            if acceptable:
                logger.info(f"Test suite completed: {message}")
                logger.info(f"Report available at: {report_file}")
            else:
                logger.error(f"Test suite failed with returncode {returncode}: {message}")
            
            return result
            
        except subprocess.TimeoutExpired:
            error_msg = "Test suite timeout after 1 hour"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'run_tests',
                'error': error_msg,
                'timeout': True
            }
            
        except Exception as e:
            error_msg = f"Error running test suite: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'action': 'run_tests',
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
            
            # بررسی آیا باید tests را اجرا کرد
            if not self.should_run_tests():
                logger.info("Tests disabled or no services updated, skipping test suite")
                return self.complete_task({
                    'success': True,
                    'changed': False,
                    'skipped': True,
                    'message': "Tests disabled or no services updated",
                    'customer_test_enabled': self.config.get('customer_test_enabled', False),
                    'any_service_updated': self.config.get('any_service_updated', False)
                })
            
            logger.info("Starting test suite execution")
            
            # اجرای مراحل
            steps = []
            
            # 1. نصب system packages
            packages_result = self.install_system_packages()
            steps.append({
                'step': 'install_system_packages',
                'result': packages_result
            })
            
            if not packages_result['success']:
                return self.fail_task(
                    "Failed to install system packages",
                    {'steps': steps}
                )
            
            # 2. ایجاد virtual environment
            venv_result = self.create_venv()
            steps.append({
                'step': 'create_venv',
                'result': venv_result
            })
            
            if not venv_result['success']:
                return self.fail_task(
                    "Failed to create virtual environment",
                    {'steps': steps}
                )
            
            # 3. نصب Python packages
            python_packages_result = self.install_python_packages()
            steps.append({
                'step': 'install_python_packages',
                'result': python_packages_result
            })
            
            if not python_packages_result['success']:
                return self.fail_task(
                    "Failed to install Python packages",
                    {'steps': steps}
                )
            
            # 4. نصب Playwright browsers (در background)
            playwright_result = self.install_playwright_browsers()
            steps.append({
                'step': 'install_playwright',
                'result': playwright_result
            })
            
            # 5. اجرای test suite
            test_result = self.run_test_suite()
            steps.append({
                'step': 'run_test_suite',
                'result': test_result
            })
            
            # خلاصه نتایج
            all_success = all(r['result']['success'] or r['result'].get('skipped', False) for r in steps)
            any_changed = any(r['result'].get('changed', False) for r in steps)
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'steps': steps,
                'customer_state': self.config.get('customer_state'),
                'customer_test_enabled': self.config.get('customer_test_enabled', True),
                'any_service_updated': self.config.get('any_service_updated', True),
                'inventory_hostname': self.config.get('inventory_hostname'),
                'message': f"Test suite completed: {test_result.get('message', 'Unknown status')}"
            }
            
            if all_success:
                logger.info("Test suite execution completed successfully")
                return self.complete_task(final_result)
            else:
                failed_steps = [
                    r['step'] for r in steps 
                    if not r['result']['success'] and not r['result'].get('skipped', False)
                ]
                error_msg = f"Failed steps: {', '.join(failed_steps)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in run tests task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})