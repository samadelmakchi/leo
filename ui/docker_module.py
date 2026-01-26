"""
ماژول مدیریت Docker
"""

import docker
from flask import Blueprint, jsonify, request
import traceback

# ایجاد Blueprint برای Docker
docker_bp = Blueprint('docker', __name__, url_prefix='/api/docker')

# ایجاد کلاینت داکر
try:
    docker_client = docker.from_env()
    DOCKER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Docker not available: {e}")
    docker_client = None
    DOCKER_AVAILABLE = False

def check_docker_available():
    """بررسی در دسترس بودن Docker"""
    if not DOCKER_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "Docker is not available or not running"
        }), 500
    return None

# ============================================================================
# Routes for Images
# ============================================================================

@docker_bp.route("/images", methods=["GET"])
def get_docker_images():
    """دریافت لیست تمام ایمیج‌های Docker"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        images = docker_client.images.list(all=True)
        
        images_list = []
        for image in images:
            # گرفتن تگ‌های ایمیج
            tags = image.tags if image.tags else ["<none>:<none>"]
            
            for tag in tags:
                # محاسبه سایز
                size_mb = image.attrs['Size'] / (1024 * 1024)
                
                # گرفتن زمان ایجاد
                created = image.attrs['Created'].split('.')[0].replace('T', ' ')
                
                # گرفتن repo و tag
                repo_tag_split = tag.split(':')
                repository = repo_tag_split[0] if len(repo_tag_split) > 0 else tag
                image_tag = repo_tag_split[1] if len(repo_tag_split) > 1 else "latest"
                
                images_list.append({
                    "id": image.short_id.replace('sha256:', ''),
                    "repository": repository,
                    "tag": image_tag,
                    "size": f"{size_mb:.2f} MB",
                    "size_bytes": image.attrs['Size'],
                    "created": created,
                    "full_id": image.id,
                    "labels": image.attrs.get('Labels', {}),
                    "virtual_size": image.attrs.get('VirtualSize', 0)
                })
        
        # مرتب کردن بر اساس زمان ایجاد (جدیدترین اول)
        images_list.sort(key=lambda x: x["created"], reverse=True)
        
        return jsonify({
            "status": "success",
            "count": len(images_list),
            "images": images_list
        })
        
    except Exception as e:
        print(f"❌ Error getting images: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc()
        }), 500

@docker_bp.route("/images/remove", methods=["POST"])
def remove_docker_image():
    """حذف یک ایمیج Docker"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        image_id = data.get("image_id")
        force = data.get("force", False)
        
        if not image_id:
            return jsonify({
                "status": "error",
                "message": "Image ID is required"
            }), 400
        
        # حذف ایمیج
        docker_client.images.remove(image_id, force=force)
        
        return jsonify({
            "status": "success",
            "message": f"Image {image_id} removed successfully"
        })
        
    except docker.errors.ImageNotFound:
        return jsonify({
            "status": "error",
            "message": f"Image not found: {image_id}"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        print(f"❌ Error removing image: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/images/prune", methods=["POST"])
def prune_docker_images():
    """حذف ایمیج‌های بدون استفاده"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        # حذف ایمیج‌های بدون استفاده
        result = docker_client.images.prune(filters={"dangling": False})
        
        deleted_count = len(result.get('ImagesDeleted', []))
        space_reclaimed = result.get('SpaceReclaimed', 0)
        
        return jsonify({
            "status": "success",
            "deleted_count": deleted_count,
            "space_reclaimed_mb": f"{space_reclaimed / (1024*1024):.2f}",
            "space_reclaimed": f"{space_reclaimed / (1024*1024):.2f} MB",
            "details": result
        })
        
    except Exception as e:
        print(f"❌ Error pruning images: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/images/pull", methods=["POST"])
def pull_docker_image():
    """Pull یک ایمیج جدید از registry"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        image_name = data.get("image")
        
        if not image_name:
            return jsonify({
                "status": "error",
                "message": "Image name is required"
            }), 400
        
        # pull ایمیج
        image = docker_client.images.pull(image_name)
        
        return jsonify({
            "status": "success",
            "message": f"Image {image_name} pulled successfully",
            "image_id": image.id,
            "tags": image.tags
        })
        
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        print(f"❌ Error pulling image: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/images/build", methods=["POST"])
def build_docker_image():
    """Build یک ایمیج از Dockerfile"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        dockerfile_path = data.get("path", ".")
        tag = data.get("tag", "custom-image:latest")
        
        # در اینجا می‌توانید منطق build را اضافه کنید
        # فعلاً به عنوان نمونه
        return jsonify({
            "status": "success",
            "message": f"Building image from {dockerfile_path} with tag {tag}",
            "note": "This endpoint needs implementation based on your requirements"
        })
        
    except Exception as e:
        print(f"❌ Error building image: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================================================
# Routes for System Info
# ============================================================================

@docker_bp.route("/system", methods=["GET"])
def get_docker_system_info():
    """دریافت اطلاعات سیستم Docker"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        # اطلاعات سیستم داکر
        info = docker_client.info()
        
        # اطلاعات دیسک
        disk_usage = docker_client.df()
        
        # محاسبه سایز لایه‌ها
        layers_size = disk_usage.get('LayersSize', 0)
        layers_size_gb = layers_size / (1024 * 1024 * 1024)
        
        return jsonify({
            "status": "success",
            "images_count": info['Images'],
            "containers_count": info['Containers'],
            "running_containers": info['ContainersRunning'],
            "stopped_containers": info['ContainersStopped'],
            "paused_containers": info['ContainersPaused'],
            "disk_usage": f"{layers_size_gb:.2f} GB",
            "system_info": {
                "docker_version": info['ServerVersion'],
                "os": info['OperatingSystem'],
                "architecture": info['Architecture'],
                "kernel_version": info['KernelVersion'],
                "cpus": info['NCPU'],
                "memory": f"{info['MemTotal'] / (1024*1024*1024):.2f} GB"
            }
        })
        
    except Exception as e:
        print(f"❌ Error getting system info: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/ping", methods=["GET"])
def docker_ping():
    """بررسی وضعیت اتصال به Docker"""
    try:
        if not DOCKER_AVAILABLE:
            return jsonify({
                "status": "error",
                "message": "Docker client not initialized"
            }), 500
        
        # تست اتصال
        docker_client.ping()
        
        return jsonify({
            "status": "success",
            "message": "Docker is running and accessible"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================================================
# Helper Functions
# ============================================================================

def get_image_details(image_id):
    """دریافت جزئیات یک ایمیج خاص"""
    if not DOCKER_AVAILABLE:
        return None
    
    try:
        image = docker_client.images.get(image_id)
        return image.attrs
    except:
        return None

def search_images_by_name(name):
    """جستجوی ایمیج‌ها بر اساس نام"""
    if not DOCKER_AVAILABLE:
        return []
    
    try:
        all_images = docker_client.images.list(all=True)
        matched = []
        
        for image in all_images:
            for tag in (image.tags or []):
                if name.lower() in tag.lower():
                    matched.append(image)
                    break
        
        return matched
    except:
        return []
    
# ============================================================================
# Routes for Docker Networks
# ============================================================================

@docker_bp.route("/networks", methods=["GET"])
def get_docker_networks():
    """دریافت لیست شبکه‌های Docker"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        networks = docker_client.networks.list()
        
        networks_list = []
        for network in networks:
            network_data = {
                "id": network.short_id,
                "name": network.name,
                "driver": network.attrs.get('Driver', 'bridge'),
                "scope": network.attrs.get('Scope', 'local'),
                "created": network.attrs.get('Created', '').split('.')[0].replace('T', ' '),
                "labels": network.attrs.get('Labels', {}),
                "containers": len(network.attrs.get('Containers', {})),
                "internal": network.attrs.get('Internal', False),
                "attachable": network.attrs.get('Attachable', False),
                "ipam": network.attrs.get('IPAM', {})
            }
            networks_list.append(network_data)
        
        # مرتب کردن بر اساس نام
        networks_list.sort(key=lambda x: x["name"])
        
        return jsonify({
            "status": "success",
            "count": len(networks_list),
            "networks": networks_list
        })
        
    except Exception as e:
        print(f"❌ Error getting networks: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/networks/<network_id>", methods=["GET"])
def get_docker_network_details(network_id):
    """دریافت جزئیات یک شبکه خاص"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        network = docker_client.networks.get(network_id)
        
        return jsonify({
            "status": "success",
            "network": {
                "id": network.id,
                "name": network.name,
                "attrs": network.attrs
            }
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Network {network_id} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/networks/create", methods=["POST"])
def create_docker_network():
    """ایجاد شبکه جدید"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        name = data.get("name")
        driver = data.get("driver", "bridge")
        internal = data.get("internal", False)
        attachable = data.get("attachable", True)
        labels = data.get("labels", {})
        
        if not name:
            return jsonify({
                "status": "error",
                "message": "Network name is required"
            }), 400
        
        # ایجاد شبکه
        network = docker_client.networks.create(
            name=name,
            driver=driver,
            internal=internal,
            attachable=attachable,
            labels=labels
        )
        
        return jsonify({
            "status": "success",
            "message": f"Network '{name}' created successfully",
            "network_id": network.id,
            "name": network.name
        })
        
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/networks/<network_id>/remove", methods=["POST"])
def remove_docker_network(network_id):
    """حذف یک شبکه"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        network = docker_client.networks.get(network_id)
        network_name = network.name
        
        # بررسی اینکه شبکه خالی باشد
        if network.attrs.get('Containers'):
            return jsonify({
                "status": "error",
                "message": f"Cannot remove network '{network_name}' because it has connected containers"
            }), 400
        
        # حذف شبکه
        network.remove()
        
        return jsonify({
            "status": "success",
            "message": f"Network '{network_name}' removed successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Network {network_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/networks/prune", methods=["POST"])
def prune_docker_networks():
    """حذف شبکه‌های بدون استفاده"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        # حذف شبکه‌های بدون استفاده
        result = docker_client.networks.prune()
        
        return jsonify({
            "status": "success",
            "deleted_count": len(result.get('NetworksDeleted', [])),
            "space_reclaimed": result.get('SpaceReclaimed', 0),
            "details": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/networks/<network_id>/containers", methods=["GET"])
def get_network_containers(network_id):
    """دریافت لیست کانتینرهای متصل به شبکه"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        network = docker_client.networks.get(network_id)
        containers = network.attrs.get('Containers', {})
        
        containers_list = []
        for container_id, container_info in containers.items():
            containers_list.append({
                "id": container_id[:12],
                "full_id": container_id,
                "name": container_info.get('Name', ''),
                "ipv4": container_info.get('IPv4Address', ''),
                "ipv6": container_info.get('IPv6Address', ''),
                "mac_address": container_info.get('MacAddress', '')
            })
        
        return jsonify({
            "status": "success",
            "network": network.name,
            "containers_count": len(containers_list),
            "containers": containers_list
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Network {network_id} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
# ============================================================================
# Routes for Docker Volumes
# ============================================================================

@docker_bp.route("/volumes", methods=["GET"])
def get_docker_volumes():
    """دریافت لیست ولوم‌های Docker"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        volumes = docker_client.volumes.list()
        
        volumes_list = []
        for volume in volumes:
            volume_data = {
                "id": volume.id,  # در ولوم‌ها، id و name معمولاً یکی هستند
                "name": volume.name,
                "driver": volume.attrs.get('Driver', 'local'),
                "mountpoint": volume.attrs.get('Mountpoint', ''),
                "created": volume.attrs.get('CreatedAt', '').split('.')[0].replace('T', ' '),
                "labels": volume.attrs.get('Labels', {}),
                "scope": volume.attrs.get('Scope', 'local'),
                "options": volume.attrs.get('Options', {}),
                "usage_data": volume.attrs.get('UsageData', {})
            }
            volumes_list.append(volume_data)
        
        # مرتب کردن بر اساس نام
        volumes_list.sort(key=lambda x: x["name"])
        
        return jsonify({
            "status": "success",
            "count": len(volumes_list),
            "volumes": volumes_list
        })
        
    except Exception as e:
        print(f"❌ Error getting volumes: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/volumes/<volume_name>", methods=["GET"])
def get_docker_volume_details(volume_name):
    """دریافت جزئیات یک ولوم خاص"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        volume = docker_client.volumes.get(volume_name)
        
        return jsonify({
            "status": "success",
            "volume": {
                "name": volume.name,
                "attrs": volume.attrs
            }
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Volume {volume_name} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/volumes/create", methods=["POST"])
def create_docker_volume():
    """ایجاد ولوم جدید"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        name = data.get("name")
        driver = data.get("driver", "local")
        driver_opts = data.get("driver_opts", {})
        labels = data.get("labels", {})
        
        if not name:
            return jsonify({
                "status": "error",
                "message": "Volume name is required"
            }), 400
        
        # ایجاد ولوم
        volume = docker_client.volumes.create(
            name=name,
            driver=driver,
            driver_opts=driver_opts,
            labels=labels
        )
        
        return jsonify({
            "status": "success",
            "message": f"Volume '{name}' created successfully",
            "volume_name": volume.name,
            "driver": volume.attrs.get('Driver', 'local')
        })
        
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/volumes/<volume_name>/remove", methods=["POST"])
def remove_docker_volume(volume_name):
    """حذف یک ولوم"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        volume = docker_client.volumes.get(volume_name)
        
        # حذف ولوم
        volume.remove()
        
        return jsonify({
            "status": "success",
            "message": f"Volume '{volume_name}' removed successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Volume {volume_name} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/volumes/prune", methods=["POST"])
def prune_docker_volumes():
    """حذف ولوم‌های بدون استفاده"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        # حذف ولوم‌های بدون استفاده
        result = docker_client.volumes.prune()
        
        deleted_count = len(result.get('VolumesDeleted', []))
        space_reclaimed = result.get('SpaceReclaimed', 0)
        
        return jsonify({
            "status": "success",
            "deleted_count": deleted_count,
            "space_reclaimed": f"{space_reclaimed / (1024*1024):.2f} MB",
            "space_reclaimed_bytes": space_reclaimed,
            "details": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/volumes/<volume_name>/inspect", methods=["GET"])
def inspect_docker_volume(volume_name):
    """بررسی محتوای یک ولوم (فهرست فایل‌ها)"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        import subprocess
        import json
        
        volume = docker_client.volumes.get(volume_name)
        mountpoint = volume.attrs.get('Mountpoint', '')
        
        if not mountpoint:
            return jsonify({
                "status": "error",
                "message": "Mountpoint not found for this volume"
            }), 404
        
        # اجرای دستور ls برای مشاهده محتوا
        try:
            result = subprocess.run(
                ['ls', '-la', mountpoint],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            files_list = []
            if result.returncode == 0:
                # پردازش خروجی ls
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # خط اول header است
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 9:
                            file_info = {
                                "permissions": parts[0],
                                "links": parts[1],
                                "owner": parts[2],
                                "group": parts[3],
                                "size": parts[4],
                                "month": parts[5],
                                "day": parts[6],
                                "time": parts[7],
                                "name": ' '.join(parts[8:])
                            }
                            files_list.append(file_info)
            
            return jsonify({
                "status": "success",
                "volume": volume_name,
                "mountpoint": mountpoint,
                "files_count": len(files_list),
                "files": files_list,
                "raw_output": result.stdout if result.returncode == 0 else ""
            })
            
        except subprocess.TimeoutExpired:
            return jsonify({
                "status": "error",
                "message": "Timeout while inspecting volume"
            }), 500
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error inspecting volume: {str(e)}"
            }), 500
            
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Volume {volume_name} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/volumes/stats", methods=["GET"])
def get_volumes_stats():
    """دریافت آمار ولوم‌ها"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        volumes = docker_client.volumes.list()
        
        total_volumes = len(volumes)
        local_driver = sum(1 for v in volumes if v.attrs.get('Driver') == 'local')
        other_drivers = total_volumes - local_driver
        
        # محاسبه سایز تخمینی (نیاز به دسترسی root دارد)
        total_size = 0
        labeled_volumes = 0
        
        for volume in volumes:
            if volume.attrs.get('Labels'):
                labeled_volumes += 1
            # می‌توانید محاسبه سایز واقعی را اینجا اضافه کنید
        
        return jsonify({
            "status": "success",
            "total_volumes": total_volumes,
            "local_driver": local_driver,
            "other_drivers": other_drivers,
            "labeled_volumes": labeled_volumes,
            "estimated_size": f"{total_size / (1024*1024):.2f} MB"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
    # ============================================================================
# Routes for Docker Containers
# ============================================================================

@docker_bp.route("/containers", methods=["GET"])
def get_docker_containers():
    """دریافت لیست کانتینرهای Docker"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        # دریافت تمام کانتینرها (شامل running و stopped)
        containers = docker_client.containers.list(all=True)
        
        containers_list = []
        for container in containers:
            container_attrs = container.attrs
            
            # گرفتن وضعیت
            status = container.status
            state = container_attrs.get('State', {})
            
            # گرفتن اطلاعات شبکه
            network_settings = container_attrs.get('NetworkSettings', {})
            networks = network_settings.get('Networks', {})
            
            # گرفتن نام تصویر
            image_name = container_attrs.get('Config', {}).get('Image', '')
            
            # گرفتن دستور اجرا
            command = container_attrs.get('Config', {}).get('Cmd', [])
            if isinstance(command, list):
                command_str = ' '.join(command)
            else:
                command_str = str(command)
            
            container_data = {
                "id": container.short_id,
                "full_id": container.id,
                "name": container.name,
                "image": image_name,
                "image_id": container_attrs.get('Image', '').split(':')[1][:12] if ':' in container_attrs.get('Image', '') else '',
                "status": status,
                "state": state.get('Status', 'unknown'),
                "created": container_attrs.get('Created', '').split('.')[0].replace('T', ' '),
                "ports": container_attrs.get('NetworkSettings', {}).get('Ports', {}),
                "networks": list(networks.keys()),
                "command": command_str[:100] + ('...' if len(command_str) > 100 else ''),
                "labels": container_attrs.get('Config', {}).get('Labels', {}),
                "restart_policy": container_attrs.get('HostConfig', {}).get('RestartPolicy', {}),
                "mounts": container_attrs.get('Mounts', []),
                "health": state.get('Health', {}).get('Status', '') if state.get('Health') else '',
                "exit_code": state.get('ExitCode', 0)
            }
            containers_list.append(container_data)
        
        # مرتب کردن بر اساس زمان ایجاد (جدیدترین اول)
        containers_list.sort(key=lambda x: x["created"], reverse=True)
        
        return jsonify({
            "status": "success",
            "count": len(containers_list),
            "containers": containers_list
        })
        
    except Exception as e:
        print(f"❌ Error getting containers: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>", methods=["GET"])
def get_docker_container_details(container_id):
    """دریافت جزئیات یک کانتینر خاص"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        
        return jsonify({
            "status": "success",
            "container": {
                "id": container.id,
                "name": container.name,
                "attrs": container.attrs
            }
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/start", methods=["POST"])
def start_docker_container(container_id):
    """شروع یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        container.start()
        
        return jsonify({
            "status": "success",
            "message": f"Container {container.name} started successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/stop", methods=["POST"])
def stop_docker_container(container_id):
    """توقف یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        container.stop()
        
        return jsonify({
            "status": "success",
            "message": f"Container {container.name} stopped successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/restart", methods=["POST"])
def restart_docker_container(container_id):
    """راه‌اندازی مجدد یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        container.restart()
        
        return jsonify({
            "status": "success",
            "message": f"Container {container.name} restarted successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/pause", methods=["POST"])
def pause_docker_container(container_id):
    """مکث یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        container.pause()
        
        return jsonify({
            "status": "success",
            "message": f"Container {container.name} paused successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/unpause", methods=["POST"])
def unpause_docker_container(container_id):
    """ادامه دادن یک کانتینر مکث شده"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        container.unpause()
        
        return jsonify({
            "status": "success",
            "message": f"Container {container.name} unpaused successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/remove", methods=["POST"])
def remove_docker_container(container_id):
    """حذف یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json or {}
        force = data.get("force", False)
        v = data.get("v", False)  # حذف ولوم‌های مرتبط
        
        container = docker_client.containers.get(container_id)
        container_name = container.name
        
        # توقف کانتینر اگر در حال اجراست
        if container.status == 'running' and not force:
            return jsonify({
                "status": "error",
                "message": f"Cannot remove running container {container_name}. Stop it first or use force."
            }), 400
        
        container.remove(force=force, v=v)
        
        return jsonify({
            "status": "success",
            "message": f"Container {container_name} removed successfully"
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/logs", methods=["GET"])
def get_container_logs(container_id):
    """دریافت لاگ‌های یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        
        # دریافت پارامترها
        tail = request.args.get('tail', '100')
        since = request.args.get('since')
        until = request.args.get('until')
        follow = request.args.get('follow', 'false').lower() == 'true'
        
        # دریافت لاگ‌ها
        logs = container.logs(
            tail=tail,
            since=since,
            until=until,
            follow=follow,
            stdout=True,
            stderr=True,
            timestamps=request.args.get('timestamps', 'false').lower() == 'true'
        )
        
        # تبدیل بایت به رشته
        logs_str = logs.decode('utf-8', errors='replace')
        
        return jsonify({
            "status": "success",
            "container": container.name,
            "logs": logs_str,
            "lines_count": len(logs_str.split('\n'))
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/stats", methods=["GET"])
def get_container_stats(container_id):
    """دریافت آمار مصرف منابع یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        container = docker_client.containers.get(container_id)
        stats = container.stats(stream=False)
        
        # پردازش آمار
        cpu_stats = stats.get('cpu_stats', {})
        memory_stats = stats.get('memory_stats', {})
        network_stats = stats.get('networks', {})
        
        processed_stats = {
            "cpu_usage": {
                "total_usage": cpu_stats.get('cpu_usage', {}).get('total_usage', 0),
                "system_cpu_usage": cpu_stats.get('system_cpu_usage', 0),
                "percent": 0.0
            },
            "memory": {
                "usage": memory_stats.get('usage', 0),
                "limit": memory_stats.get('limit', 0),
                "percent": 0.0
            },
            "network": network_stats,
            "pids": stats.get('pids_stats', {}).get('current', 0),
            "read_time": stats.get('read', '')
        }
        
        # محاسبه درصد CPU
        if (cpu_stats.get('cpu_usage', {}).get('total_usage') and 
            cpu_stats.get('system_cpu_usage')):
            cpu_delta = cpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage']
            if system_delta > 0:
                processed_stats['cpu_usage']['percent'] = (cpu_delta / system_delta) * 100.0
        
        # محاسبه درصد Memory
        if memory_stats.get('usage') and memory_stats.get('limit'):
            processed_stats['memory']['percent'] = (memory_stats['usage'] / memory_stats['limit']) * 100.0
        
        return jsonify({
            "status": "success",
            "container": container.name,
            "stats": processed_stats
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/<container_id>/exec", methods=["POST"])
def exec_container_command(container_id):
    """اجرای دستور در یک کانتینر"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        command = data.get("command")
        
        if not command:
            return jsonify({
                "status": "error",
                "message": "Command is required"
            }), 400
        
        container = docker_client.containers.get(container_id)
        
        # اجرای دستور
        exec_result = container.exec_run(
            cmd=command,
            stdout=True,
            stderr=True,
            stdin=False,
            tty=False
        )
        
        exit_code = exec_result.exit_code
        output = exec_result.output.decode('utf-8', errors='replace')
        
        return jsonify({
            "status": "success",
            "container": container.name,
            "command": command,
            "exit_code": exit_code,
            "output": output
        })
        
    except docker.errors.NotFound:
        return jsonify({
            "status": "error",
            "message": f"Container {container_id} not found"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/create", methods=["POST"])
def create_docker_container():
    """ایجاد کانتینر جدید"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        data = request.json
        
        # پارامترهای الزامی
        image = data.get("image")
        name = data.get("name")
        
        if not image:
            return jsonify({
                "status": "error",
                "message": "Image name is required"
            }), 400
        
        # پارامترهای اختیاری
        command = data.get("command")
        ports = data.get("ports", {})
        volumes = data.get("volumes", {})
        environment = data.get("environment", {})
        network = data.get("network")
        restart_policy = data.get("restart_policy", {"Name": "unless-stopped"})
        
        # ایجاد کانتینر
        container = docker_client.containers.create(
            image=image,
            name=name,
            command=command,
            ports=ports,
            volumes=volumes,
            environment=environment,
            network=network,
            restart_policy=restart_policy,
            detach=True
        )
        
        return jsonify({
            "status": "success",
            "message": f"Container created successfully",
            "container_id": container.id,
            "name": container.name
        })
        
    except docker.errors.ImageNotFound:
        return jsonify({
            "status": "error",
            "message": f"Image not found: {image}"
        }), 404
    except docker.errors.APIError as e:
        return jsonify({
            "status": "error",
            "message": str(e.explanation)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/prune", methods=["POST"])
def prune_docker_containers():
    """حذف کانتینرهای متوقف شده"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        # حذف کانتینرهای متوقف شده
        result = docker_client.containers.prune()
        
        return jsonify({
            "status": "success",
            "deleted_count": len(result.get('ContainersDeleted', [])),
            "space_reclaimed": f"{result.get('SpaceReclaimed', 0) / (1024*1024):.2f} MB",
            "details": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/containers/stats/all", methods=["GET"])
def get_all_containers_stats():
    """دریافت آمار تمام کانتینرها"""
    error_response = check_docker_available()
    if error_response:
        return error_response
    
    try:
        containers = docker_client.containers.list(all=True)
        
        stats_summary = {
            "total": len(containers),
            "running": sum(1 for c in containers if c.status == 'running'),
            "stopped": sum(1 for c in containers if c.status == 'exited' or c.status == 'stopped'),
            "paused": sum(1 for c in containers if c.status == 'paused'),
            "restarting": sum(1 for c in containers if c.status == 'restarting'),
            "images": len(set(c.attrs['Config']['Image'] for c in containers))
        }
        
        return jsonify({
            "status": "success",
            "stats": stats_summary
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500