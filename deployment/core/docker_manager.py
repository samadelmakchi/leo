#!/usr/bin/env python3
"""
Docker Manager
مدیریت عملیات Docker
"""

import logging
import docker
from typing import Dict, Any, List, Optional, Union
from docker.models.containers import Container
from docker.models.networks import Network
from docker.models.volumes import Volume
from docker.models.images import Image
import time

logger = logging.getLogger(__name__)


class DockerManager:
    """مدیریت Docker"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        مقداردهی اولیه Docker Manager
        
        Args:
            config: تنظیمات Docker
        """
        self.config = config or {}
        self.base_url = self.config.get('docker_socket', 'unix://var/run/docker.sock')
        self.timeout = self.config.get('timeout', 300)
        
        try:
            self.client = docker.from_env(timeout=self.timeout)
            if self.base_url != 'unix://var/run/docker.sock':
                self.client = docker.DockerClient(base_url=self.base_url, timeout=self.timeout)
            
            # تست اتصال
            self.client.ping()
            logger.info("Docker client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            raise
    
    # ==================== Container Management ====================
    
    def list_containers(self, filters: Dict = None, all: bool = True) -> List[Container]:
        """
        لیست containerها
        
        Args:
            filters: فیلترها
            all: نمایش تمام containerها (حتی متوقف شده)
            
        Returns:
            لیست containerها
        """
        try:
            containers = self.client.containers.list(all=all, filters=filters)
            logger.debug(f"Found {len(containers)} containers")
            return containers
        except Exception as e:
            logger.error(f"Error listing containers: {str(e)}")
            return []
    
    def get_container(self, container_id: str) -> Optional[Container]:
        """
        دریافت یک container
        
        Args:
            container_id: ID یا نام container
            
        Returns:
            container یا None
        """
        try:
            container = self.client.containers.get(container_id)
            return container
        except docker.errors.NotFound:
            logger.warning(f"Container not found: {container_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting container {container_id}: {str(e)}")
            return None
    
    def create_container(self, config: Dict[str, Any]) -> Optional[Container]:
        """
        ایجاد container جدید
        
        Args:
            config: تنظیمات container
            
        Returns:
            container ایجاد شده یا None
        """
        try:
            container = self.client.containers.create(**config)
            logger.info(f"Container created: {container.id[:12]} ({container.name})")
            return container
        except Exception as e:
            logger.error(f"Error creating container: {str(e)}")
            return None
    
    def start_container(self, container_id: str) -> bool:
        """
        شروع یک container
        
        Args:
            container_id: ID یا نام container
            
        Returns:
            True اگر موفق باشد
        """
        try:
            container = self.get_container(container_id)
            if container:
                container.start()
                logger.info(f"Container started: {container_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error starting container {container_id}: {str(e)}")
            return False
    
    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        توقف یک container
        
        Args:
            container_id: ID یا نام container
            timeout: timeout توقف
            
        Returns:
            True اگر موفق باشد
        """
        try:
            container = self.get_container(container_id)
            if container:
                container.stop(timeout=timeout)
                logger.info(f"Container stopped: {container_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {str(e)}")
            return False
    
    def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        راه‌اندازی مجدد container
        
        Args:
            container_id: ID یا نام container
            timeout: timeout توقف
            
        Returns:
            True اگر موفق باشد
        """
        try:
            container = self.get_container(container_id)
            if container:
                container.restart(timeout=timeout)
                logger.info(f"Container restarted: {container_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error restarting container {container_id}: {str(e)}")
            return False
    
    def remove_container(self, container_id: str, force: bool = False, v: bool = False) -> bool:
        """
        حذف container
        
        Args:
            container_id: ID یا نام container
            force: حذف اجباری حتی اگر running باشد
            v: حذف volumeهای attached
            
        Returns:
            True اگر موفق باشد
        """
        try:
            container = self.get_container(container_id)
            if container:
                container.remove(force=force, v=v)
                logger.info(f"Container removed: {container_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing container {container_id}: {str(e)}")
            return False
    
    def container_exec(self, container_id: str, command: str, **kwargs) -> Dict:
        """
        اجرای command در container
        
        Args:
            container_id: ID یا نام container
            command: دستور برای اجرا
            **kwargs: آرگومان‌های اضافی
            
        Returns:
            نتیجه اجرا
        """
        try:
            container = self.get_container(container_id)
            if not container:
                return {
                    'success': False,
                    'error': f"Container not found: {container_id}"
                }
            
            exec_id = container.client.api.exec_create(
                container.id,
                command,
                **kwargs
            )['Id']
            
            output = container.client.api.exec_start(exec_id)
            exit_code = container.client.api.exec_inspect(exec_id)['ExitCode']
            
            result = {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'output': output.decode('utf-8') if isinstance(output, bytes) else output,
                'exec_id': exec_id
            }
            
            logger.debug(f"Command executed in container {container_id}: exit_code={exit_code}")
            return result
            
        except Exception as e:
            error_msg = f"Error executing command in container {container_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_container_stats(self, container_id: str) -> Dict:
        """
        دریافت آمار container
        
        Args:
            container_id: ID یا نام container
            
        Returns:
            آمار container
        """
        try:
            container = self.get_container(container_id)
            if not container:
                return {
                    'success': False,
                    'error': f"Container not found: {container_id}"
                }
            
            stats = container.stats(stream=False)
            
            # پردازش stats
            cpu_stats = stats.get('cpu_stats', {})
            memory_stats = stats.get('memory_stats', {})
            network_stats = stats.get('networks', {})
            
            result = {
                'success': True,
                'container_id': container_id,
                'container_name': container.name,
                'status': container.status,
                'cpu_usage': cpu_stats.get('cpu_usage', {}).get('total_usage', 0),
                'memory_usage': memory_stats.get('usage', 0),
                'memory_limit': memory_stats.get('limit', 0),
                'network_rx': sum(net.get('rx_bytes', 0) for net in network_stats.values()),
                'network_tx': sum(net.get('tx_bytes', 0) for net in network_stats.values()),
                'timestamp': stats.get('read', '')
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting stats for container {container_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    # ==================== Network Management ====================
    
    def list_networks(self, filters: Dict = None) -> List[Network]:
        """
        لیست شبکه‌ها
        
        Args:
            filters: فیلترها
            
        Returns:
            لیست شبکه‌ها
        """
        try:
            networks = self.client.networks.list(filters=filters)
            logger.debug(f"Found {len(networks)} networks")
            return networks
        except Exception as e:
            logger.error(f"Error listing networks: {str(e)}")
            return []
    
    def get_network(self, network_id: str) -> Optional[Network]:
        """
        دریافت یک شبکه
        
        Args:
            network_id: ID یا نام شبکه
            
        Returns:
            شبکه یا None
        """
        try:
            network = self.client.networks.get(network_id)
            return network
        except docker.errors.NotFound:
            logger.warning(f"Network not found: {network_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting network {network_id}: {str(e)}")
            return None
    
    def create_network(self, config: Dict[str, Any]) -> Optional[Network]:
        """
        ایجاد شبکه جدید
        
        Args:
            config: تنظیمات شبکه
            
        Returns:
            شبکه ایجاد شده یا None
        """
        try:
            network = self.client.networks.create(**config)
            logger.info(f"Network created: {network.id[:12]} ({network.name})")
            return network
        except docker.errors.APIError as e:
            if "already exists" in str(e):
                logger.warning(f"Network already exists: {config.get('name')}")
                return self.get_network(config['name'])
            else:
                logger.error(f"Error creating network: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error creating network: {str(e)}")
            raise
    
    def remove_network(self, network_id: str, force: bool = False) -> bool:
        """
        حذف شبکه
        
        Args:
            network_id: ID یا نام شبکه
            force: حذف اجباری
            
        Returns:
            True اگر موفق باشد
        """
        try:
            network = self.get_network(network_id)
            if network:
                network.remove(force=force)
                logger.info(f"Network removed: {network_id}")
                return True
            return False
        except docker.errors.APIError as e:
            if "has active endpoints" in str(e) and not force:
                logger.error(f"Network {network_id} has active containers. Use force=True to remove.")
                raise
            logger.error(f"Error removing network {network_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error removing network {network_id}: {str(e)}")
            return False
    
    def connect_container_to_network(self, container_id: str, network_id: str, 
                                   ipv4_address: str = None, aliases: List[str] = None) -> bool:
        """
        اتصال container به شبکه
        
        Args:
            container_id: ID یا نام container
            network_id: ID یا نام شبکه
            ipv4_address: آدرس IPv4
            aliases: aliasهای شبکه
            
        Returns:
            True اگر موفق باشد
        """
        try:
            container = self.get_container(container_id)
            network = self.get_network(network_id)
            
            if container and network:
                network.connect(container, ipv4_address=ipv4_address, aliases=aliases)
                logger.info(f"Container {container_id} connected to network {network_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error connecting container {container_id} to network {network_id}: {str(e)}")
            return False
    
    # ==================== Volume Management ====================
    
    def list_volumes(self, filters: Dict = None) -> List[Volume]:
        """
        لیست volumeها
        
        Args:
            filters: فیلترها
            
        Returns:
            لیست volumeها
        """
        try:
            volumes = self.client.volumes.list(filters=filters)
            logger.debug(f"Found {len(volumes)} volumes")
            return volumes
        except Exception as e:
            logger.error(f"Error listing volumes: {str(e)}")
            return []
    
    def get_volume(self, volume_id: str) -> Optional[Volume]:
        """
        دریافت یک volume
        
        Args:
            volume_id: ID یا نام volume
            
        Returns:
            volume یا None
        """
        try:
            volume = self.client.volumes.get(volume_id)
            return volume
        except docker.errors.NotFound:
            logger.warning(f"Volume not found: {volume_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting volume {volume_id}: {str(e)}")
            return None
    
    def create_volume(self, config: Dict[str, Any]) -> Optional[Volume]:
        """
        ایجاد volume جدید
        
        Args:
            config: تنظیمات volume
            
        Returns:
            volume ایجاد شده یا None
        """
        try:
            volume = self.client.volumes.create(**config)
            logger.info(f"Volume created: {volume.id[:12]} ({volume.name})")
            return volume
        except Exception as e:
            logger.error(f"Error creating volume: {str(e)}")
            return None
    
    def remove_volume(self, volume_id: str, force: bool = False) -> bool:
        """
        حذف volume
        
        Args:
            volume_id: ID یا نام volume
            force: حذف اجباری
            
        Returns:
            True اگر موفق باشد
        """
        try:
            volume = self.get_volume(volume_id)
            if volume:
                volume.remove(force=force)
                logger.info(f"Volume removed: {volume_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing volume {volume_id}: {str(e)}")
            return False
    
    # ==================== Image Management ====================
    
    def list_images(self, filters: Dict = None) -> List[Image]:
        """
        لیست imageها
        
        Args:
            filters: فیلترها
            
        Returns:
            لیست imageها
        """
        try:
            images = self.client.images.list(filters=filters)
            logger.debug(f"Found {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"Error listing images: {str(e)}")
            return []
    
    def pull_image(self, image_name: str, tag: str = None, **kwargs) -> Optional[Image]:
        """
        pull کردن image
        
        Args:
            image_name: نام image
            tag: tag image
            **kwargs: آرگومان‌های اضافی
            
        Returns:
            image یا None
        """
        try:
            full_image = f"{image_name}:{tag}" if tag else image_name
            logger.info(f"Pulling image: {full_image}")
            
            image = self.client.images.pull(image_name, tag=tag, **kwargs)
            logger.info(f"Image pulled: {full_image}")
            return image
        except Exception as e:
            logger.error(f"Error pulling image {image_name}:{tag if tag else 'latest'}: {str(e)}")
            return None
    
    def build_image(self, path: str, tag: str, **kwargs) -> Optional[Image]:
        """
        build کردن image
        
        Args:
            path: مسیر Dockerfile
            tag: tag برای image
            **kwargs: آرگومان‌های اضافی
            
        Returns:
            image ساخته شده یا None
        """
        try:
            logger.info(f"Building image from {path} with tag {tag}")
            
            image, logs = self.client.images.build(
                path=path,
                tag=tag,
                **kwargs
            )
            
            # لاگ کردن خروجی build
            for log in logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
            
            logger.info(f"Image built: {tag}")
            return image
            
        except Exception as e:
            logger.error(f"Error building image {tag}: {str(e)}")
            return None
    
    def remove_image(self, image_id: str, force: bool = False, noprune: bool = False) -> bool:
        """
        حذف image
        
        Args:
            image_id: ID یا نام image
            force: حذف اجباری
            noprune: عدم حذف parent images
            
        Returns:
            True اگر موفق باشد
        """
        try:
            self.client.images.remove(image_id, force=force, noprune=noprune)
            logger.info(f"Image removed: {image_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing image {image_id}: {str(e)}")
            return False
    
    # ==================== Docker Compose ====================
    
    def compose_up(self, compose_path: str, project_name: str = None, 
                  services: List[str] = None, **kwargs) -> Dict:
        """
        اجرای docker compose up
        
        Args:
            compose_path: مسیر docker-compose.yml
            project_name: نام پروژه
            services: لیست سرویس‌ها برای اجرا
            **kwargs: آرگومان‌های اضافی
            
        Returns:
            نتیجه اجرا
        """
        try:
            import yaml
            from pathlib import Path
            
            compose_file = Path(compose_path)
            if not compose_file.exists():
                return {
                    'success': False,
                    'error': f"Docker compose file not found: {compose_path}"
                }
            
            # خواندن فایل compose
            with open(compose_file, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            # برای سادگی، از docker-compose CLI استفاده می‌کنیم
            import subprocess
            
            cmd = ['docker', 'compose']
            
            if project_name:
                cmd.extend(['-p', project_name])
            
            cmd.extend(['-f', compose_path, 'up', '-d'])
            
            if services:
                cmd.extend(services)
            
            logger.info(f"Running docker compose up: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            result = {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'command': ' '.join(cmd)
            }
            
            if result['success']:
                logger.info("Docker compose up completed successfully")
            else:
                logger.error(f"Docker compose up failed: {process.stderr}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error running docker compose up: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def compose_down(self, compose_path: str, project_name: str = None, 
                    remove_volumes: bool = False, **kwargs) -> Dict:
        """
        اجرای docker compose down
        
        Args:
            compose_path: مسیر docker-compose.yml
            project_name: نام پروژه
            remove_volumes: حذف volumeها
            **kwargs: آرگومان‌های اضافی
            
        Returns:
            نتیجه اجرا
        """
        try:
            import subprocess
            
            cmd = ['docker', 'compose']
            
            if project_name:
                cmd.extend(['-p', project_name])
            
            cmd.extend(['-f', compose_path, 'down'])
            
            if remove_volumes:
                cmd.append('--volumes')
            
            if kwargs.get('remove_orphans', False):
                cmd.append('--remove-orphans')
            
            logger.info(f"Running docker compose down: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            result = {
                'success': process.returncode == 0,
                'returncode': process.returncode,
                'stdout': process.stdout.strip(),
                'stderr': process.stderr.strip(),
                'command': ' '.join(cmd)
            }
            
            if result['success']:
                logger.info("Docker compose down completed successfully")
            else:
                logger.error(f"Docker compose down failed: {process.stderr}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error running docker compose down: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    # ==================== Utilities ====================
    
    def get_system_info(self) -> Dict:
        """
        دریافت اطلاعات سیستم Docker
        
        Returns:
            اطلاعات سیستم
        """
        try:
            info = self.client.info()
            version = self.client.version()
            
            result = {
                'success': True,
                'info': {
                    'containers': info.get('Containers', 0),
                    'containers_running': info.get('ContainersRunning', 0),
                    'containers_stopped': info.get('ContainersStopped', 0),
                    'containers_paused': info.get('ContainersPaused', 0),
                    'images': info.get('Images', 0),
                    'driver': info.get('Driver', ''),
                    'docker_root_dir': info.get('DockerRootDir', ''),
                    'architecture': info.get('Architecture', ''),
                    'os': info.get('OperatingSystem', ''),
                    'kernel_version': info.get('KernelVersion', ''),
                    'cpus': info.get('NCPU', 0),
                    'memory': info.get('MemTotal', 0)
                },
                'version': {
                    'api_version': version.get('ApiVersion', ''),
                    'version': version.get('Version', ''),
                    'git_commit': version.get('GitCommit', ''),
                    'go_version': version.get('GoVersion', ''),
                    'os': version.get('Os', ''),
                    'arch': version.get('Arch', '')
                }
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting Docker system info: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def cleanup(self, remove_containers: bool = False, remove_volumes: bool = False, 
               remove_images: bool = False, remove_networks: bool = False) -> Dict:
        """
        تمیز کردن منابع Docker
        
        Args:
            remove_containers: حذف containerهای متوقف شده
            remove_volumes: حذف volumeهای بدون استفاده
            remove_images: حذف imageهای بدون استفاده
            remove_networks: حذف شبکه‌های بدون استفاده
            
        Returns:
            نتیجه cleanup
        """
        try:
            results = {
                'containers_removed': 0,
                'volumes_removed': 0,
                'images_removed': 0,
                'networks_removed': 0
            }
            
            if remove_containers:
                # حذف containerهای متوقف شده
                stopped_containers = self.list_containers(filters={'status': 'exited'})
                for container in stopped_containers:
                    if self.remove_container(container.id):
                        results['containers_removed'] += 1
            
            if remove_volumes:
                # حذف volumeهای بدون استفاده (نیاز به دسترسی privileged)
                try:
                    import subprocess
                    process = subprocess.run(
                        ['docker', 'volume', 'prune', '-f'],
                        capture_output=True,
                        text=True
                    )
                    if process.returncode == 0:
                        # استخراج تعداد volumeهای حذف شده از خروجی
                        import re
                        match = re.search(r'Total reclaimed space:.*\((\d+) volumes?\)', process.stdout)
                        if match:
                            results['volumes_removed'] = int(match.group(1))
                except Exception as e:
                    logger.warning(f"Error pruning volumes: {str(e)}")
            
            if remove_images:
                # حذف imageهای بدون tag
                dangling_images = self.list_images(filters={'dangling': True})
                for image in dangling_images:
                    if self.remove_image(image.id):
                        results['images_removed'] += 1
            
            if remove_networks:
                # حذف شبکه‌های بدون استفاده
                try:
                    import subprocess
                    process = subprocess.run(
                        ['docker', 'network', 'prune', '-f'],
                        capture_output=True,
                        text=True
                    )
                    if process.returncode == 0:
                        import re
                        match = re.search(r'Total reclaimed space:.*\((\d+) networks?\)', process.stdout)
                        if match:
                            results['networks_removed'] = int(match.group(1))
                except Exception as e:
                    logger.warning(f"Error pruning networks: {str(e)}")
            
            result = {
                'success': True,
                'results': results,
                'message': f"Cleanup completed: {results['containers_removed']} containers, "
                          f"{results['volumes_removed']} volumes, "
                          f"{results['images_removed']} images, "
                          f"{results['networks_removed']} networks removed"
            }
            
            logger.info(result['message'])
            return result
            
        except Exception as e:
            error_msg = f"Error during Docker cleanup: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }


def create_docker_manager(config: Dict = None) -> DockerManager:
    """
    تابع helper برای ایجاد Docker Manager
    
    Args:
        config: تنظیمات
        
    Returns:
        instance از DockerManager
    """
    return DockerManager(config)