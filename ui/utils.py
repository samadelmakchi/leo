"""
ماژول توابع کمکی - Utility Functions
"""

from datetime import datetime
import json
import hashlib
from functools import wraps
from flask import jsonify, request
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Pagination Functions
# ============================================================================

def paginate(items, page=1, per_page=20):
    """
    تابع کمک‌کننده برای صفحه‌بندی
    
    Args:
        items: لیست آیتم‌ها
        page: شماره صفحه (شروع از 1)
        per_page: تعداد آیتم در هر صفحه
    
    Returns:
        tuple: (آیتم‌های صفحه فعلی, تعداد کل آیتم‌ها, تعداد کل صفحات)
    """
    if not items:
        return [], 0, 0
    
    # اعتبارسنجی ورودی‌ها
    page = max(1, page)
    per_page = max(1, min(per_page, 1000))  # محدودیت برای جلوگیری از load زیاد
    
    start = (page - 1) * per_page
    end = start + per_page
    total = len(items)
    
    # محاسبه تعداد صفحات
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    # بررسی اگر صفحه خواسته شده خارج از محدوده باشد
    if start >= total:
        return [], total, total_pages
    
    return items[start:end], total, total_pages


def get_pagination_params(request, default_per_page=20, max_per_page=100):
    """
    دریافت پارامترهای صفحه‌بندی از request
    
    Args:
        request: شی request فلاسک
        default_per_page: تعداد پیش‌فرض آیتم در صفحه
        max_per_page: حداکثر تعداد آیتم در صفحه
    
    Returns:
        tuple: (page, per_page)
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', default_per_page, type=int)
        
        # اعتبارسنجی و محدودیت
        page = max(1, page)
        per_page = min(max(1, per_page), max_per_page)
        
        return page, per_page
    except ValueError:
        logger.warning(f"Invalid pagination parameters: page={request.args.get('page')}, per_page={request.args.get('per_page')}")
        return 1, default_per_page


def create_pagination_response(items, page, per_page, total, total_pages, **extra_fields):
    """
    ایجاد پاسخ استاندارد برای صفحه‌بندی
    
    Args:
        items: آیتم‌های صفحه فعلی
        page: شماره صفحه فعلی
        per_page: تعداد آیتم در هر صفحه
        total: تعداد کل آیتم‌ها
        total_pages: تعداد کل صفحات
        **extra_fields: فیلدهای اضافی برای اضافه شدن به پاسخ
    
    Returns:
        dict: پاسخ صفحه‌بندی استاندارد
    """
    response = {
        "status": "success",
        "data": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None
        }
    }
    
    # اضافه کردن فیلدهای اضافی
    response.update(extra_fields)
    
    return response

# ============================================================================
# Validation & Sanitization Functions
# ============================================================================

def validate_required_fields(data, required_fields):
    """
    اعتبارسنجی فیلدهای الزامی
    
    Args:
        data: دیکشنری داده‌ها
        required_fields: لیست فیلدهای الزامی
    
    Returns:
        tuple: (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return False, f"فیلدهای الزامی وجود ندارد: {', '.join(missing_fields)}"
    
    return True, ""


def sanitize_input(input_str, max_length=1000):
    """
    پاکسازی ورودی کاربر
    
    Args:
        input_str: رشته ورودی
        max_length: حداکثر طول مجاز
    
    Returns:
        str: رشته پاکسازی شده
    """
    if not input_str:
        return ""
    
    # محدودیت طول
    if len(input_str) > max_length:
        input_str = input_str[:max_length]
    
    # حذف کاراکترهای خطرناک (می‌توانید بر اساس نیاز اضافه کنید)
    dangerous_chars = ['<', '>', 'script', 'javascript:', 'onload', 'onerror']
    for char in dangerous_chars:
        input_str = input_str.replace(char, '')
    
    return input_str.strip()


def validate_integer(value, min_val=None, max_val=None, default=None):
    """
    اعتبارسنجی عدد صحیح
    
    Args:
        value: مقدار ورودی
        min_val: حداقل مقدار مجاز
        max_val: حداکثر مقدار مجاز
        default: مقدار پیش‌فرض در صورت نامعتبر بودن
    
    Returns:
        int: عدد معتبر
    """
    try:
        int_value = int(value)
        
        if min_val is not None and int_value < min_val:
            return default if default is not None else min_val
        
        if max_val is not None and int_value > max_val:
            return default if default is not None else max_val
        
        return int_value
    except (ValueError, TypeError):
        return default

# ============================================================================
# Time & Date Functions
# ============================================================================

def format_timestamp(timestamp, format_str="%Y-%m-%d %H:%M:%S"):
    """
    فرمت‌بندی timestamp
    
    Args:
        timestamp: timestamp یا رشته تاریخ
        format_str: فرمت خروجی
    
    Returns:
        str: تاریخ فرمت شده
    """
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        
        return dt.strftime(format_str)
    except:
        return ""


def get_current_timestamp():
    """دریافت timestamp فعلی"""
    return datetime.now().isoformat()


def time_ago(timestamp):
    """
    نمایش زمان به صورت "چند وقت پیش"
    
    Args:
        timestamp: timestamp
    
    Returns:
        str: متن "چند وقت پیش"
    """
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} سال پیش"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} ماه پیش"
        elif diff.days > 0:
            return f"{diff.days} روز پیش"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ساعت پیش"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} دقیقه پیش"
        else:
            return "همین الان"
    except:
        return ""

