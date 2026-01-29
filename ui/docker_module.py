"""
ماژول مدیریت Docker - نسخه بهینه‌شده
"""

import docker
import subprocess
import json
from flask import Blueprint, jsonify, request
from functools import wraps
from utils import paginate, get_pagination_params
from app import cache
import logging

logger = logging.getLogger(__name__)

# ایجاد Blueprint برای Docker
docker_bp = Blueprint('docker', __name__, url_prefix='/api/docker')

# ============================================================================
# مدیریت Docker Client
# ============================================================================

def init_docker_client():
    """ایجاد و مدیریت Docker Client"""
    global docker_client, DOCKER_AVAILABLE
    
    try:
        docker_client = docker.from_env()
        docker_client.ping()  # تست اتصال
        DOCKER_AVAILABLE = True
        logger.info("✅ Docker client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Docker not available: {e}")
        docker_client = None
        DOCKER_AVAILABLE = False

# مقداردهی اولیه
init_docker_client()

# ============================================================================
# Decorator برای مدیریت خطاها
# ============================================================================

def handle_docker_errors(func):
    """دکوراتور برای مدیریت خطاهای Docker"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # بررسی دسترسی به Docker
        if not DOCKER_AVAILABLE:
            logger.warning("Docker not available")
            return jsonify({
                "status": "error",
                "message": "Docker is not available or not running"
            }), 503
        
        try:
            logger.debug(f"Executing {func.__name__}")
            return func(*args, **kwargs)
        except docker.errors.NotFound as e:
            logger.warning(f"Resource not found in {func.__name__}: {e}")
            return jsonify({
                "status": "error",
                "message": f"Resource not found: {str(e)}"
            }), 404
        except docker.errors.APIError as e:
            logger.error(f"Docker API error in {func.__name__}: {e}")
            return jsonify({
                "status": "error",
                "message": f"Docker API error: {str(e.explanation)}"
            }), 500
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Internal server error: {str(e)[:100]}..."
            }), 500
    return wrapper

# ============================================================================
# توابع کمکی مشترک
# ============================================================================

def format_size(size_bytes):
    """فرمت‌بندی سایز به صورت خوانا"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def parse_datetime(docker_datetime):
    """تبدیل datetime داکر به فرمت خوانا"""
    if not docker_datetime:
        return ""
    return docker_datetime.split('.')[0].replace('T', ' ')

# ============================================================================
# Routes for Images
# ============================================================================

@docker_bp.route("/images", methods=["GET"])
@handle_docker_errors
def get_docker_images():
    """دریافت لیست تمام ایمیج‌های Docker"""
    images = docker_client.images.list(all=True)
    
    images_list = []
    for image in images:
        tags = image.tags if image.tags else ["<none>:<none>"]
        
        for tag in tags:
            size_mb = image.attrs['Size'] / (1024 * 1024)
            created = parse_datetime(image.attrs.get('Created'))
            
            repo_tag_split = tag.split(':')
            repository = repo_tag_split[0] if len(repo_tag_split) > 0 else tag
            image_tag = repo_tag_split[1] if len(repo_tag_split) > 1 else "latest"
            
            images_list.append({
                "id": image.short_id.replace('sha256:', ''),
                "repository": repository,
                "tag": image_tag,
                "size": format_size(image.attrs['Size']),
                "size_bytes": image.attrs['Size'],
                "created": created,
                "full_id": image.id,
                "labels": image.attrs.get('Labels', {}),
                "virtual_size": image.attrs.get('VirtualSize', 0)
            })
    
    # مرتب کردن و صفحه‌بندی
    images_list.sort(key=lambda x: x["created"], reverse=True)
    
    page, per_page = get_pagination_params(request)
    paginated_images, total, total_pages = paginate(images_list, page, per_page)
    
    logger.info(f"Retrieved {len(images_list)} images, showing page {page}/{total_pages}")
    
    return jsonify({
        "status": "success",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "count": len(images_list),
        "images": paginated_images
    })

@docker_bp.route("/images/remove", methods=["POST"])
@handle_docker_errors
def remove_docker_image():
    """حذف یک ایمیج Docker"""
    data = request.json
    image_id = data.get("image_id")
    force = data.get("force", False)
    
    if not image_id:
        return jsonify({
            "status": "error",
            "message": "Image ID is required"
        }), 400
    
    logger.info(f"Removing image: {image_id}, force={force}")
    docker_client.images.remove(image_id, force=force)
    logger.info(f"Image {image_id} removed successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Image {image_id} removed successfully"
    })

