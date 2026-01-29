"""
فایل اصلی Flask Application - نسخه بهینه‌شده
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import logging
from logging.handlers import RotatingFileHandler
import psutil
from config import config

# ایمپورت ماژول‌ها
from docker_module import docker_bp
from ansible_module import ansible_bp
from cron_module import cron_bp
from system_module import system_bp
from utils import (
    success_response, 
    error_response,
    get_current_timestamp,
    format_size
)

# ============================================================================
# Configuration
# ============================================================================

# تنظیمات برنامه
class Config:
    """کلاس تنظیمات برنامه"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    ENV = os.environ.get('FLASK_ENV', 'production')
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # Rate Limiting
    RATE_LIMIT_PER_DAY = int(os.environ.get('RATE_LIMIT_PER_DAY', 200))
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', 50))
    
    # Caching
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 10))
    
    # Application
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))

# ============================================================================
# Flask Application
# ============================================================================

app = Flask(__name__)
app.config.from_object(config)

# ============================================================================
# Logging Configuration
# ============================================================================

def setup_logging():
    """تنظیم سیستم logging"""
    # ایجاد پوشه logs
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # فرمت log
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Handler برای فایل اصلی
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=Config.LOG_MAX_SIZE,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
    file_handler.setFormatter(formatter)
    
    # Handler برای console (در حالت debug)
    if Config.DEBUG:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
    
    # Handler برای خطاها
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=Config.LOG_MAX_SIZE,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # تنظیم logging برای app
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # تنظیم log level برای کتابخانه‌ها
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('docker').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    app.logger.info("Logging system initialized successfully")

# ============================================================================
# CORS Configuration
# ============================================================================

