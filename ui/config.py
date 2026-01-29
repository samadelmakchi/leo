"""
فایل مدیریت تنظیمات برنامه
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# بارگذاری فایل .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """کلاس اصلی تنظیمات"""
    
    # ========================================================================
    # Flask Configuration
    # ========================================================================
    
    # Basic
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    
    # Server
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', '5000'))
    
    # Application
    APP_NAME = os.getenv('APP_NAME', 'Docker Management System')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    
    # ========================================================================
    # Security Configuration
    # ========================================================================
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS_METHODS = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE').split(',')
    CORS_ALLOW_HEADERS = os.getenv('CORS_ALLOW_HEADERS', 'Content-Type,Authorization').split(',')
    CORS_EXPOSE_HEADERS = os.getenv('CORS_EXPOSE_HEADERS', '').split(',')
    CORS_SUPPORTS_CREDENTIALS = os.getenv('CORS_SUPPORTS_CREDENTIALS', 'false').lower() == 'true'
    CORS_MAX_AGE = int(os.getenv('CORS_MAX_AGE', '3600'))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_PER_DAY = int(os.getenv('RATE_LIMIT_PER_DAY', '200'))
    RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', '50'))
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '20'))
    RATE_LIMIT_STRATEGY = os.getenv('RATE_LIMIT_STRATEGY', 'fixed-window')
    RATE_LIMIT_STORAGE = os.getenv('RATE_LIMIT_STORAGE', 'memory')
    
    # API Security
    API_KEY_REQUIRED = os.getenv('API_KEY_REQUIRED', 'false').lower() == 'true'
    API_KEY_HEADER = os.getenv('API_KEY_HEADER', 'X-API-Key')
    DEFAULT_API_KEY = os.getenv('DEFAULT_API_KEY', '')
    
    # ========================================================================
    # Cache Configuration
    # ========================================================================
    
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    
    # Redis Configuration
    REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_SSL = os.getenv('REDIS_SSL', 'false').lower() == 'true'
    
    # Cache Settings
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_THRESHOLD = int(os.getenv('CACHE_THRESHOLD', '1000'))
    CACHE_KEY_PREFIX = os.getenv('CACHE_KEY_PREFIX', 'docker_management_')
    
    # ========================================================================
    # Logging Configuration
    # ========================================================================
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_ERROR_FILE = os.getenv('LOG_ERROR_FILE', 'logs/error.log')
    LOG_ACCESS_FILE = os.getenv('LOG_ACCESS_FILE', 'logs/access.log')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '10'))
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    
    CONSOLE_LOG_ENABLED = os.getenv('CONSOLE_LOG_ENABLED', 'true').lower() == 'true'
    CONSOLE_LOG_LEVEL = os.getenv('CONSOLE_LOG_LEVEL', 'INFO')
    
    # ========================================================================
    # Docker Configuration
    # ========================================================================
    
    DOCKER_HOST = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
    DOCKER_TIMEOUT = int(os.getenv('DOCKER_TIMEOUT', '10'))
    DOCKER_VERSION = os.getenv('DOCKER_VERSION', 'auto')
    DOCKER_TLS_VERIFY = os.getenv('DOCKER_TLS_VERIFY', 'false').lower() == 'true'
    DOCKER_CERT_PATH = os.getenv('DOCKER_CERT_PATH', '')
    
    DOCKER_MONITOR_INTERVAL = int(os.getenv('DOCKER_MONITOR_INTERVAL', '60'))
    DOCKER_HEALTH_CHECK_INTERVAL = int(os.getenv('DOCKER_HEALTH_CHECK_INTERVAL', '30'))
    
    # ========================================================================
    # Ansible Configuration
    # ========================================================================
    
    ANSIBLE_INVENTORY_PATH = os.getenv('ANSIBLE_INVENTORY_PATH', 'config/inventory.yml')
    ANSIBLE_PLAYBOOKS_DIR = os.getenv('ANSIBLE_PLAYBOOKS_DIR', 'playbooks')
    ANSIBLE_DEFAULT_PLAYBOOK = os.getenv('ANSIBLE_DEFAULT_PLAYBOOK', 'main.yml')
    ANSIBLE_CONFIG_FILE = os.getenv('ANSIBLE_CONFIG_FILE', 'ansible.cfg')
    
    ANSIBLE_TIMEOUT = int(os.getenv('ANSIBLE_TIMEOUT', '3600'))
    ANSIBLE_CHECK_MODE = os.getenv('ANSIBLE_CHECK_MODE', 'false').lower() == 'true'
    ANSIBLE_VERBOSITY = int(os.getenv('ANSIBLE_VERBOSITY', '1'))
    ANSIBLE_FORKS = int(os.getenv('ANSIBLE_FORKS', '5'))
    
    # ========================================================================
    # Backup Configuration
    # ========================================================================
    
    BACKUP_BASE_DIR = os.getenv('BACKUP_BASE_DIR', 'backups')
    BACKUP_LOG_DIR = os.getenv('BACKUP_LOG_DIR', 'logs/backup')
    BACKUP_TEMP_DIR = os.getenv('BACKUP_TEMP_DIR', '/tmp/backups')
    
    BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
    BACKUP_MAX_SIZE_GB = int(os.getenv('BACKUP_MAX_SIZE_GB', '10'))
    BACKUP_COMPRESSION_LEVEL = int(os.getenv('BACKUP_COMPRESSION_LEVEL', '6'))
    BACKUP_ENCRYPTION_ENABLED = os.getenv('BACKUP_ENCRYPTION_ENABLED', 'false').lower() == 'true'
    BACKUP_ENCRYPTION_KEY = os.getenv('BACKUP_ENCRYPTION_KEY', '')
    
    BACKUP_SCHEDULE_ENABLED = os.getenv('BACKUP_SCHEDULE_ENABLED', 'true').lower() == 'true'
    BACKUP_SCHEDULE_TIME = os.getenv('BACKUP_SCHEDULE_TIME', '02:00')
    BACKUP_SCHEDULE_DAY_OF_WEEK = int(os.getenv('BACKUP_SCHEDULE_DAY_OF_WEEK', '0'))
    BACKUP_NOTIFICATION_ENABLED = os.getenv('BACKUP_NOTIFICATION_ENABLED', 'true').lower() == 'true'
    
    # ========================================================================
    # Monitoring Configuration
    # ========================================================================
    
    HEALTH_CHECK_ENABLED = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))
    HEALTH_CHECK_TIMEOUT = int(os.getenv('HEALTH_CHECK_TIMEOUT', '5'))
    
    METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
    METRICS_PORT = int(os.getenv('METRICS_PORT', '9100'))
    METRICS_PATH = os.getenv('METRICS_PATH', '/metrics')
    
    ALERT_DISK_USAGE_THRESHOLD = int(os.getenv('ALERT_DISK_USAGE_THRESHOLD', '90'))
    ALERT_MEMORY_USAGE_THRESHOLD = int(os.getenv('ALERT_MEMORY_USAGE_THRESHOLD', '85'))
    ALERT_CPU_USAGE_THRESHOLD = int(os.getenv('ALERT_CPU_USAGE_THRESHOLD', '80'))
    ALERT_DOCKER_DOWN = os.getenv('ALERT_DOCKER_DOWN', 'true').lower() == 'true'
    
    # ========================================================================
    # UI Configuration
    # ========================================================================
    
    UI_THEME = os.getenv('UI_THEME', 'dark')
    UI_LANGUAGE = os.getenv('UI_LANGUAGE', 'fa')
    UI_TIMEZONE = os.getenv('UI_TIMEZONE', 'Asia/Tehran')
    UI_REFRESH_INTERVAL = int(os.getenv('UI_REFRESH_INTERVAL', '30'))
    
    DASHBOARD_MAX_CONTAINERS = int(os.getenv('DASHBOARD_MAX_CONTAINERS', '20'))
    DASHBOARD_MAX_IMAGES = int(os.getenv('DASHBOARD_MAX_IMAGES', '20'))
    DASHBOARD_MAX_LOGS = int(os.getenv('DASHBOARD_MAX_LOGS', '100'))
    DASHBOARD_CHART_HISTORY_HOURS = int(os.getenv('DASHBOARD_CHART_HISTORY_HOURS', '24'))
    
    # ========================================================================
    # Advanced Configuration
    # ========================================================================
    
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'false').lower() == 'true'
    SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', '3600'))
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'txt,log,yml,yaml,json,tar,gz,zip,sql').split(',')
    
    WORKERS = int(os.getenv('WORKERS', '4'))
    THREADS = int(os.getenv('THREADS', '8'))
    WORKER_TIMEOUT = int(os.getenv('WORKER_TIMEOUT', '30'))
    
    SSL_ENABLED = os.getenv('SSL_ENABLED', 'false').lower() == 'true'
    SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '')
    SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', '')
    
    # ========================================================================
    # Development Configuration
    # ========================================================================
    
    DEBUG_TOOLBAR_ENABLED = os.getenv('DEBUG_TOOLBAR_ENABLED', 'false').lower() == 'true'
    DEBUG_SQL_QUERIES = os.getenv('DEBUG_SQL_QUERIES', 'false').lower() == 'true'
    DEBUG_PROFILER_ENABLED = os.getenv('DEBUG_PROFILER_ENABLED', 'false').lower() == 'true'
    
    MOCK_DOCKER = os.getenv('MOCK_DOCKER', 'false').lower() == 'true'
    MOCK_ANSIBLE = os.getenv('MOCK_ANSIBLE', 'false').lower() == 'true'
    MOCK_CRON = os.getenv('MOCK_CRON', 'false').lower() == 'true'
    
    # ========================================================================
    # Helper Properties
    # ========================================================================
    
    @property
    def is_production(self):
        """آیا در محیط production هستیم؟"""
        return self.FLASK_ENV == 'production'
    
    @property
    def is_development(self):
        """آیا در محیط development هستیم؟"""
        return self.FLASK_ENV == 'development'
    
    @property
    def is_testing(self):
        """آیا در محیط testing هستیم؟"""
        return self.FLASK_ENV == 'testing'
    
    @property
    def redis_url(self):
        """URL کامل Redis"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def cache_config(self):
        """پیکربندی کش"""
        if self.CACHE_TYPE == 'redis' and self.REDIS_ENABLED:
            return {
                'CACHE_TYPE': 'redis',
                'CACHE_REDIS_URL': self.redis_url,
                'CACHE_DEFAULT_TIMEOUT': self.CACHE_DEFAULT_TIMEOUT,
                'CACHE_KEY_PREFIX': self.CACHE_KEY_PREFIX
            }
        return {
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': self.CACHE_DEFAULT_TIMEOUT,
            'CACHE_THRESHOLD': self.CACHE_THRESHOLD
        }
    
    @property
    def rate_limit_config(self):
        """پیکربندی Rate Limiting"""
        if not self.RATE_LIMIT_ENABLED:
            return None
        
        limits = []
        if self.RATE_LIMIT_PER_MINUTE:
            limits.append(f"{self.RATE_LIMIT_PER_MINUTE} per minute")
        if self.RATE_LIMIT_PER_HOUR:
            limits.append(f"{self.RATE_LIMIT_PER_HOUR} per hour")
        if self.RATE_LIMIT_PER_DAY:
            limits.append(f"{self.RATE_LIMIT_PER_DAY} per day")
        
        return {
            'default': limits,
            'strategy': self.RATE_LIMIT_STRATEGY,
            'storage_uri': 'redis://' if self.RATE_LIMIT_STORAGE == 'redis' else 'memory://'
        }


# ایجاد نمونه config
config = Config()