@docker_bp.route("/images/prune", methods=["POST"])
@handle_docker_errors
def prune_docker_images():
    """حذف ایمیج‌های بدون استفاده"""
    result = docker_client.images.prune(filters={"dangling": False})
    
    deleted_count = len(result.get('ImagesDeleted', []))
    space_reclaimed = result.get('SpaceReclaimed', 0)
    
    logger.info(f"Pruned {deleted_count} images, reclaimed {format_size(space_reclaimed)}")
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "space_reclaimed": format_size(space_reclaimed),
        "space_reclaimed_bytes": space_reclaimed,
        "details": result
    })

@docker_bp.route("/images/pull", methods=["POST"])
@handle_docker_errors
def pull_docker_image():
    """Pull یک ایمیج جدید از registry"""
    data = request.json
    image_name = data.get("image")
    
    if not image_name:
        return jsonify({
            "status": "error",
            "message": "Image name is required"
        }), 400
    
    logger.info(f"Pulling image: {image_name}")
    image = docker_client.images.pull(image_name)
    logger.info(f"Image {image_name} pulled successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Image {image_name} pulled successfully",
        "image_id": image.id,
        "tags": image.tags
    })

@docker_bp.route("/images/build", methods=["POST"])
@handle_docker_errors
def build_docker_image():
    """Build یک ایمیج از Dockerfile"""
    data = request.json
    dockerfile_path = data.get("path", ".")
    tag = data.get("tag", "custom-image:latest")
    
    # در اینجا می‌توانید منطق build را اضافه کنید
    return jsonify({
        "status": "success",
        "message": f"Building image from {dockerfile_path} with tag {tag}",
        "note": "This endpoint needs implementation based on your requirements"
    })

# ============================================================================
# Routes for System Info
# ============================================================================

@docker_bp.route("/system", methods=["GET"])
@handle_docker_errors
@cache.cached(timeout=30)  # کش برای 30 ثانیه
def get_docker_system_info():
    """دریافت اطلاعات سیستم Docker"""
    info = docker_client.info()
    disk_usage = docker_client.df()
    
    layers_size = disk_usage.get('LayersSize', 0)
    
    return jsonify({
        "status": "success",
        "images_count": info['Images'],
        "containers_count": info['Containers'],
        "running_containers": info['ContainersRunning'],
        "stopped_containers": info['ContainersStopped'],
        "paused_containers": info['ContainersPaused'],
        "disk_usage": format_size(layers_size),
        "system_info": {
            "docker_version": info['ServerVersion'],
            "os": info['OperatingSystem'],
            "architecture": info['Architecture'],
            "kernel_version": info['KernelVersion'],
            "cpus": info['NCPU'],
            "memory": format_size(info['MemTotal']),
            "storage_driver": info.get('Driver', 'N/A')
        }
    })

@docker_bp.route("/ping", methods=["GET"])
@handle_docker_errors
def docker_ping():
    """بررسی وضعیت اتصال به Docker"""
    docker_client.ping()
    return jsonify({
        "status": "success",
        "message": "Docker is running and accessible"
    })

# ============================================================================
# Routes for Docker Networks
# ============================================================================

@docker_bp.route("/networks", methods=["GET"])
@handle_docker_errors
def get_docker_networks():
    """دریافت لیست شبکه‌های Docker"""
    networks = docker_client.networks.list()
    
    networks_list = []
    for network in networks:
        networks_list.append({
            "id": network.short_id,
            "name": network.name,
            "driver": network.attrs.get('Driver', 'bridge'),
            "scope": network.attrs.get('Scope', 'local'),
            "created": parse_datetime(network.attrs.get('Created')),
            "labels": network.attrs.get('Labels', {}),
            "containers": len(network.attrs.get('Containers', {})),
            "internal": network.attrs.get('Internal', False),
            "attachable": network.attrs.get('Attachable', False),
            "ipam": network.attrs.get('IPAM', {})
        })
    
    networks_list.sort(key=lambda x: x["name"])
    
    page, per_page = get_pagination_params(request)
    paginated_networks, total, total_pages = paginate(networks_list, page, per_page)
    
    return jsonify({
        "status": "success",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "count": len(networks_list),
        "networks": paginated_networks
    })

