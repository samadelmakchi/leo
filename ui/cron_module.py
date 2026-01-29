"""
ماژول مدیریت Cron Jobs - نسخه بهینه‌شده
"""

import os
import re
import tempfile
import subprocess
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, jsonify, request
from utils import (
    success_response,
    error_response,
    not_found_response,
    forbidden_response,
    validate_required_fields,
    sanitize_input,
    get_current_timestamp,
    log_request_info
)

logger = logging.getLogger(__name__)

# ایجاد Blueprint برای Cron
cron_bp = Blueprint('cron', __name__, url_prefix='/api/cron')

# ============================================================================
# Configuration
# ============================================================================

# کاربران مجاز برای مدیریت cron
ALLOWED_USERS = ['root']  # می‌توانید کاربران دیگر را اضافه کنید

# محدودیت‌ها
MAX_CRON_JOBS = 100
MAX_COMMAND_LENGTH = 1000
CRON_VALIDATION_RULES = {
    'minute': (0, 59),
    'hour': (0, 23),
    'day_of_month': (1, 31),
    'month': (1, 12),
    'day_of_week': (0, 7)  # 0 و 7 هر دو یکشنبه هستند
}

# ============================================================================
# Decorators
# ============================================================================

def handle_cron_errors(func):
    """دکوراتور برای مدیریت خطاهای Cron"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            log_request_info()
            return func(*args, **kwargs)
        except PermissionError as e:
            logger.error(f"Permission denied in {func.__name__}: {e}")
            return forbidden_response(
                message="دسترسی به cron محدود شده است",
                details="برنامه نیاز به دسترسی sudo دارد"
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error in {func.__name__}: {e}")
            return error_response(
                message=f"خطا در اجرای دستور cron: {e.stderr[:200] if e.stderr else str(e)}",
                status_code=500
            )
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return error_response(
                message="خطا در مدیریت cron jobs",
                status_code=500,
                details=str(e)[:200]
            )
    return wrapper

def validate_user_access(user):
    """اعتبارسنجی دسترسی کاربر"""
    if user not in ALLOWED_USERS:
        raise PermissionError(f"User {user} not allowed to manage cron")

# ============================================================================
# Core Cron Functions
# ============================================================================

def get_crontab(user='root'):
    """دریافت crontab کاربر به صورت امن"""
    validate_user_access(user)
    
    try:
        if user == 'root':
            cmd = ['sudo', 'crontab', '-l']
        else:
            cmd = ['crontab', '-l', '-u', user]
        
        logger.debug(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10  # محدودیت زمانی
        )
        
        if result.returncode == 0:
            content = result.stdout.strip()
            logger.info(f"Crontab retrieved for user {user}, length: {len(content)} chars")
            return content
        else:
            # اگر crontab خالی باشد
            if 'no crontab' in result.stderr.lower():
                logger.info(f"No crontab found for user {user}")
                return ""
            
            logger.error(f"Error getting crontab for {user}: {result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, 
                cmd, 
                result.stdout, 
                result.stderr
            )
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while getting crontab for user {user}")
        raise Exception("Timeout while reading crontab")

def set_crontab(crontab_content, user='root'):
    """ذخیره crontab کاربر به صورت امن"""
    validate_user_access(user)
    
    # اعتبارسنجی اولیه
    if not isinstance(crontab_content, str):
        raise ValueError("Crontab content must be a string")
    
    if len(crontab_content) > 10000:  # محدودیت سایز
        raise ValueError("Crontab content too large")
    
    try:
        # ایجاد فایل موقت امن
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.cron',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(crontab_content)
            temp_file = f.name
        
        try:
            # تنظیم crontab
            if user == 'root':
                cmd = ['sudo', 'crontab', temp_file]
            else:
                cmd = ['crontab', temp_file, '-u', user]
            
            logger.debug(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            
            logger.info(f"Crontab updated successfully for user {user}")
            return True, "Crontab updated successfully"
            
        finally:
            # حذف فایل موقت در هر صورت
            try:
                os.unlink(temp_file)
            except OSError as e:
                logger.warning(f"Could not delete temp file {temp_file}: {e}")
                
    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting crontab for {user}: {e.stderr}")
        return False, f"Cron error: {e.stderr[:200]}"
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while setting crontab for user {user}")
        return False, "Timeout while updating crontab"

def parse_cron_line(line):
    """پارس کردن یک خط cron با جزئیات کامل"""
    line = line.strip()
    
    # خطوط خالی یا کامنت
    if not line or line.startswith('#'):
        # کامنت‌ها را هم برگردانیم
        if line.startswith('#'):
            return {
                'type': 'comment',
                'raw': line,
                'enabled': False
            }
        return None
    
    # استخراج متغیرهای محیطی
    env_vars = {}
    parts = line.split()
    
    while parts and '=' in parts[0]:
        key_value = parts.pop(0)
        if '=' in key_value:
            key, value = key_value.split('=', 1)
            env_vars[key] = value
    
    # بررسی تعداد اجزاء کافی
    if len(parts) < 5:
        return None
    
    # استخراج زمان‌بندی
    schedule = {
        'minute': parts[0],
        'hour': parts[1],
        'day_of_month': parts[2],
        'month': parts[3],
        'day_of_week': parts[4]
    }
    
    # دستور باقی‌مانده
    command = ' '.join(parts[5:]) if len(parts) > 5 else ''
    
    # بررسی وضعیت فعال/غیرفعال
    enabled = not line.strip().startswith('#')
    
    return {
        'type': 'job',
        'schedule': schedule,
        'command': command,
        'env_vars': env_vars,
        'raw': line if enabled else line[1:].strip(),
        'enabled': enabled,
        'validated': validate_cron_schedule_internal(schedule)
    }

def format_cron_job(job, user='root'):
    """فرمت‌بندی یک cron job برای نمایش"""
    if job.get('type') == 'comment':
        return {
            'id': hash(job.get('raw', '')),
            'type': 'comment',
            'content': job.get('raw', ''),
            'user': user
        }
    
    schedule = job.get('schedule', {})
    command = job.get('command', '')
    
    # تولید شناسه منحصر به فرد
    job_id = abs(hash(f"{user}:{job.get('raw', '')}")) % (10 ** 8)
    
    # ترجمه زمان‌بندی به فارسی
    schedule_text_parts = []
    
    if schedule.get('minute') != '*':
        schedule_text_parts.append(f"دقیقه {schedule['minute']}")
    if schedule.get('hour') != '*':
        schedule_text_parts.append(f"ساعت {schedule['hour']}")
    if schedule.get('day_of_month') != '*':
        schedule_text_parts.append(f"روز {schedule['day_of_month']} ماه")
    if schedule.get('month') != '*':
        schedule_text_parts.append(f"ماه {schedule['month']}")
    if schedule.get('day_of_week') != '*':
        days_map = {'0': 'یکشنبه', '1': 'دوشنبه', '2': 'سه‌شنبه', 
                   '3': 'چهارشنبه', '4': 'پنجشنبه', '5': 'جمعه', '6': 'شنبه', '7': 'یکشنبه'}
        day_num = schedule['day_of_week']
        day_name = days_map.get(day_num, day_num)
        schedule_text_parts.append(f"روز {day_name}")
    
    schedule_text = '، '.join(schedule_text_parts) if schedule_text_parts else 'هر دقیقه'
    
    # تشخیص نوع دستور
    command_type = 'unknown'
    if 'docker' in command.lower():
        command_type = 'docker'
    elif 'ansible' in command.lower():
        command_type = 'ansible'
    elif 'backup' in command.lower():
        command_type = 'backup'
    elif 'curl' in command.lower() or 'wget' in command.lower():
        command_type = 'web'
    elif 'python' in command.lower() or 'python3' in command.lower():
        command_type = 'python'
    elif 'sh ' in command.lower() or 'bash ' in command.lower():
        command_type = 'shell'
    
    return {
        'id': job_id,
        'type': 'job',
        'schedule': schedule,
        'schedule_text': schedule_text,
        'command': command,
        'short_command': command[:80] + ('...' if len(command) > 80 else ''),
        'command_type': command_type,
        'env_vars': job.get('env_vars', {}),
        'raw': job.get('raw', ''),
        'user': user,
        'enabled': job.get('enabled', True),
        'validated': job.get('validated', True),
        'created_at': get_current_timestamp()
    }

# ============================================================================
# Validation Functions
# ============================================================================

def validate_cron_schedule_internal(schedule):
    """اعتبارسنجی داخلی زمان‌بندی cron"""
    for field, (min_val, max_val) in CRON_VALIDATION_RULES.items():
        value = schedule.get(field, '*')
        if not validate_cron_field(value, min_val, max_val):
            return False
    return True

def validate_cron_field(field, min_val, max_val):
    """اعتبارسنجی یک فیلد cron"""
    if field == '*':
        return True
    
    # بررسی لیست
    if ',' in field:
        parts = field.split(',')
        return all(validate_cron_part(part.strip(), min_val, max_val) for part in parts)
    
    # بررسی بازه
    if '-' in field:
        parts = field.split('-')
        if len(parts) != 2:
            return False
        try:
            start = int(parts[0])
            end = int(parts[1])
            return min_val <= start <= max_val and min_val <= end <= max_val and start <= end
        except:
            return False
    
    # بررسی step
    if '/' in field:
        parts = field.split('/')
        if len(parts) != 2:
            return False
        try:
            base = parts[0] if parts[0] != '*' else str(min_val)
            step = int(parts[1])
            value = int(base)
            return min_val <= value <= max_val and step > 0
        except:
            return False
    
    # بررسی مقدار ساده
    try:
        value = int(field)
        return min_val <= value <= max_val
    except:
        return False

def validate_cron_part(part, min_val, max_val):
    """اعتبارسنجی بخشی از یک فیلد cron"""
    return validate_cron_field(part, min_val, max_val)

def validate_cron_command(command):
    """اعتبارسنجی دستور cron"""
    if not command or not command.strip():
        return False, "Command cannot be empty"
    
    if len(command) > MAX_COMMAND_LENGTH:
        return False, f"Command too long (max {MAX_COMMAND_LENGTH} characters)"
    
    # بررسی دستورات خطرناک (می‌توانید سفارشی کنید)
    dangerous_patterns = [
        r'rm\s+-rf\s+/\s*',
        r':\(\)\{\s*:\|\:&\s*\};:',
        r'mkfs',
        r'dd\s+if=/dev/',
        r'>/dev/sd'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False, "Dangerous command detected"
    
    return True, ""

# ============================================================================
# Routes
# ============================================================================

@cron_bp.route("/jobs", methods=["GET"])
@handle_cron_errors
def get_cron_jobs():
    """دریافت تمام cron jobs"""
    user = request.args.get('user', 'root', type=str)
    
    crontab = get_crontab(user)
    
    jobs = []
    comments = []
    
    for line in crontab.split('\n'):
        parsed = parse_cron_line(line)
        if parsed:
            if parsed.get('type') == 'comment':
                comments.append(format_cron_job(parsed, user))
            else:
                jobs.append(format_cron_job(parsed, user))
    
    logger.info(f"Retrieved {len(jobs)} jobs and {len(comments)} comments for user {user}")
    
    return success_response(
        data={
            'jobs': jobs,
            'comments': comments,
            'total_jobs': len(jobs),
            'total_lines': len(crontab.split('\n')),
            'user': user,
            'crontab_size': len(crontab)
        },
        message=f"لیست cron jobs کاربر {user}"
    )

@cron_bp.route("/jobs/<int:job_id>", methods=["GET"])
@handle_cron_errors
def get_cron_job(job_id):
    """دریافت یک cron job خاص"""
    user = request.args.get('user', 'root', type=str)
    
    crontab = get_crontab(user)
    
    for line in crontab.split('\n'):
        parsed = parse_cron_line(line)
        if parsed and parsed.get('type') == 'job':
            formatted = format_cron_job(parsed, user)
            if formatted['id'] == job_id:
                return success_response(
                    data={'job': formatted},
                    message=f"جزییات cron job #{job_id}"
                )
    
    return not_found_response(
        message=f"Cron job با شناسه {job_id} یافت نشد"
    )

@cron_bp.route("/jobs/add", methods=["POST"])
@handle_cron_errors
def add_cron_job():
    """اضافه کردن cron job جدید"""
    data = request.json
    
    # اعتبارسنجی فیلدهای الزامی
    is_valid, error_msg = validate_required_fields(
        data, 
        ['command', 'schedule']
    )
    if not is_valid:
        return error_response(message=error_msg, status_code=400)
    
    command = sanitize_input(data.get('command', ''))
    schedule = data.get('schedule', {})
    user = data.get('user', 'root')
    enabled = data.get('enabled', True)
    env_vars = data.get('env_vars', {})
    description = data.get('description', '')
    
    # اعتبارسنجی دستور
    is_valid, error_msg = validate_cron_command(command)
    if not is_valid:
        return error_response(message=error_msg, status_code=400)
    
    # اعتبارسنجی زمان‌بندی
    if not validate_cron_schedule_internal(schedule):
        return error_response(
            message="زمان‌بندی cron نامعتبر است",
            status_code=400
        )
    
    # ساخت خط cron
    cron_line_parts = []
    
    # اضافه کردن description به صورت کامنت
    if description:
        cron_line_parts.append(f"# {description}")
    
    # اضافه کردن متغیرهای محیطی
    for key, value in env_vars.items():
        cron_line_parts.append(f"{key}={value}")
    
    # اضافه کردن زمان‌بندی
    cron_line_parts.extend([
        schedule.get('minute', '*'),
        schedule.get('hour', '*'),
        schedule.get('day_of_month', '*'),
        schedule.get('month', '*'),
        schedule.get('day_of_week', '*')
    ])
    
    # اضافه کردن دستور
    cron_line_parts.append(command)
    
    cron_line = ' '.join(cron_line_parts)
    
    # اگر غیرفعال است
    if not enabled:
        cron_line = f"# {cron_line}"
    
    # دریافت crontab فعلی
    current_crontab = get_crontab(user)
    
    # بررسی محدودیت تعداد jobs
    job_count = sum(1 for line in current_crontab.split('\n') 
                   if parse_cron_line(line) and parse_cron_line(line).get('type') == 'job')
    
    if job_count >= MAX_CRON_JOBS:
        return error_response(
            message=f"تعداد cron jobs به حد مجاز ({MAX_CRON_JOBS}) رسیده است",
            status_code=400
        )
    
    # اضافه کردن job جدید
    new_crontab = current_crontab.strip()
    if new_crontab:
        new_crontab += '\n\n'
    new_crontab += cron_line + '\n'
    
    # ذخیره crontab جدید
    success, message = set_crontab(new_crontab, user)
    
    if success:
        logger.info(f"Added new cron job for user {user}: {command[:50]}...")
        return success_response(
            data={
                'cron_line': cron_line,
                'user': user,
                'enabled': enabled
            },
            message="Cron job با موفقیت اضافه شد"
        )
    else:
        return error_response(
            message=f"خطا در اضافه کردن cron job: {message}",
            status_code=500
        )

@cron_bp.route("/jobs/<int:job_id>/toggle", methods=["POST"])
@handle_cron_errors
def toggle_cron_job(job_id):
    """فعال/غیرفعال کردن cron job"""
    data = request.json
    enabled = data.get('enabled')
    
    if enabled is None:
        return error_response(
            message="فیلد enabled الزامی است",
            status_code=400
        )
    
    user = data.get('user', 'root')
    
    # دریافت crontab فعلی
    current_crontab = get_crontab(user)
    lines = current_crontab.split('\n')
    
    new_lines = []
    job_found = False
    
    for line in lines:
        parsed = parse_cron_line(line)
        if parsed and parsed.get('type') == 'job':
            formatted = format_cron_job(parsed, user)
            if formatted['id'] == job_id:
                job_found = True
                if enabled and line.strip().startswith('#'):
                    # حذف کامنت
                    new_line = line.strip()[1:].strip()
                elif not enabled and not line.strip().startswith('#'):
                    # اضافه کردن کامنت
                    new_line = f"# {line.strip()}"
                else:
                    new_line = line
            else:
                new_line = line
        else:
            new_line = line
        
        new_lines.append(new_line)
    
    if not job_found:
        return not_found_response(
            message=f"Cron job با شناسه {job_id} یافت نشد"
        )
    
    new_crontab = '\n'.join(new_lines)
    
    # ذخیره crontab جدید
    success, message = set_crontab(new_crontab, user)
    
    if success:
        action = "فعال" if enabled else "غیرفعال"
        logger.info(f"Cron job #{job_id} {action} for user {user}")
        return success_response(
            message=f"Cron job {action} شد"
        )
    else:
        return error_response(
            message=f"خطا در تغییر وضعیت cron job: {message}",
            status_code=500
        )

@cron_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
@handle_cron_errors
def delete_cron_job(job_id):
    """حذف cron job"""
    user = request.args.get('user', 'root', type=str)
    
    # دریافت crontab فعلی
    current_crontab = get_crontab(user)
    lines = current_crontab.split('\n')
    
    new_lines = []
    job_found = False
    
    for line in lines:
        parsed = parse_cron_line(line)
        if parsed and parsed.get('type') == 'job':
            formatted = format_cron_job(parsed, user)
            if formatted['id'] == job_id:
                job_found = True
                continue  # حذف این خط
        new_lines.append(line)
    
    if not job_found:
        return not_found_response(
            message=f"Cron job با شناسه {job_id} یافت نشد"
        )
    
    new_crontab = '\n'.join(new_lines).strip()
    
    # ذخیره crontab جدید
    success, message = set_crontab(new_crontab, user)
    
    if success:
        logger.info(f"Deleted cron job #{job_id} for user {user}")
        return success_response(
            message="Cron job با موفقیت حذف شد"
        )
    else:
        return error_response(
            message=f"خطا در حذف cron job: {message}",
            status_code=500
        )

@cron_bp.route("/system/status", methods=["GET"])
@handle_cron_errors
def get_cron_system_status():
    """دریافت وضعیت سیستم cron"""
    status_info = {
        'timestamp': get_current_timestamp(),
        'services': {},
        'users': {}
    }
    
    # بررسی سرویس cron برای سیستم‌های مختلف
    services_to_check = ['cron', 'crond', 'systemd-cron']
    
    for service in services_to_check:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=5
            )
            status_info['services'][service] = {
                'active': result.stdout.strip() == 'active',
                'status': result.stdout.strip()
            }
        except:
            status_info['services'][service] = {
                'active': False,
                'status': 'not_found'
            }
    
    # بررسی processهای cron
    try:
        result = subprocess.run(
            ['pgrep', '-c', 'cron'],
            capture_output=True,
            text=True,
            timeout=5
        )
        status_info['process_count'] = int(result.stdout.strip() or 0)
    except:
        status_info['process_count'] = 0
    
    # بررسی crontab برای کاربران مجاز
    for user in ALLOWED_USERS:
        try:
            crontab = get_crontab(user)
            job_count = sum(1 for line in crontab.split('\n') 
                          if parse_cron_line(line) and parse_cron_line(line).get('type') == 'job')
            
            status_info['users'][user] = {
                'has_crontab': bool(crontab.strip()),
                'job_count': job_count,
                'crontab_size': len(crontab)
            }
        except Exception as e:
            status_info['users'][user] = {
                'error': str(e)[:100]
            }
    
    return success_response(
        data=status_info,
        message="وضعیت سیستم cron"
    )

@cron_bp.route("/validate/schedule", methods=["POST"])
@handle_cron_errors
def validate_cron_schedule():
    """اعتبارسنجی زمان‌بندی cron"""
    data = request.json
    schedule = data.get('schedule', {})
    
    errors = []
    warnings = []
    
    # اعتبارسنجی هر فیلد
    for field, (min_val, max_val) in CRON_VALIDATION_RULES.items():
        value = schedule.get(field, '*')
        
        if not validate_cron_field(value, min_val, max_val):
            field_names = {
                'minute': 'دقیقه',
                'hour': 'ساعت',
                'day_of_month': 'روز ماه',
                'month': 'ماه',
                'day_of_week': 'روز هفته'
            }
            errors.append(f"{field_names.get(field, field)} نامعتبر است (مقادیر مجاز: {min_val}-{max_val})")
    
    # هشدار برای زمان‌بندی‌های مشکوک
    if schedule.get('minute') == '*' and schedule.get('hour') == '*':
        warnings.append("اجرای هر دقیقه ممکن است باعث overload شود")
    
    if errors:
        return error_response(
            message="خطا در اعتبارسنجی زمان‌بندی",
            status_code=400,
            errors=errors,
            warnings=warnings
        )
    
    return success_response(
        data={
            'valid': True,
            'schedule': schedule,
            'warnings': warnings
        },
        message="زمان‌بندی cron معتبر است"
    )

@cron_bp.route("/validate/command", methods=["POST"])
@handle_cron_errors
def validate_cron_command_endpoint():
    """اعتبارسنجی دستور cron"""
    data = request.json
    command = data.get('command', '')
    
    is_valid, error_msg = validate_cron_command(command)
    
    if not is_valid:
        return error_response(
            message=error_msg,
            status_code=400
        )
    
    return success_response(
        data={'valid': True},
        message="دستور cron معتبر است"
    )

@cron_bp.route("/backup", methods=["GET"])
@handle_cron_errors
def backup_crontab():
    """پشتیبان‌گیری از crontab"""
    user = request.args.get('user', 'root', type=str)
    
    crontab = get_crontab(user)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ایجاد نام فایل پشتیبان
    backup_filename = f"crontab_backup_{user}_{timestamp}.txt"
    
    return success_response(
        data={
            'crontab': crontab,
            'backup_filename': backup_filename,
            'user': user,
            'timestamp': timestamp,
            'size': len(crontab)
        },
        message="پشتیبان crontab ایجاد شد"
    )

@cron_bp.route("/restore", methods=["POST"])
@handle_cron_errors
def restore_crontab():
    """بازیابی crontab"""
    data = request.json
    crontab_content = data.get('crontab', '')
    user = data.get('user', 'root')
    
    if not crontab_content:
        return error_response(
            message="محتویات crontab الزامی است",
            status_code=400
        )
    
    # ذخیره crontab جدید
    success, message = set_crontab(crontab_content, user)
    
    if success:
        logger.info(f"Crontab restored for user {user}")
        return success_response(
            message="Crontab با موفقیت بازیابی شد"
        )
    else:
        return error_response(
            message=f"خطا در بازیابی crontab: {message}",
            status_code=500
        )

@cron_bp.route("/stats", methods=["GET"])
@handle_cron_errors
def get_cron_stats():
    """دریافت آمار cron"""
    stats = {
        'timestamp': get_current_timestamp(),
        'total_jobs': 0,
        'enabled_jobs': 0,
        'disabled_jobs': 0,
        'users': {}
    }
    
    for user in ALLOWED_USERS:
        try:
            crontab = get_crontab(user)
            user_stats = {
                'total_jobs': 0,
                'enabled_jobs': 0,
                'disabled_jobs': 0,
                'crontab_size': len(crontab)
            }
            
            for line in crontab.split('\n'):
                parsed = parse_cron_line(line)
                if parsed and parsed.get('type') == 'job':
                    user_stats['total_jobs'] += 1
                    if parsed.get('enabled'):
                        user_stats['enabled_jobs'] += 1
                    else:
                        user_stats['disabled_jobs'] += 1
            
            stats['users'][user] = user_stats
            stats['total_jobs'] += user_stats['total_jobs']
            stats['enabled_jobs'] += user_stats['enabled_jobs']
            stats['disabled_jobs'] += user_stats['disabled_jobs']
            
        except Exception as e:
            stats['users'][user] = {'error': str(e)[:100]}
    
    return success_response(
        data=stats,
        message="آمار سیستم cron"
    )