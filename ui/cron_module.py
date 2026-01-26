"""
ماژول مدیریت Cron Jobs
"""

import os
import json
import subprocess
from flask import Blueprint, jsonify, request
from datetime import datetime

# ایجاد Blueprint برای Cron
cron_bp = Blueprint('cron', __name__, url_prefix='/api/cron')

# ============================================================================
# Helper Functions
# ============================================================================

def get_crontab(user='root'):
    """دریافت crontab کاربر"""
    try:
        if user == 'root':
            cmd = ['sudo', 'crontab', '-l']
        else:
            cmd = ['crontab', '-l', '-u', user]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            # اگر crontab خالی باشد
            if result.stderr and 'no crontab' in result.stderr:
                return ""
            return f"Error: {result.stderr}"
            
    except Exception as e:
        return f"Exception: {str(e)}"

def set_crontab(crontab_content, user='root'):
    """تنظیم crontab کاربر"""
    try:
        # ایجاد فایل موقت
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(crontab_content)
            temp_file = f.name
        
        # تنظیم crontab
        if user == 'root':
            cmd = ['sudo', 'crontab', temp_file]
        else:
            cmd = ['crontab', temp_file, '-u', user]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # حذف فایل موقت
        os.unlink(temp_file)
        
        if result.returncode == 0:
            return True, "Crontab updated successfully"
        else:
            return False, result.stderr
            
    except Exception as e:
        return False, f"Exception: {str(e)}"

def parse_cron_line(line):
    """پارس کردن یک خط cron"""
    line = line.strip()
    
    # حذف توضیحات
    if line.startswith('#') or not line:
        return None
    
    # جدا کردن اجزاء
    parts = line.split()
    
    if len(parts) < 6:
        return None
    
    # استخراج زمان‌بندی
    minute = parts[0]
    hour = parts[1]
    day_of_month = parts[2]
    month = parts[3]
    day_of_week = parts[4]
    
    # دستور باقی‌مانده
    command = ' '.join(parts[5:])
    
    # استخراج متغیرهای محیطی
    env_vars = {}
    while len(parts) >= 2 and '=' in parts[0]:
        key, value = parts[0].split('=', 1)
        env_vars[key] = value
        parts = parts[1:]
        command = ' '.join(parts[5:])
    
    return {
        'schedule': {
            'minute': minute,
            'hour': hour,
            'day_of_month': day_of_month,
            'month': month,
            'day_of_week': day_of_week
        },
        'command': command,
        'env_vars': env_vars,
        'raw': line
    }

def format_cron_job(job):
    """فرمت‌بندی یک cron job برای نمایش"""
    schedule = job.get('schedule', {})
    command = job.get('command', '')
    
    # ترجمه زمان‌بندی
    schedule_text = []
    
    if schedule.get('minute') != '*':
        schedule_text.append(f"دقیقه: {schedule['minute']}")
    if schedule.get('hour') != '*':
        schedule_text.append(f"ساعت: {schedule['hour']}")
    if schedule.get('day_of_month') != '*':
        schedule_text.append(f"روز ماه: {schedule['day_of_month']}")
    if schedule.get('month') != '*':
        schedule_text.append(f"ماه: {schedule['month']}")
    if schedule.get('day_of_week') != '*':
        schedule_text.append(f"روز هفته: {schedule['day_of_week']}")
    
    return {
        'id': hash(job.get('raw', '')),
        'schedule': schedule,
        'schedule_text': '، '.join(schedule_text) if schedule_text else 'همیشه',
        'command': command,
        'short_command': command[:50] + '...' if len(command) > 50 else command,
        'env_vars': job.get('env_vars', {}),
        'raw': job.get('raw', ''),
        'user': job.get('user', 'root'),
        'enabled': not job.get('raw', '').strip().startswith('#')
    }

# ============================================================================
# Routes
# ============================================================================