@docker_bp.route("/networks/<network_id>", methods=["GET"])
@handle_docker_errors
def get_docker_network_details(network_id):
    """دریافت جزئیات یک شبکه خاص"""
    network = docker_client.networks.get(network_id)
    
    return jsonify({
        "status": "success",
        "network": {
            "id": network.id,
            "name": network.name,
            "attrs": network.attrs
        }
    })

@docker_bp.route("/networks/create", methods=["POST"])
@handle_docker_errors
def create_docker_network():
    """ایجاد شبکه جدید"""
    data = request.json
    name = data.get("name")
    
    if not name:
        return jsonify({
            "status": "error",
            "message": "Network name is required"
        }), 400
    
    driver = data.get("driver", "bridge")
    internal = data.get("internal", False)
    attachable = data.get("attachable", True)
    labels = data.get("labels", {})
    
    network = docker_client.networks.create(
        name=name,
        driver=driver,
        internal=internal,
        attachable=attachable,
        labels=labels
    )
    
    logger.info(f"Network '{name}' created successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Network '{name}' created successfully",
        "network_id": network.id,
        "name": network.name
    })

@docker_bp.route("/networks/<network_id>/remove", methods=["POST"])
@handle_docker_errors
def remove_docker_network(network_id):
    """حذف یک شبکه"""
    network = docker_client.networks.get(network_id)
    network_name = network.name
    
    # بررسی اینکه شبکه خالی باشد
    if network.attrs.get('Containers'):
        return jsonify({
            "status": "error",
            "message": f"Cannot remove network '{network_name}' because it has connected containers"
        }), 400
    
    network.remove()
    logger.info(f"Network '{network_name}' removed successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Network '{network_name}' removed successfully"
    })

@docker_bp.route("/networks/prune", methods=["POST"])
@handle_docker_errors
def prune_docker_networks():
    """حذف شبکه‌های بدون استفاده"""
    result = docker_client.networks.prune()
    
    deleted_count = len(result.get('NetworksDeleted', []))
    logger.info(f"Pruned {deleted_count} unused networks")
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "space_reclaimed": result.get('SpaceReclaimed', 0),
        "details": result
    })

@docker_bp.route("/networks/<network_id>/containers", methods=["GET"])
@handle_docker_errors
def get_network_containers(network_id):
    """دریافت لیست کانتینرهای متصل به شبکه"""
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

# ============================================================================
# Routes for Docker Volumes
# ============================================================================

@docker_bp.route("/volumes", methods=["GET"])
@handle_docker_errors
def get_docker_volumes():
    """دریافت لیست ولوم‌های Docker"""
    volumes = docker_client.volumes.list()
    
    volumes_list = []
    for volume in volumes:
        volume_data = {
            "id": volume.id,
            "name": volume.name,
            "driver": volume.attrs.get('Driver', 'local'),
            "mountpoint": volume.attrs.get('Mountpoint', ''),
            "created": parse_datetime(volume.attrs.get('CreatedAt')),
            "labels": volume.attrs.get('Labels', {}),
            "scope": volume.attrs.get('Scope', 'local'),
            "options": volume.attrs.get('Options', {}),
            "usage_data": volume.attrs.get('UsageData', {})
        }
        volumes_list.append(volume_data)
    
    volumes_list.sort(key=lambda x: x["name"])
    
    page, per_page = get_pagination_params(request)
    paginated_volumes, total, total_pages = paginate(volumes_list, page, per_page)
    
    return jsonify({
        "status": "success",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "count": len(volumes_list),
        "volumes": paginated_volumes
    })

@docker_bp.route("/volumes/<volume_name>", methods=["GET"])
@handle_docker_errors
def get_docker_volume_details(volume_name):
    """دریافت جزئیات یک ولوم خاص"""
    volume = docker_client.volumes.get(volume_name)
    
    return jsonify({
        "status": "success",
        "volume": {
            "name": volume.name,
            "attrs": volume.attrs
        }
    })

@docker_bp.route("/volumes/create", methods=["POST"])
@handle_docker_errors
def create_docker_volume():
    """ایجاد ولوم جدید"""
    data = request.json
    name = data.get("name")
    
    if not name:
        return jsonify({
            "status": "error",
            "message": "Volume name is required"
        }), 400
    
    driver = data.get("driver", "local")
    driver_opts = data.get("driver_opts", {})
    labels = data.get("labels", {})
    
    volume = docker_client.volumes.create(
        name=name,
        driver=driver,
        driver_opts=driver_opts,
        labels=labels
    )
    
    logger.info(f"Volume '{name}' created successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Volume '{name}' created successfully",
        "volume_name": volume.name,
        "driver": volume.attrs.get('Driver', 'local')
    })