# ============================================================================
# File & Size Functions
# ============================================================================

def format_size(size_bytes):
    """
    فرمت‌بندی سایز به صورت خوانا
    
    Args:
        size_bytes: سایز به بایت
    
    Returns:
        str: سایز فرمت شده
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes < 1024 * 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024 * 1024):.2f} TB"


def parse_size(size_str):
    """
    تبدیل سایز رشته‌ای به بایت
    
    Args:
        size_str: رشته سایز (مثلاً "10 MB", "1.5 GB")
    
    Returns:
        int: سایز به بایت
    """
    size_str = size_str.upper().strip()
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024
    }
    
    for unit, multiplier in multipliers.items():
        if size_str.endswith(unit):
            try:
                number = float(size_str[:-len(unit)].strip())
                return int(number * multiplier)
            except ValueError:
                return 0
    
    try:
        return int(float(size_str))
    except ValueError:
        return 0

# ============================================================================
# Security Functions
# ============================================================================

def generate_hash(data, algorithm='sha256'):
    """
    تولید هش از داده
    
    Args:
        data: داده ورودی
        algorithm: الگوریتم هش (sha256, md5, ...)
    
    Returns:
        str: هش تولید شده
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    if algorithm == 'sha256':
        return hashlib.sha256(data).hexdigest()
    elif algorithm == 'md5':
        return hashlib.md5(data).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(data).hexdigest()
    else:
        raise ValueError(f"Algorithm {algorithm} not supported")


def validate_api_key(api_key, valid_keys):
    """
    اعتبارسنجی API Key
    
    Args:
        api_key: کلید API دریافتی
        valid_keys: لیست کلیدهای معتبر
    
    Returns:
        bool: آیا کلید معتبر است یا نه
    """
    if not api_key:
        return False
    
    return api_key in valid_keys

# ============================================================================
# Decorators
# ============================================================================

def require_api_key(valid_keys):
    """
    دکوراتور برای نیاز به API Key
    
    Args:
        valid_keys: لیست کلیدهای معتبر
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            
            if not validate_api_key(api_key, valid_keys):
                logger.warning(f"Invalid API key attempt: {api_key}")
                return jsonify({
                    "status": "error",
                    "message": "API Key نامعتبر یا وجود ندارد"
                }), 401
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def cache_response(timeout=60):
    """
    دکوراتور برای کش کردن پاسخ
    
    Args:
        timeout: زمان انقضای کش (ثانیه)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # این یک پیاده‌سازی ساده است
            # برای استفاده واقعی از Flask-Caching استفاده کنید
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # در اینجا می‌توانید منطق کش را اضافه کنید
            # فعلاً فقط نمونه است
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================================
# Response Helpers
# ============================================================================

