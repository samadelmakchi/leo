"""
ماژول مدیریت System
"""

import psutil
import platform
import socket
import os
import json
from datetime import datetime

@docker_bp.route("/system/info", methods=["GET"])
def get_system_info():
    """دریافت اطلاعات کامل سیستم"""
    try:
        # اطلاعات پایه
        info = {
            "timestamp": datetime.now().isoformat(),
            "system": {}
        }
        
        # ============ سیستم عامل ============
        system_info = {
            "os": {
                "name": platform.system(),
                "version": platform.version(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "hostname": socket.gethostname(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime": int(time.time() - psutil.boot_time())
        }
        
        # ============ CPU ============
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "usage": psutil.cpu_percent(interval=1),
            "per_cpu_usage": psutil.cpu_percent(interval=1, percpu=True),
            "frequency": {
                "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                "min": psutil.cpu_freq().min if psutil.cpu_freq() else None,
                "max": psutil.cpu_freq().max if psutil.cpu_freq() else None
            },
            "stats": psutil.cpu_stats()._asdict() if hasattr(psutil, 'cpu_stats') else {},
            "times": psutil.cpu_times()._asdict()
        }
        
        # ============ Memory ============
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        memory_info = {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "free": mem.free,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_free": swap.free,
            "swap_percent": swap.percent
        }
        
        # ============ Disk ============
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except:
                continue
        
        # ============ Network ============
        net_info = {
            "interfaces": {},
            "connections": []
        }
        
        # اطلاعات اینترفیس‌ها
        for interface, addrs in psutil.net_if_addrs().items():
            net_info["interfaces"][interface] = []
            for addr in addrs:
                net_info["interfaces"][interface].append({
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                })
        
        # آمار شبکه
        net_io = psutil.net_io_counters()
        net_info["io_counters"] = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
            "dropin": net_io.dropin,
            "dropout": net_io.dropout
        }
        
        # ============ Processes ============
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # ============ جمع‌آوری همه اطلاعات ============
        info["system"] = system_info
        info["cpu"] = cpu_info
        info["memory"] = memory_info
        info["disk"] = disk_info
        info["network"] = net_info
        info["processes"] = processes[:50]  # فقط 50 پردازش اول
        info["load_average"] = os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        
        # اطلاعات Docker
        try:
            docker_info = docker_client.info()
            info["docker"] = {
                "version": docker_info.get('ServerVersion', 'N/A'),
                "containers": docker_info.get('Containers', 0),
                "running": docker_info.get('ContainersRunning', 0),
                "paused": docker_info.get('ContainersPaused', 0),
                "stopped": docker_info.get('ContainersStopped', 0),
                "images": docker_info.get('Images', 0),
                "driver": docker_info.get('Driver', 'N/A'),
                "storage_driver": docker_info.get('DriverStatus', [])
            }
        except:
            info["docker"] = {"error": "Docker not available"}
        
        return jsonify({
            "status": "success",
            "data": info
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@docker_bp.route("/system/resources", methods=["GET"])
def get_system_resources():
    """دریافت اطلاعات منابع مصرفی برای نمودارها"""
    try:
        # اطلاعات لحظه‌ای
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu_percent,
            "memory": {
                "percent": mem.percent,
                "used": mem.used,
                "available": mem.available
            },
            "disk": {
                "percent": disk.percent,
                "used": disk.used,
                "free": disk.free
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            },
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
            "process_count": len(list(psutil.process_iter()))
        }
        
        return jsonify({
            "status": "success",
            "data": data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500