@cron_bp.route("/jobs", methods=["GET"])
def get_cron_jobs():
    """دریافت تمام cron jobs"""
    try:
        users = ['root']  # می‌توانید کاربران دیگر را هم اضافه کنید
        
        all_jobs = []
        
        for user in users:
            crontab = get_crontab(user)
            
            if crontab and not crontab.startswith('Error') and not crontab.startswith('Exception'):
                lines = crontab.split('\n')
                
                for line in lines:
                    job = parse_cron_line(line)
                    if job:
                        job['user'] = user
                        formatted_job = format_cron_job(job)
                        all_jobs.append(formatted_job)
        
        return jsonify({
            "status": "success",
            "count": len(all_jobs),
            "jobs": all_jobs
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@cron_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_cron_job(job_id):
    """دریافت یک cron job خاص"""
    try:
        all_jobs_response = get_cron_jobs()
        if all_jobs_response.status_code != 200:
            return all_jobs_response
        
        data = all_jobs_response.get_json()
        
        for job in data.get('jobs', []):
            if job.get('id') == job_id:
                return jsonify({
                    "status": "success",
                    "job": job
                })
        
        return jsonify({
            "status": "error",
            "message": f"Cron job with ID {job_id} not found"
        }), 404
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@cron_bp.route("/jobs/add", methods=["POST"])
def add_cron_job():
    """اضافه کردن cron job جدید"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        schedule = data.get('schedule', {})
        command = data.get('command', '')
        user = data.get('user', 'root')
        enabled = data.get('enabled', True)
        
        # اعتبارسنجی
        if not command:
            return jsonify({
                "status": "error",
                "message": "Command is required"
            }), 400
        
        # ساخت خط cron
        cron_line = ""
        
        # اضافه کردن متغیرهای محیطی اگر وجود دارند
        env_vars = data.get('env_vars', {})
        for key, value in env_vars.items():
            cron_line += f"{key}={value} "
        
        # زمان‌بندی
        cron_line += f"{schedule.get('minute', '*')} "
        cron_line += f"{schedule.get('hour', '*')} "
        cron_line += f"{schedule.get('day_of_month', '*')} "
        cron_line += f"{schedule.get('month', '*')} "
        cron_line += f"{schedule.get('day_of_week', '*')} "
        
        # دستور
        cron_line += command
        
        # اگر غیرفعال است، کامنت کن
        if not enabled:
            cron_line = f"# {cron_line}"
        
        # دریافت crontab فعلی
        current_crontab = get_crontab(user)
        if current_crontab.startswith('Error') or current_crontab.startswith('Exception'):
            return jsonify({
                "status": "error",
                "message": f"Failed to get current crontab: {current_crontab}"
            }), 500
        
        # اضافه کردن job جدید
        new_crontab = current_crontab
        if new_crontab and not new_crontab.endswith('\n'):
            new_crontab += '\n'
        new_crontab += cron_line + '\n'
        
        # ذخیره crontab جدید
        success, message = set_crontab(new_crontab, user)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Cron job added successfully",
                "cron_line": cron_line
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to add cron job: {message}"
            }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@cron_bp.route("/jobs/<int:job_id>/toggle", methods=["POST"])
def toggle_cron_job(job_id):
    """فعال/غیرفعال کردن cron job"""
    try:
        data = request.json
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({
                "status": "error",
                "message": "enabled field is required"
            }), 400
        
        # دریافت cron job
        job_response = get_cron_job(job_id)
        if job_response.status_code != 200:
            return job_response
        
        job_data = job_response.get_json()
        job = job_data.get('job')
        user = job.get('user', 'root')
        raw_line = job.get('raw', '')
        
        # دریافت crontab فعلی
        current_crontab = get_crontab(user)
        if current_crontab.startswith('Error') or current_crontab.startswith('Exception'):
            return jsonify({
                "status": "error",
                "message": f"Failed to get current crontab: {current_crontab}"
            }), 500
        
        lines = current_crontab.split('\n')
        new_lines = []
        
        for line in lines:
            if line.strip() == raw_line.strip():
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
            
            new_lines.append(new_line)
        
        new_crontab = '\n'.join(new_lines)
        
        # ذخیره crontab جدید
        success, message = set_crontab(new_crontab, user)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Cron job {'enabled' if enabled else 'disabled'} successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to toggle cron job: {message}"
            }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@cron_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
def delete_cron_job(job_id):
    """حذف cron job"""
    try:
        # دریافت cron job
        job_response = get_cron_job(job_id)
        if job_response.status_code != 200:
            return job_response
        
        job_data = job_response.get_json()
        job = job_data.get('job')
        user = job.get('user', 'root')
        raw_line = job.get('raw', '')
        
        # دریافت crontab فعلی
        current_crontab = get_crontab(user)
        if current_crontab.startswith('Error') or current_crontab.startswith('Exception'):
            return jsonify({
                "status": "error",
                "message": f"Failed to get current crontab: {current_crontab}"
            }), 500
        
        # حذف خط مربوطه
        lines = current_crontab.split('\n')
        new_lines = [line for line in lines if line.strip() != raw_line.strip()]
        
        new_crontab = '\n'.join(new_lines)
        
        # ذخیره crontab جدید
        success, message = set_crontab(new_crontab, user)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Cron job deleted successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to delete cron job: {message}"
            }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@cron_bp.route("/system/status", methods=["GET"])
def get_cron_system_status():
    """دریافت وضعیت سیستم cron"""
    try:
        # بررسی سرویس cron
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'cron'],
                capture_output=True,
                text=True
            )
            cron_active = result.stdout.strip() == 'active'
        except:
            cron_active = False
        
        # بررسی تعداد processهای cron
        try:
            result = subprocess.run(
                ['pgrep', '-c', 'cron'],
                capture_output=True,
                text=True
            )
            cron_processes = int(result.stdout.strip() or 0)
        except:
            cron_processes = 0
        
        return jsonify({
            "status": "success",
            "cron_service": {
                "active": cron_active,
                "status": "فعال" if cron_active else "غیرفعال"
            },
            "processes": cron_processes,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@cron_bp.route("/validate", methods=["POST"])
def validate_cron_schedule():
    """اعتبارسنجی زمان‌بندی cron"""
    try:
        data = request.json
        schedule = data.get('schedule', {})
        
        errors = []
        
        # اعتبارسنجی دقیقه
        minute = schedule.get('minute', '*')
        if minute != '*' and not validate_cron_field(minute, 0, 59):
            errors.append("دقیقه نامعتبر است (0-59)")
        
        # اعتبارسنجی ساعت
        hour = schedule.get('hour', '*')
        if hour != '*' and not validate_cron_field(hour, 0, 23):
            errors.append("ساعت نامعتبر است (0-23)")
        
        # اعتبارسنجی روز ماه
        day_of_month = schedule.get('day_of_month', '*')
        if day_of_month != '*' and not validate_cron_field(day_of_month, 1, 31):
            errors.append("روز ماه نامعتبر است (1-31)")
        
        # اعتبارسنجی ماه
        month = schedule.get('month', '*')
        if month != '*' and not validate_cron_field(month, 1, 12):
            errors.append("ماه نامعتبر است (1-12)")
        
        # اعتبارسنجی روز هفته
        day_of_week = schedule.get('day_of_week', '*')
        if day_of_week != '*' and not validate_cron_field(day_of_week, 0, 7):
            errors.append("روز هفته نامعتبر است (0-7, 0=یکشنبه)")
        
        if errors:
            return jsonify({
                "status": "error",
                "errors": errors
            }), 400
        else:
            return jsonify({
                "status": "success",
                "message": "زمان‌بندی معتبر است"
            })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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