@docker_bp.route("/volumes/<volume_name>/remove", methods=["POST"])
@handle_docker_errors
def remove_docker_volume(volume_name):
    """حذف یک ولوم"""
    volume = docker_client.volumes.get(volume_name)
    volume.remove()
    
    logger.info(f"Volume '{volume_name}' removed successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Volume '{volume_name}' removed successfully"
    })

@docker_bp.route("/volumes/prune", methods=["POST"])
@handle_docker_errors
def prune_docker_volumes():
    """حذف ولوم‌های بدون استفاده"""
    result = docker_client.volumes.prune()
    
    deleted_count = len(result.get('VolumesDeleted', []))
    space_reclaimed = result.get('SpaceReclaimed', 0)
    
    logger.info(f"Pruned {deleted_count} volumes, reclaimed {format_size(space_reclaimed)}")
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "space_reclaimed": format_size(space_reclaimed),
        "space_reclaimed_bytes": space_reclaimed,
        "details": result
    })

@docker_bp.route("/volumes/<volume_name>/inspect", methods=["GET"])
@handle_docker_errors
def inspect_docker_volume(volume_name):
    """بررسی محتوای یک ولوم (فهرست فایل‌ها)"""
    volume = docker_client.volumes.get(volume_name)
    mountpoint = volume.attrs.get('Mountpoint', '')
    
    if not mountpoint:
        return jsonify({
            "status": "error",
            "message": "Mountpoint not found for this volume"
        }), 404
    
    try:
        result = subprocess.run(
            ['ls', '-la', mountpoint],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        files_list = []
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 9:
                        file_info = {
                            "permissions": parts[0],
                            "links": int(parts[1]),
                            "owner": parts[2],
                            "group": parts[3],
                            "size": int(parts[4]) if parts[4].isdigit() else parts[4],
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

@docker_bp.route("/volumes/stats", methods=["GET"])
@handle_docker_errors
@cache.cached(timeout=60)
def get_volumes_stats():
    """دریافت آمار ولوم‌ها"""
    volumes = docker_client.volumes.list()
    
    total_volumes = len(volumes)
    local_driver = sum(1 for v in volumes if v.attrs.get('Driver') == 'local')
    other_drivers = total_volumes - local_driver
    labeled_volumes = sum(1 for v in volumes if v.attrs.get('Labels'))
    
    return jsonify({
        "status": "success",
        "total_volumes": total_volumes,
        "local_driver": local_driver,
        "other_drivers": other_drivers,
        "labeled_volumes": labeled_volumes
    })

# ============================================================================
# Routes for Docker Containers
# ============================================================================

@docker_bp.route("/containers", methods=["GET"])
@handle_docker_errors
def get_docker_containers():
    """دریافت لیست کانتینرهای Docker"""
    containers = docker_client.containers.list(all=True)
    
    containers_list = []
    for container in containers:
        container_attrs = container.attrs
        
        # گرفتن اطلاعات شبکه
        network_settings = container_attrs.get('NetworkSettings', {})
        networks = network_settings.get('Networks', {})
        
        # گرفتن نام تصویر
        image_name = container_attrs.get('Config', {}).get('Image', '')
        
        # گرفتن دستور اجرا
        command = container_attrs.get('Config', {}).get('Cmd', [])
        command_str = ' '.join(command) if isinstance(command, list) else str(command)
        
        # گرفتن وضعیت health
        state = container_attrs.get('State', {})
        health_status = ""
        if state.get('Health'):
            health_status = state['Health'].get('Status', '')
        
        container_data = {
            "id": container.short_id,
            "full_id": container.id,
            "name": container.name.strip('/'),
            "image": image_name,
            "image_id": container_attrs.get('Image', '').split(':')[1][:12] if ':' in container_attrs.get('Image', '') else '',
            "status": container.status,
            "state": state.get('Status', 'unknown'),
            "created": parse_datetime(container_attrs.get('Created')),
            "ports": container_attrs.get('NetworkSettings', {}).get('Ports', {}),
            "networks": list(networks.keys()),
            "command": command_str[:100] + ('...' if len(command_str) > 100 else ''),
            "labels": container_attrs.get('Config', {}).get('Labels', {}),
            "restart_policy": container_attrs.get('HostConfig', {}).get('RestartPolicy', {}),
            "mounts": container_attrs.get('Mounts', []),
            "health": health_status,
            "exit_code": state.get('ExitCode', 0)
        }
        containers_list.append(container_data)
    
    # مرتب کردن و صفحه‌بندی
    containers_list.sort(key=lambda x: x["created"], reverse=True)
    
    page, per_page = get_pagination_params(request)
    paginated_containers, total, total_pages = paginate(containers_list, page, per_page)
    
    return jsonify({
        "status": "success",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "count": len(containers_list),
        "containers": paginated_containers
    })

@docker_bp.route("/containers/<container_id>", methods=["GET"])
@handle_docker_errors
def get_docker_container_details(container_id):
    """دریافت جزئیات یک کانتینر خاص"""
    container = docker_client.containers.get(container_id)
    
    return jsonify({
        "status": "success",
        "container": {
            "id": container.id,
            "name": container.name,
            "attrs": container.attrs
        }
    })

@docker_bp.route("/containers/<container_id>/start", methods=["POST"])
@handle_docker_errors
def start_docker_container(container_id):
    """شروع یک کانتینر"""
    container = docker_client.containers.get(container_id)
    container.start()
    
    logger.info(f"Container {container.name} started successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Container {container.name} started successfully"
    })

@docker_bp.route("/containers/<container_id>/stop", methods=["POST"])
@handle_docker_errors
def stop_docker_container(container_id):
    """توقف یک کانتینر"""
    container = docker_client.containers.get(container_id)
    container.stop()
    
    logger.info(f"Container {container.name} stopped successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Container {container.name} stopped successfully"
    })