CORS(app, resources={
    r"/api/*": {
        "origins": Config.CORS_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
        "expose_headers": ["Content-Range", "X-Total-Count"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# ============================================================================
# Rate Limiting
# ============================================================================

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[
        f"{Config.RATE_LIMIT_PER_DAY} per day",
        f"{Config.RATE_LIMIT_PER_HOUR} per hour"
    ],
    storage_uri="memory://",
    strategy="fixed-window",  # یا "moving-window"
    on_breach=lambda request_limit: app.logger.warning(
        f"Rate limit breached for {request_limit.key}: {request_limit.limit}"
    )
)

# معافیت‌های Rate Limiting
@limiter.request_filter
def ip_whitelist():
    """فیلتر IPهای وایت‌لیست"""
    whitelist_ips = ['127.0.0.1', '::1']
    return request.remote_addr in whitelist_ips

# ============================================================================
# Cache Configuration
# ============================================================================

if Config.CACHE_TYPE == 'redis':
    cache_config = {
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': Config.CACHE_REDIS_URL,
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_KEY_PREFIX': 'docker_management_'
    }
else:
    cache_config = {
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 1000
    }

cache = Cache(app, config=cache_config)

# ============================================================================
# Security Middleware
# ============================================================================

@app.after_request
def add_security_headers(response):
    """اضافه کردن هدرهای امنیتی به پاسخ‌ها"""
    security_headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
    
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response

@app.before_request
def log_request():
    """لاگ کردن درخواست‌ها"""
    if request.path.startswith('/api/'):
        app.logger.info(
            f"Request: {request.method} {request.path} - "
            f"IP: {request.remote_addr} - "
            f"User-Agent: {request.user_agent}"
        )

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """مدیریت خطای 404"""
    app.logger.warning(f"404 Not Found: {request.path}")
    return error_response(
        message="صفحه مورد نظر یافت نشد",
        status_code=404
    ), 404

@app.errorhandler(429)
def rate_limit_error(error):
    """مدیریت خطای Rate Limit"""
    app.logger.warning(f"429 Rate Limit: {request.remote_addr} - {request.path}")
    return error_response(
        message="تعداد درخواست‌های شما بیش از حد مجاز است",
        status_code=429,
        details="لطفاً بعداً تلاش کنید"
    ), 429

@app.errorhandler(500)
def internal_error(error):
    """مدیریت خطای 500"""
    app.logger.error(f"500 Internal Server Error: {error}")
    return error_response(
        message="خطای داخلی سرور",
        status_code=500,
        details="لطفاً بعداً تلاش کنید" if not Config.DEBUG else str(error)
    ), 500

@app.errorhandler(Exception)
def handle_exception(error):
    """مدیریت خطاهای عمومی"""
    app.logger.error(f"Unhandled exception: {error}", exc_info=True)
    return error_response(
        message="خطای غیرمنتظره",
        status_code=500,
        details=str(error) if Config.DEBUG else None
    ), 500

# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.route("/api/health", methods=["GET"])
@limiter.exempt
def health_check():
    """بررسی سلامت کامل سیستم"""
    health_status = {
        "status": "healthy",
        "timestamp": get_current_timestamp(),
        "uptime": int(datetime.now().timestamp() - psutil.boot_time()),
        "version": "1.0.0",
        "services": {}
    }
    
    # بررسی Docker
    try:
        from docker_module import DOCKER_AVAILABLE, docker_client
        if DOCKER_AVAILABLE:
            docker_client.ping()
            health_status["services"]["docker"] = {
                "status": "healthy",
                "version": docker_client.version()['Version'],
                "containers": len(docker_client.containers.list(all=True))
            }
        else:
            health_status["services"]["docker"] = {
                "status": "unavailable",
                "message": "Docker not available"
            }
    except Exception as e:
        app.logger.error(f"Docker health check failed: {e}")
        health_status["services"]["docker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Disk Space
    try:
        disk = psutil.disk_usage('/')
        health_status["services"]["disk"] = {
            "status": "healthy" if disk.percent < 90 else "warning",
            "usage_percent": round(disk.percent, 2),
            "total": format_size(disk.total),
            "used": format_size(disk.used),
            "free": format_size(disk.free),
            "threshold": 90
        }
    except Exception as e:
        app.logger.error(f"Disk health check failed: {e}")
        health_status["services"]["disk"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Memory
    try:
        memory = psutil.virtual_memory()
        health_status["services"]["memory"] = {
            "status": "healthy" if memory.percent < 85 else "warning",
            "usage_percent": round(memory.percent, 2),
            "total": format_size(memory.total),
            "available": format_size(memory.available),
            "threshold": 85
        }
    except Exception as e:
        app.logger.error(f"Memory health check failed: {e}")
        health_status["services"]["memory"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی CPU Load
    try:
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        cpu_count = psutil.cpu_count()
        health_status["services"]["cpu"] = {
            "status": "healthy" if load_avg[0] < cpu_count * 2 else "warning",
            "load_1min": round(load_avg[0], 2),
            "load_5min": round(load_avg[1], 2),
            "load_15min": round(load_avg[2], 2),
            "cores": cpu_count,
            "threshold": cpu_count * 2
        }
    except Exception as e:
        app.logger.error(f"CPU health check failed: {e}")
        health_status["services"]["cpu"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # بررسی Application Services
    health_status["services"]["application"] = {
        "status": "healthy",
        "debug": Config.DEBUG,
        "environment": Config.ENV,
        "cache_type": Config.CACHE_TYPE,
        "log_level": Config.LOG_LEVEL
    }
    
    # تعیین وضعیت کلی
    unhealthy_services = [
        name for name, info in health_status["services"].items() 
        if info.get("status") == "unhealthy"
    ]
    warning_services = [
        name for name, info in health_status["services"].items() 
        if info.get("status") == "warning"
    ]
    
    if unhealthy_services:
        health_status["status"] = "unhealthy"
        health_status["unhealthy_services"] = unhealthy_services
    elif warning_services:
        health_status["status"] = "warning"
        health_status["warning_services"] = warning_services
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return jsonify(health_status), status_code

@app.route("/api/health/liveness", methods=["GET"])
@limiter.exempt
def liveness_probe():
    """بررسی ساده برای liveness probe (Kubernetes)"""
    try:
        # بررسی ابتدایی که برنامه در حال اجراست
        return jsonify({
            "status": "ok",
            "timestamp": get_current_timestamp()
        }), 200
    except Exception as e:
        app.logger.error(f"Liveness probe failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 503

@app.route("/api/health/readiness", methods=["GET"])
@limiter.exempt
def readiness_probe():
    """بررسی readiness برای load balancer"""
    checks = {}
    
    # بررسی Docker
    try:
        from docker_module import DOCKER_AVAILABLE
        checks["docker"] = {
            "ready": DOCKER_AVAILABLE,
            "message": "Docker is available" if DOCKER_AVAILABLE else "Docker not available"
        }
    except Exception as e:
        checks["docker"] = {
            "ready": False,
            "error": str(e)
        }
    
    # بررسی Disk Space
    try:
        disk = psutil.disk_usage('/')
        checks["disk"] = {
            "ready": disk.percent < 95,
            "usage_percent": disk.percent,
            "message": "Disk space is sufficient" if disk.percent < 95 else "Disk space is low"
        }
    except Exception as e:
        checks["disk"] = {
            "ready": False,
            "error": str(e)
        }
    
    # بررسی Memory
    try:
        memory = psutil.virtual_memory()
        checks["memory"] = {
            "ready": memory.percent < 90,
            "usage_percent": memory.percent,
            "message": "Memory is sufficient" if memory.percent < 90 else "Memory is low"
        }
    except Exception as e:
        checks["memory"] = {
            "ready": False,
            "error": str(e)
        }
    
    # بررسی همه checks
    all_ready = all(check.get("ready", False) for check in checks.values())
    
    if all_ready:
        return jsonify({
            "status": "ready",
            "timestamp": get_current_timestamp(),
            "checks": checks
        }), 200
    else:
        failed_checks = [name for name, check in checks.items() if not check.get("ready", False)]
        return jsonify({
            "status": "not ready",
            "timestamp": get_current_timestamp(),
            "failed_checks": failed_checks,
            "checks": checks
        }), 503

@app.route("/api/health/metrics", methods=["GET"])
@limiter.exempt
def metrics_endpoint():
    """ارائه metrics برای Prometheus"""
    try:
        # جمع‌آوری metrics
        metrics = {
            "timestamp": get_current_timestamp(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids())
            },
            "application": {
                "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time()),
                "debug_mode": Config.DEBUG
            }
        }
        
        # افزودن metrics مربوط به ماژول‌ها
        try:
            from docker_module import DOCKER_AVAILABLE
            if DOCKER_AVAILABLE:
                from docker_module import docker_client
                metrics["docker"] = {
                    "available": True,
                    "container_count": len(docker_client.containers.list(all=True)),
                    "image_count": len(docker_client.images.list())
                }
            else:
                metrics["docker"] = {"available": False}
        except Exception as e:
            metrics["docker"] = {"available": False, "error": str(e)}
        
        return jsonify(metrics), 200
        
    except Exception as e:
        app.logger.error(f"Error collecting metrics: {e}")
        return error_response(
            message="خطا در جمع‌آوری metrics",
            status_code=500
        )

# ============================================================================
# Application Info Endpoint
# ============================================================================

@app.route("/api/info", methods=["GET"])
def api_info():
    """اطلاعات کلی برنامه"""
    info = {
        "name": "Docker Management System",
        "version": "1.0.0",
        "description": "سیستم مدیریت Docker، Ansible، Cron و Backup",
        "author": "Your Team",
        "license": "MIT",
        "timestamp": get_current_timestamp(),
        "environment": Config.ENV,
        "debug": Config.DEBUG,
        "endpoints": {
            "docker": "/api/docker",
            "ansible": "/api/ansible",
            "cron": "/api/cron",
            "system": "/api/system",
            "health": "/api/health",
            "metrics": "/api/health/metrics"
        },
        "features": [
            "مدیریت Docker Containers",
            "مدیریت Docker Images",
            "مدیریت Docker Networks",
            "مدیریت Docker Volumes",
            "مدیریت Ansible Inventory",
            "اجرای Ansible Playbooks",
            "مدیریت Cron Jobs",
            "مدیریت Backup‌ها",
            "مدیریت Log Files",
            "مانیتورینگ سیستم"
        ]
    }
    
    return success_response(
        data=info,
        message="اطلاعات برنامه"
    )

# ============================================================================
# Register Blueprints
# ============================================================================

# ثبت Blueprint ماژول‌ها
app.register_blueprint(docker_bp)
app.register_blueprint(ansible_bp)
app.register_blueprint(cron_bp)
app.register_blueprint(system_bp)

# تنظیم Rate Limiting برای Blueprint‌ها
limiter.limit("50 per hour")(docker_bp)
limiter.limit("30 per hour")(ansible_bp)
limiter.limit("20 per hour")(cron_bp)
limiter.limit("100 per hour")(system_bp)

# ============================================================================
# Frontend Routes
# ============================================================================

@app.route("/")
def index():
    """صفحه اصلی"""
    return render_template("index.html")

@app.route("/<path:path>")
def catch_all(path):
    """مدیریت مسیرهای frontend (برای SPA)"""
    if path.startswith('api/'):
        # مسیرهای API باید قبلاً مدیریت شده باشند
        return error_response(
            message="API endpoint not found",
            status_code=404
        ), 404
    
    # برای مسیرهای frontend، index.html را برگردان
    try:
        return render_template("index.html")
    except Exception as e:
        app.logger.error(f"Error rendering template for path {path}: {e}")
        return error_response(
            message="خطا در نمایش صفحه",
            status_code=500
        ), 500

@app.route("/section/<section_name>")
def get_section(section_name):
    """دریافت بخش مورد نظر"""
    valid_sections = [
        'dashboard', 'docker', 'containers', 'images', 
        'networks', 'volumes', 'ansible', 'inventory',
        'backup', 'logs', 'cron', 'system', 'settings'
    ]
    
    if section_name not in valid_sections:
        return f"<div class='alert alert-danger'>بخش {section_name} یافت نشد</div>", 404
    
    try:
        return render_template(f"sections/{section_name}.html")
    except Exception as e:
        app.logger.error(f"Error loading section {section_name}: {e}")
        return f"<div class='alert alert-danger'>خطا در بارگذاری بخش {section_name}</div>", 500

# ============================================================================
# Application Startup
# ============================================================================

@app.before_first_request
def initialize_app():
    """مقداردهی اولیه برنامه"""
    app.logger.info("Application is initializing...")
    
    # ایجاد پوشه‌های مورد نیاز
    required_dirs = ['logs', 'templates', 'static', 'backups', 'config']
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    # بررسی وجود فایل‌های ضروری
    required_files = {
        'config/inventory.yml': 'فایل inventory Ansible',
        'playbooks/main.yml': 'Playbook اصلی Ansible'
    }
    
    for file_path, description in required_files.items():
        if not Path(file_path).exists():
            app.logger.warning(f"{description} ({file_path}) not found")
    
    app.logger.info("Application initialized successfully")

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # تنظیم logging
    setup_logging()
    
    # لاگ اطلاعات شروع
    app.logger.info("=" * 50)
    app.logger.info("Starting Docker Management System")
    app.logger.info(f"Environment: {Config.ENV}")
    app.logger.info(f"Debug Mode: {Config.DEBUG}")
    app.logger.info(f"Host: {Config.HOST}")
    app.logger.info(f"Port: {Config.PORT}")
    app.logger.info(f"Log Level: {Config.LOG_LEVEL}")
    app.logger.info("=" * 50)
    
    # اجرای برنامه
    try:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
            threaded=True,
            use_reloader=Config.DEBUG
        )
    except Exception as e:
        app.logger.critical(f"Failed to start application: {e}")
        sys.exit(1)