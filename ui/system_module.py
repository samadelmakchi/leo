"""
ماژول مدیریت System - نسخه بهینه‌شده
"""

import psutil
import platform
import socket
import os
import json
import time
from datetime import datetime
from functools import wraps
import logging
from flask import Blueprint, jsonify, request
from app import cache
from utils import (
    success_response, 
    error_response, 
    format_size,
    get_current_timestamp,
    log_request_info
)

logger = logging.getLogger(__name__)

# ایجاد Blueprint برای System
system_bp = Blueprint('system', __name__, url_prefix='/api/system')

# ============================================================================
# Decorators
# ============================================================================

def handle_system_errors(func):
    """دکوراتور برای مدیریت خطاهای System"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            log_request_info()
            return func(*args, **kwargs)
        except psutil.AccessDenied as e:
            logger.error(f"Access denied in {func.__name__}: {e}")
            return error_response(
                message="دسترسی به اطلاعات سیستم محدود شده است",
                status_code=403,
                details="برنامه نیاز به دسترسی بالاتر دارد"
            )
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return error_response(
                message="خطا در دریافت اطلاعات سیستم",
                status_code=500,
                details=str(e)[:200]
            )
    return wrapper

# ============================================================================
# Helper Functions
# ============================================================================

def get_system_uptime():
    """دریافت زمان uptime سیستم"""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = time.time() - psutil.boot_time()
    
    # تبدیل به فرمت خوانا
    days = int(uptime_seconds // (24 * 3600))
    hours = int((uptime_seconds % (24 * 3600)) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    return {
        "seconds": int(uptime_seconds),
        "formatted": f"{days} روز, {hours} ساعت, {minutes} دقیقه",
        "boot_time": boot_time.isoformat()
    }

def get_cpu_info():
    """دریافت اطلاعات CPU"""
    try:
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()
        cpu_times = psutil.cpu_times()
        
        return {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=0.5),
            "per_cpu_usage": psutil.cpu_percent(interval=0.5, percpu=True),
            "frequency": {
                "current": round(cpu_freq.current, 2) if cpu_freq else None,
                "min": round(cpu_freq.min, 2) if cpu_freq else None,
                "max": round(cpu_freq.max, 2) if cpu_freq else None
            },
            "stats": {
                "ctx_switches": cpu_stats.ctx_switches,
                "interrupts": cpu_stats.interrupts,
                "soft_interrupts": cpu_stats.soft_interrupts,
                "syscalls": cpu_stats.syscalls
            },
            "times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
                "iowait": getattr(cpu_times, 'iowait', 0)
            }
        }
    except Exception as e:
        logger.warning(f"Error getting CPU info: {e}")
        return {"error": str(e)}

def get_memory_info():
    """دریافت اطلاعات Memory"""
    try:
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()
        
        return {
            "virtual": {
                "total": virtual_mem.total,
                "available": virtual_mem.available,
                "used": virtual_mem.used,
                "free": virtual_mem.free,
                "percent": virtual_mem.percent,
                "cached": getattr(virtual_mem, 'cached', 0),
                "buffers": getattr(virtual_mem, 'buffers', 0),
                "shared": getattr(virtual_mem, 'shared', 0)
            },
            "swap": {
                "total": swap_mem.total,
                "used": swap_mem.used,
                "free": swap_mem.free,
                "percent": swap_mem.percent,
                "sin": swap_mem.sin,
                "sout": swap_mem.sout
            }
        }
    except Exception as e:
        logger.warning(f"Error getting memory info: {e}")
        return {"error": str(e)}

def get_disk_info():
    """دریافت اطلاعات Disk"""
    try:
        disk_info = []
        
        for partition in psutil.disk_partitions():
            try:
                if os.name == 'nt' and 'cdrom' in partition.opts:
                    continue  # Skip CD-ROM drives on Windows
                
                usage = psutil.disk_usage(partition.mountpoint)
                
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "total": usage.total,
                    "total_formatted": format_size(usage.total),
                    "used": usage.used,
                    "used_formatted": format_size(usage.used),
                    "free": usage.free,
                    "free_formatted": format_size(usage.free),
                    "percent": usage.percent,
                    "read_only": 'ro' in partition.opts
                })
            except (PermissionError, FileNotFoundError) as e:
                logger.debug(f"Skipping partition {partition.mountpoint}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error getting disk usage for {partition.mountpoint}: {e}")
                continue
        
        # اطلاعات IO
        disk_io = psutil.disk_io_counters()
        io_info = {
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_time": disk_io.read_time,
            "write_time": disk_io.write_time
        } if disk_io else {}
        
        return {
            "partitions": disk_info,
            "io_counters": io_info,
            "total_partitions": len(disk_info)
        }
    except Exception as e:
        logger.warning(f"Error getting disk info: {e}")
        return {"error": str(e)}

def get_network_info():
    """دریافت اطلاعات Network"""
    try:
        network_info = {
            "interfaces": {},
            "connections": [],
            "io_counters": {}
        }
        
        # اطلاعات اینترفیس‌ها
        for interface, addrs in psutil.net_if_addrs().items():
            interface_addrs = []
            for addr in addrs:
                interface_addrs.append({
                    "family": str(addr.family).replace('AddressFamily.', ''),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast,
                    "ptp": addr.ptp
                })
            
            network_info["interfaces"][interface] = interface_addrs
        
        # آمار IO شبکه
        net_io = psutil.net_io_counters()
        if net_io:
            network_info["io_counters"] = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_sent_formatted": format_size(net_io.bytes_sent),
                "bytes_recv": net_io.bytes_recv,
                "bytes_recv_formatted": format_size(net_io.bytes_recv),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
        
        # اتصالات شبکه
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections[:20]:  # فقط 20 اتصال اول
                network_info["connections"].append({
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                })
        except (psutil.AccessDenied, AttributeError):
            pass  # دسترسی محدود
        
        return network_info
    except Exception as e:
        logger.warning(f"Error getting network info: {e}")
        return {"error": str(e)}

def get_processes_info(limit=50):
    """دریافت اطلاعات Processes"""
    try:
        processes = []
        fields = ['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 
                 'status', 'create_time', 'memory_info', 'cpu_times']
        
        for proc in psutil.process_iter(fields):
            try:
                info = proc.info
                
                # فرمت‌بندی بهتر
                process_info = {
                    "pid": info['pid'],
                    "name": info['name'],
                    "username": info['username'] or 'N/A',
                    "cpu_percent": round(info['cpu_percent'], 1),
                    "memory_percent": round(info['memory_percent'], 1),
                    "status": info['status'],
                    "create_time": datetime.fromtimestamp(info['create_time']).isoformat() if info['create_time'] else None,
                    "memory_rss": info['memory_info'].rss if info.get('memory_info') else 0,
                    "memory_vms": info['memory_info'].vms if info.get('memory_info') else 0,
                    "cpu_times_user": info['cpu_times'].user if info.get('cpu_times') else 0,
                    "cpu_times_system": info['cpu_times'].system if info.get('cpu_times') else 0
                }
                
                processes.append(process_info)
                
                if len(processes) >= limit:
                    break
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue
        
        return {
            "processes": processes,
            "total": len(processes),
            "total_all": len(list(psutil.pids()))
        }
    except Exception as e:
        logger.warning(f"Error getting processes info: {e}")
        return {"error": str(e)}

def get_docker_info():
    """دریافت اطلاعات Docker"""
    try:
        from docker_module import docker_client, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE:
            return {"status": "unavailable", "message": "Docker not available"}
        
        info = docker_client.info()
        version = docker_client.version()
        
        return {
            "status": "available",
            "version": info.get('ServerVersion', 'N/A'),
            "api_version": version.get('ApiVersion', 'N/A'),
            "containers": {
                "total": info.get('Containers', 0),
                "running": info.get('ContainersRunning', 0),
                "paused": info.get('ContainersPaused', 0),
                "stopped": info.get('ContainersStopped', 0)
            },
            "images": info.get('Images', 0),
            "system": {
                "os": info.get('OperatingSystem', 'N/A'),
                "architecture": info.get('Architecture', 'N/A'),
                "kernel": info.get('KernelVersion', 'N/A'),
                "cpus": info.get('NCPU', 0),
                "memory": format_size(info.get('MemTotal', 0)),
                "driver": info.get('Driver', 'N/A'),
                "storage_driver": info.get('DriverStatus', [])
            }
        }
    except ImportError:
        return {"status": "module_not_found", "message": "Docker module not available"}
    except Exception as e:
        logger.warning(f"Error getting Docker info: {e}")
        return {"status": "error", "message": str(e)}

# ============================================================================
# Routes
# ============================================================================

@system_bp.route("/info", methods=["GET"])
@handle_system_errors
@cache.cached(timeout=30)  # کش برای 30 ثانیه
def get_system_info():
    """دریافت اطلاعات کامل سیستم"""
    data = {
        "timestamp": get_current_timestamp(),
        "system": {
            "os": {
                "name": platform.system(),
                "version": platform.version(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            },
            "hostname": socket.gethostname(),
            "uptime": get_system_uptime(),
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        },
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "processes": get_processes_info(limit=30),
        "docker": get_docker_info()
    }
    
    # فرمت‌بندی سایزها برای خوانایی بهتر
    if "memory" in data and "virtual" in data["memory"]:
        mem_virtual = data["memory"]["virtual"]
        mem_virtual["total_formatted"] = format_size(mem_virtual["total"])
        mem_virtual["available_formatted"] = format_size(mem_virtual["available"])
        mem_virtual["used_formatted"] = format_size(mem_virtual["used"])
        mem_virtual["free_formatted"] = format_size(mem_virtual["free"])
    
    logger.info("System info retrieved successfully")
    
    return success_response(
        data=data,
        message="اطلاعات سیستم با موفقیت دریافت شد"
    )

@system_bp.route("/resources", methods=["GET"])
@handle_system_errors
@cache.cached(timeout=5)  # کش کوتاه برای اطلاعات لحظه‌ای
def get_system_resources():
    """دریافت اطلاعات منابع مصرفی برای نمودارها"""
    # اطلاعات لحظه‌ای
    cpu_percent = psutil.cpu_percent(interval=0.3)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/') if os.name != 'nt' else psutil.disk_usage('C:\\')
    net_io = psutil.net_io_counters()
    
    data = {
        "timestamp": get_current_timestamp(),
        "cpu": {
            "percent": cpu_percent,
            "per_cpu": psutil.cpu_percent(interval=0.3, percpu=True)
        },
        "memory": {
            "percent": memory.percent,
            "used": memory.used,
            "used_formatted": format_size(memory.used),
            "available": memory.available,
            "available_formatted": format_size(memory.available),
            "total": memory.total,
            "total_formatted": format_size(memory.total)
        },
        "disk": {
            "percent": disk.percent,
            "used": disk.used,
            "used_formatted": format_size(disk.used),
            "free": disk.free,
            "free_formatted": format_size(disk.free),
            "total": disk.total,
            "total_formatted": format_size(disk.total)
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_sent_formatted": format_size(net_io.bytes_sent),
            "bytes_recv": net_io.bytes_recv,
            "bytes_recv_formatted": format_size(net_io.bytes_recv),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        },
        "processes": {
            "count": len(psutil.pids()),
            "running": len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'running'])
        }
    }
    
    return success_response(
        data=data,
        message="اطلاعات منابع سیستم دریافت شد"
    )

@system_bp.route("/health", methods=["GET"])
@handle_system_errors
def get_system_health():
    """بررسی سلامت سیستم"""
    health_status = {
        "timestamp": get_current_timestamp(),
        "status": "healthy",
        "checks": {}
    }
    
    # بررسی CPU
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        health_status["checks"]["cpu"] = {
            "status": "healthy" if cpu_percent < 90 else "warning",
            "usage_percent": cpu_percent,
            "threshold": 90
        }
    except Exception as e:
        health_status["checks"]["cpu"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Memory
    try:
        memory = psutil.virtual_memory()
        health_status["checks"]["memory"] = {
            "status": "healthy" if memory.percent < 85 else "warning",
            "usage_percent": memory.percent,
            "available": format_size(memory.available),
            "threshold": 85
        }
    except Exception as e:
        health_status["checks"]["memory"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Disk
    try:
        disk = psutil.disk_usage('/')
        health_status["checks"]["disk"] = {
            "status": "healthy" if disk.percent < 90 else "warning",
            "usage_percent": disk.percent,
            "free": format_size(disk.free),
            "threshold": 90
        }
    except Exception as e:
        health_status["checks"]["disk"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Load Average
    try:
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
            cores = psutil.cpu_count()
            health_status["checks"]["load"] = {
                "status": "healthy" if load_avg[0] < cores * 2 else "warning",
                "load_1min": load_avg[0],
                "load_5min": load_avg[1],
                "load_15min": load_avg[2],
                "cores": cores,
                "threshold": cores * 2
            }
    except Exception as e:
        health_status["checks"]["load"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Docker
    try:
        docker_info = get_docker_info()
        health_status["checks"]["docker"] = {
            "status": "healthy" if docker_info.get("status") == "available" else "unhealthy",
            "info": docker_info
        }
    except Exception as e:
        health_status["checks"]["docker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # تعیین وضعیت کلی
    unhealthy_checks = [name for name, check in health_status["checks"].items() 
                       if check.get("status") == "unhealthy"]
    warning_checks = [name for name, check in health_status["checks"].items() 
                     if check.get("status") == "warning"]
    
    if unhealthy_checks:
        health_status["status"] = "unhealthy"
        health_status["unhealthy_checks"] = unhealthy_checks
    elif warning_checks:
        health_status["status"] = "warning"
        health_status["warning_checks"] = warning_checks
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return jsonify(health_status), status_code

@system_bp.route("/stats/history", methods=["GET"])
@handle_system_errors
def get_system_stats_history():
    """دریافت تاریخچه آمار سیستم (برای نمودارها)"""
    # این endpoint می‌تواند از دیتابیس یا فایل تاریخچه بخواند
    # فعلاً نمونه بازمی‌گرداند
    
    hours = request.args.get('hours', 24, type=int)
    hours = min(max(1, hours), 168)  # محدود به 1 تا 168 ساعت (1 هفته)
    
    # در اینجا می‌توانید از دیتابیس یا cache تاریخچه بخوانید
    sample_data = {
        "timestamp": get_current_timestamp(),
        "range_hours": hours,
        "data": {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        },
        "note": "این endpoint نیاز به پیاده‌سازی ذخیره‌سازی تاریخچه دارد"
    }
    
    return success_response(
        data=sample_data,
        message=f"تاریخچه {hours} ساعته سیستم"
    )

@system_bp.route("/processes/top", methods=["GET"])
@handle_system_errors
def get_top_processes():
    """دریافت پردازش‌های پر مصرف"""
    limit = request.args.get('limit', 10, type=int)
    limit = min(max(1, limit), 50)
    
    sort_by = request.args.get('sort_by', 'cpu')  # cpu, memory, pid
    
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                        'memory_info', 'username', 'status']):
            try:
                info = proc.info
                
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": round(info['cpu_percent'], 1),
                    "memory_percent": round(info['memory_percent'], 1),
                    "memory_rss": info['memory_info'].rss if info.get('memory_info') else 0,
                    "username": info['username'] or 'N/A',
                    "status": info['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # مرتب‌سازی
        if sort_by == 'cpu':
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        elif sort_by == 'memory':
            processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        elif sort_by == 'pid':
            processes.sort(key=lambda x: x['pid'])
        
        # محدود کردن تعداد
        top_processes = processes[:limit]
        
        return success_response(
            data={
                "processes": top_processes,
                "total": len(processes),
                "sort_by": sort_by,
                "limit": limit
            },
            message=f"{limit} پردازش پر مصرف سیستم"
        )
    except Exception as e:
        logger.error(f"Error getting top processes: {e}")
        return error_response(
            message="خطا در دریافت پردازش‌های پر مصرف",
            status_code=500
        )