def success_response(data=None, message="عملیات با موفقیت انجام شد", **kwargs):
    """
    ایجاد پاسخ موفقیت
    
    Args:
        data: داده پاسخ
        message: پیام موفقیت
        **kwargs: فیلدهای اضافی
    
    Returns:
        tuple: (json_response, status_code)
    """
    response = {
        "status": "success",
        "message": message,
        "timestamp": get_current_timestamp()
    }
    
    if data is not None:
        response["data"] = data
    
    response.update(kwargs)
    
    return jsonify(response), 200


def error_response(message="خطا در انجام عملیات", status_code=400, errors=None, **kwargs):
    """
    ایجاد پاسخ خطا
    
    Args:
        message: پیام خطا
        status_code: کد وضعیت HTTP
        errors: لیست خطاهای جزئی
        **kwargs: فیلدهای اضافی
    
    Returns:
        tuple: (json_response, status_code)
    """
    response = {
        "status": "error",
        "message": message,
        "timestamp": get_current_timestamp()
    }
    
    if errors:
        response["errors"] = errors
    
    response.update(kwargs)
    
    return jsonify(response), status_code


def not_found_response(message="منبع یافت نشد", **kwargs):
    """پاسخ 404"""
    return error_response(message=message, status_code=404, **kwargs)


def forbidden_response(message="دسترسی غیرمجاز", **kwargs):
    """پاسخ 403"""
    return error_response(message=message, status_code=403, **kwargs)


def internal_error_response(message="خطای داخلی سرور", **kwargs):
    """پاسخ 500"""
    return error_response(message=message, status_code=500, **kwargs)

# ============================================================================
# Docker Specific Helpers
# ============================================================================

def parse_docker_datetime(docker_datetime):
    """
    تبدیل datetime داکر به فرمت خوانا
    
    Args:
        docker_datetime: رشته datetime داکر
    
    Returns:
        str: datetime فرمت شده
    """
    if not docker_datetime:
        return ""
    
    try:
        # فرمت داکر: 2024-01-01T10:30:45.123456789Z
        dt_str = docker_datetime.split('.')[0].replace('T', ' ')
        dt_str = dt_str.replace('Z', '')
        return dt_str
    except:
        return docker_datetime


def get_container_status_badge(status):
    """
    دریافت badge وضعیت کانتینر
    
    Args:
        status: وضعیت کانتینر
    
    Returns:
        dict: اطلاعات badge
    """
    status_map = {
        'running': {
            'label': 'در حال اجرا',
            'color': 'success',
            'icon': 'play-circle'
        },
        'exited': {
            'label': 'متوقف شده',
            'color': 'secondary',
            'icon': 'stop-circle'
        },
        'paused': {
            'label': 'مکث شده',
            'color': 'warning',
            'icon': 'pause-circle'
        },
        'restarting': {
            'label': 'در حال راه‌اندازی مجدد',
            'color': 'info',
            'icon': 'arrow-repeat'
        },
        'dead': {
            'label': 'مرده',
            'color': 'danger',
            'icon': 'x-circle'
        },
        'created': {
            'label': 'ایجاد شده',
            'color': 'primary',
            'icon': 'plus-circle'
        }
    }
    
    return status_map.get(status.lower(), {
        'label': status,
        'color': 'dark',
        'icon': 'question-circle'
    })

# ============================================================================
# Logging Helper
# ============================================================================

def log_request_info():
    """لاگ کردن اطلاعات درخواست"""
    logger.info(f"Request: {request.method} {request.path} - IP: {request.remote_addr}")
    if request.method in ['POST', 'PUT', 'PATCH']:
        logger.debug(f"Request data: {request.get_json(silent=True) or request.form.to_dict()}")