@docker_bp.route("/containers/<container_id>/restart", methods=["POST"])
@handle_docker_errors
def restart_docker_container(container_id):
    """راه‌اندازی مجدد یک کانتینر"""
    container = docker_client.containers.get(container_id)
    container.restart()
    
    logger.info(f"Container {container.name} restarted successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Container {container.name} restarted successfully"
    })

@docker_bp.route("/containers/<container_id>/pause", methods=["POST"])
@handle_docker_errors
def pause_docker_container(container_id):
    """مکث یک کانتینر"""
    container = docker_client.containers.get(container_id)
    container.pause()
    
    logger.info(f"Container {container.name} paused successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Container {container.name} paused successfully"
    })

@docker_bp.route("/containers/<container_id>/unpause", methods=["POST"])
@handle_docker_errors
def unpause_docker_container(container_id):
    """ادامه دادن یک کانتینر مکث شده"""
    container = docker_client.containers.get(container_id)
    container.unpause()
    
    logger.info(f"Container {container.name} unpaused successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Container {container.name} unpaused successfully"
    })

@docker_bp.route("/containers/<container_id>/remove", methods=["POST"])
@handle_docker_errors
def remove_docker_container(container_id):
    """حذف یک کانتینر"""
    data = request.json or {}
    force = data.get("force", False)
    v = data.get("v", False)
    
    container = docker_client.containers.get(container_id)
    container_name = container.name
    
    # توقف کانتینر اگر در حال اجراست
    if container.status == 'running' and not force:
        return jsonify({
            "status": "error",
            "message": f"Cannot remove running container {container_name}. Stop it first or use force."
        }), 400
    
    container.remove(force=force, v=v)
    logger.info(f"Container {container_name} removed successfully")
    
    return jsonify({
        "status": "success",
        "message": f"Container {container_name} removed successfully"
    })

@docker_bp.route("/containers/<container_id>/logs", methods=["GET"])
@handle_docker_errors
def get_container_logs(container_id):
    """دریافت لاگ‌های یک کانتینر"""
    container = docker_client.containers.get(container_id)
    
    # دریافت پارامترها
    tail = request.args.get('tail', '100')
    since = request.args.get('since')
    until = request.args.get('until')
    follow = request.args.get('follow', 'false').lower() == 'true'
    timestamps = request.args.get('timestamps', 'false').lower() == 'true'
    
    # دریافت لاگ‌ها
    logs = container.logs(
        tail=tail,
        since=since,
        until=until,
        follow=follow,
        stdout=True,
        stderr=True,
        timestamps=timestamps
    )
    
    logs_str = logs.decode('utf-8', errors='replace')
    
    return jsonify({
        "status": "success",
        "container": container.name,
        "logs": logs_str,
        "lines_count": len(logs_str.split('\n'))
    })

