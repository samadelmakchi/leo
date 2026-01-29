#!/usr/bin/env python3
"""
Task 10: Pre-pull Docker Images
جایگزین task انسیبل: 10-pre-pull-images.yml
"""

import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from deployment.core.docker_manager import DockerManager
from deployment.core.task_base import BaseTask

logger = logging.getLogger(__name__)


class PrePullImagesTask(BaseTask):
    """Pre-pull کردن imageهای Docker"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(task_name="pre_pull_images", config=config)
        
        self.docker_mgr = DockerManager()
        
        # لیست imageهای global
        self.global_images = [
            'mariadb:10.11',
            'mariadb:10.6.20-focal',
            'nginx:alpine',
            'node:22',
            'php:8.1-apache-bookworm',
            'php:8.2-apache-bookworm'
        ]
    
    def validate_parameters(self) -> Dict:
        """اعتبارسنجی پارامترها"""
        return {
            'valid': True,
            'errors': [],
            'warnings': []
        }
    
    def pull_image(self, image_name: str) -> Dict:
        """
        Pull کردن یک image Docker
        
        Args:
            image_name: نام image
            
        Returns:
            نتیجه عملیات
        """
        try:
            logger.debug(f"Pulling Docker image: {image_name}")
            
            # استفاده از docker-py برای pull
            try:
                image = self.docker_mgr.client.images.pull(image_name)
                
                return {
                    'success': True,
                    'changed': True,
                    'image': image_name,
                    'image_id': image.id[:12] if image else None,
                    'message': f"Successfully pulled {image_name}"
                }
                
            except Exception as e:
                # اگر pull با docker-py شکست خورد، از command line استفاده کن
                logger.warning(f"Docker-py failed for {image_name}, trying command line: {str(e)}")
                
                cmd = ['docker', 'pull', image_name]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 دقیقه timeout
                )
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'changed': True,
                        'image': image_name,
                        'message': f"Successfully pulled {image_name} via CLI",
                        'stdout': result.stdout.strip()
                    }
                else:
                    # اگر image وجود نداشت، ignore کن
                    if "not found" in result.stderr.lower():
                        logger.warning(f"Image not found: {image_name}, ignoring")
                        return {
                            'success': True,
                            'changed': False,
                            'skipped': True,
                            'image': image_name,
                            'message': f"Image not found: {image_name}, ignoring"
                        }
                    else:
                        error_msg = f"Failed to pull {image_name}: {result.stderr.strip()}"
                        logger.error(error_msg)
                        return {
                            'success': False,
                            'image': image_name,
                            'error': error_msg,
                            'stderr': result.stderr.strip()
                        }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout pulling image {image_name}"
            logger.error(error_msg)
            return {
                'success': False,
                'image': image_name,
                'error': error_msg,
                'timeout': True
            }
            
        except Exception as e:
            error_msg = f"Error pulling image {image_name}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'image': image_name,
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
            
            logger.info(f"Pre-pulling {len(self.global_images)} global Docker images")
            
            # Pull همه imageها
            results = []
            pulled_count = 0
            skipped_count = 0
            failed_count = 0
            
            for image in self.global_images:
                result = self.pull_image(image)
                results.append({
                    'image': image,
                    'result': result
                })
                
                if result['success']:
                    if result.get('changed', False):
                        pulled_count += 1
                        logger.info(f"Pulled image: {image}")
                    elif result.get('skipped', False):
                        skipped_count += 1
                        logger.debug(f"Skipped image: {image} - {result.get('message')}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to pull image: {image} - {result.get('error')}")
            
            # خلاصه نتایج
            all_success = failed_count == 0
            any_changed = pulled_count > 0
            
            final_result = {
                'success': all_success,
                'changed': any_changed,
                'total_images': len(self.global_images),
                'pulled': pulled_count,
                'skipped': skipped_count,
                'failed': failed_count,
                'results': results,
                'message': f"Pre-pulled {pulled_count} images, {skipped_count} skipped, {failed_count} failed"
            }
            
            if all_success:
                logger.info(f"Pre-pull images completed: {final_result['message']}")
                return self.complete_task(final_result)
            else:
                failed_images = [
                    r['image'] for r in results 
                    if not r['result']['success']
                ]
                error_msg = f"Failed to pull images: {', '.join(failed_images)}"
                return self.fail_task(error_msg, final_result)
                
        except Exception as e:
            error_msg = f"Unexpected error in pre-pull images task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self.fail_task(error_msg, {'exception': str(e)})