@docker_bp.route("/containers/<container_id>/stats", methods=["GET"])
@handle_docker_errors
def get_container_stats(container_id):
    """دریافت آمار مصرف منابع یک کانتینر"""
    container = docker_client.containers.get(container_id)
    stats = container.stats(stream=False)
    
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

@docker_bp.route("/containers/<container_id>/exec", methods=["POST"])
@handle_docker_errors
def exec_container_command(container_id):
    """اجرای دستور در یک کانتینر"""
    data = request.json
    command = data.get("command")
    
    if not command:
        return jsonify({
            "status": "error",
            "message": "Command is required"
        }), 400
    
    container = docker_client.containers.get(container_id)
    
    exec_result = container.exec_run(
        cmd=command,
        stdout=True,
        stderr=True,
        stdin=False,
        tty=False
    )
    
    exit_code = exec_result.exit_code
    output = exec_result.output.decode('utf-8', errors='replace')
    
    logger.info(f"Executed command '{command}' in container {container.name}, exit code: {exit_code}")
    
    return jsonify({
        "status": "success",
        "container": container.name,
        "command": command,
        "exit_code": exit_code,
        "output": output
    })

@docker_bp.route("/containers/create", methods=["POST"])
@handle_docker_errors
def create_docker_container():
    """ایجاد کانتینر جدید"""
    data = request.json
    image = data.get("image")
    
    if not image:
        return jsonify({
            "status": "error",
            "message": "Image name is required"
        }), 400
    
    name = data.get("name")
    command = data.get("command")
    ports = data.get("ports", {})
    volumes = data.get("volumes", {})
    environment = data.get("environment", {})
    network = data.get("network")
    restart_policy = data.get("restart_policy", {"Name": "unless-stopped"})
    
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
    
    logger.info(f"Container {container.name} created successfully from image {image}")
    
    return jsonify({
        "status": "success",
        "message": "Container created successfully",
        "container_id": container.id,
        "name": container.name
    })

@docker_bp.route("/containers/prune", methods=["POST"])
@handle_docker_errors
def prune_docker_containers():
    """حذف کانتینرهای متوقف شده"""
    result = docker_client.containers.prune()
    
    deleted_count = len(result.get('ContainersDeleted', []))
    space_reclaimed = result.get('SpaceReclaimed', 0)
    
    logger.info(f"Pruned {deleted_count} stopped containers, reclaimed {format_size(space_reclaimed)}")
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "space_reclaimed": format_size(space_reclaimed),
        "space_reclaimed_bytes": space_reclaimed,
        "details": result
    })

@docker_bp.route("/containers/stats/all", methods=["GET"])
@handle_docker_errors
@cache.cached(timeout=30)
def get_all_containers_stats():
    """دریافت آمار تمام کانتینرها"""
    containers = docker_client.containers.list(all=True)
    
    stats_summary = {
        "total": len(containers),
        "running": sum(1 for c in containers if c.status == 'running'),
        "stopped": sum(1 for c in containers if c.status in ['exited', 'stopped']),
        "paused": sum(1 for c in containers if c.status == 'paused'),
        "restarting": sum(1 for c in containers if c.status == 'restarting'),
        "images": len(set(c.attrs['Config']['Image'] for c in containers))
    }
    
    return jsonify({
        "status": "success",
        "stats": stats_summary
    })

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
# Health Check Endpoint
# ============================================================================

@docker_bp.route("/health", methods=["GET"])
def docker_health():
    """بررسی سلامت سرویس Docker"""
    try:
        if not DOCKER_AVAILABLE:
            return jsonify({
                "status": "unhealthy",
                "message": "Docker client not initialized",
                "timestamp": datetime.now().isoformat()
            }), 503
        
        # تست اتصال به Docker
        docker_client.ping()
        
        # بررسی وضعیت کلی
        info = docker_client.info()
        
        return jsonify({
            "status": "healthy",
            "message": "Docker is running and accessible",
            "version": info.get('ServerVersion', 'unknown'),
            "containers": {
                "total": info.get('Containers', 0),
                "running": info.get('ContainersRunning', 0),
                "paused": info.get('ContainersPaused', 0),
                "stopped": info.get('ContainersStopped', 0)
            },
            "images": info.get('Images', 0),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "message": f"Docker health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 503