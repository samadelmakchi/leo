"""
ماژول مدیریت Ansible - Inventory - Backup - Logs - نسخه بهینه‌شده
"""

import os
import re
import yaml
import shutil
import tempfile
import subprocess
import glob
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file
from utils import (
    success_response,
    error_response,
    not_found_response,
    forbidden_response,
    validate_required_fields,
    sanitize_input,
    format_size,
    get_current_timestamp,
    time_ago,
    log_request_info,
    paginate,
    get_pagination_params
)

logger = logging.getLogger(__name__)

# ایجاد Blueprint برای Ansible
ansible_bp = Blueprint('ansible', __name__, url_prefix='/api/ansible')

# ============================================================================
# Configuration
# ============================================================================

# مسیرهای فایل‌ها
BASE_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = BASE_DIR / "config"
INVENTORY_FILE = CONFIG_DIR / "inventory.yml"
PLAYBOOKS_DIR = BASE_DIR / "playbooks"
DEFAULT_PLAYBOOK = PLAYBOOKS_DIR / "main.yml"
BACKUP_DIR = BASE_DIR / "backups"
LOGS_DIR = BASE_DIR / "logs"

# ایجاد پوشه‌های مورد نیاز
for directory in [CONFIG_DIR, PLAYBOOKS_DIR, BACKUP_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Decorators
# ============================================================================

def handle_ansible_errors(func):
    """دکوراتور برای مدیریت خطاهای Ansible"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            log_request_info()
            return func(*args, **kwargs)
        except yaml.YAMLError as e:
            logger.error(f"YAML error in {func.__name__}: {e}")
            return error_response(
                message="خطا در پردازش فایل YAML",
                status_code=400,
                details=str(e)[:200]
            )
        except FileNotFoundError as e:
            logger.error(f"File not found in {func.__name__}: {e}")
            return not_found_response(
                message="فایل مورد نظر یافت نشد",
                details=str(e)
            )
        except PermissionError as e:
            logger.error(f"Permission denied in {func.__name__}: {e}")
            return forbidden_response(
                message="دسترسی به فایل محدود شده است"
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error in {func.__name__}: {e}")
            return error_response(
                message=f"خطا در اجرای Ansible: {e.stderr[:200] if e.stderr else str(e)}",
                status_code=500
            )
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return error_response(
                message="خطا در عملیات Ansible",
                status_code=500,
                details=str(e)[:200]
            )
    return wrapper

# ============================================================================
# Inventory Management
# ============================================================================

def load_inventory():
    """بارگذاری فایل inventory"""
    try:
        if not INVENTORY_FILE.exists():
            # ایجاد inventory اولیه
            default_inventory = {
                "all": {
                    "hosts": {},
                    "vars": {
                        "ansible_user": "root",
                        "ansible_ssh_private_key_file": "~/.ssh/id_rsa",
                        "project_path": "/home/calibri",
                        "backup_path": "/home/calibri/backup",
                        "backup_keep_days": 7,
                        "backup_enabled": True
                    }
                }
            }
            save_inventory(default_inventory)
            return default_inventory
        
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
            
    except Exception as e:
        logger.error(f"Error loading inventory: {e}")
        raise

def save_inventory(data):
    """ذخیره فایل inventory"""
    try:
        # اعتبارسنجی ساختار
        if not isinstance(data, dict) or "all" not in data:
            raise ValueError("Inventory structure is invalid")
        
        # ذخیره با فرمت‌بندی مناسب
        with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, indent=2)
        
        logger.info("Inventory saved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error saving inventory: {e}")
        raise

def validate_customer_name(name):
    """اعتبارسنجی نام مشتری"""
    if not name or not isinstance(name, str):
        return False, "نام مشتری الزامی است و باید رشته باشد"
    
    if len(name) > 50:
        return False, "نام مشتری نمی‌تواند بیشتر از ۵۰ کاراکتر باشد"
    
    # فقط حروف، اعداد، خط تیره و زیرخط مجاز
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "نام مشتری فقط می‌تواند شامل حروف، اعداد، خط تیره و زیرخط باشد"
    
    return True, ""

# ============================================================================
# Routes for Inventory
# ============================================================================

@ansible_bp.route("/inventory", methods=["GET"])
@handle_ansible_errors
def api_inventory():
    """دریافت کل inventory"""
    inventory = load_inventory()
    
    return success_response(
        data=inventory,
        message="فایل inventory با موفقیت دریافت شد"
    )

@ansible_bp.route("/inventory/save", methods=["POST"])
@handle_ansible_errors
def api_inventory_save():
    """ذخیره تغییرات در inventory"""
    data = request.json
    
    # اعتبارسنجی فیلدهای الزامی
    is_valid, error_msg = validate_required_fields(data, ['customer'])
    if not is_valid:
        return error_response(message=error_msg, status_code=400)
    
    customer = data.get("customer")
    new_vars = data.get("vars", {})
    
    # اعتبارسنجی نام مشتری
    is_valid, error_msg = validate_customer_name(customer)
    if not is_valid:
        return error_response(message=error_msg, status_code=400)
    
    # بارگذاری inventory فعلی
    inventory = load_inventory()
    
    # اطمینان از ساختار inventory
    if "all" not in inventory:
        inventory["all"] = {}
    if "hosts" not in inventory["all"]:
        inventory["all"]["hosts"] = {}
    if "vars" not in inventory["all"]:
        inventory["all"]["vars"] = {}
    
    # اگر مشتری وجود ندارد، ایجاد آن
    if customer not in inventory["all"]["hosts"]:
        inventory["all"]["hosts"][customer] = {
            "vars": {
                "customer_name": customer,
                "customer_state": "active",
                "created_at": get_current_timestamp()
            }
        }
    
    # آپدیت متغیرها
    inventory["all"]["hosts"][customer]["vars"].update(new_vars)
    
    # ذخیره inventory
    save_inventory(inventory)
    
    logger.info(f"Inventory updated for customer: {customer}")
    
    return success_response(
        message="تغییرات با موفقیت ذخیره شد",
        data={
            "customer": customer,
            "updated_vars": list(new_vars.keys())
        }
    )

@ansible_bp.route("/inventory/customers", methods=["GET"])
@handle_ansible_errors
def api_inventory_customers():
    """دریافت لیست مشتریان"""
    inventory = load_inventory()
    
    customers = {}
    for host, data in inventory.get("all", {}).get("hosts", {}).items():
        vars_data = data.get("vars", {})
        customers[host] = {
            "id": host,
            "name": vars_data.get("customer_name", host),
            "state": vars_data.get("customer_state", "inactive"),
            "created_at": vars_data.get("created_at"),
            "backup_enabled": vars_data.get("backup_enabled", True),
            "modules": vars_data.get("modules", []),
            "last_backup": vars_data.get("last_backup")
        }
    
    # صفحه‌بندی
    page, per_page = get_pagination_params(request)
    customer_list = list(customers.values())
    paginated_customers, total, total_pages = paginate(customer_list, page, per_page)
    
    return success_response(
        data={
            "customers": paginated_customers,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            }
        },
        message="لیست مشتریان با موفقیت دریافت شد"
    )

@ansible_bp.route("/inventory/customer/<customer_name>", methods=["GET"])
@handle_ansible_errors
def api_inventory_customer(customer_name):
    """دریافت اطلاعات یک مشتری خاص"""
    inventory = load_inventory()
    
    if customer_name not in inventory.get("all", {}).get("hosts", {}):
        return not_found_response(
            message=f"مشتری '{customer_name}' یافت نشد"
        )
    
    customer_data = inventory["all"]["hosts"][customer_name]
    
    # ادغام متغیرهای global با متغیرهای مشتری
    global_vars = inventory.get("all", {}).get("vars", {})
    customer_vars = customer_data.get("vars", {})
    merged_vars = {**global_vars, **customer_vars}
    
    return success_response(
        data={
            "customer": customer_name,
            "vars": merged_vars,
            "raw_data": customer_data
        },
        message=f"اطلاعات مشتری '{customer_name}' دریافت شد"
    )

@ansible_bp.route("/inventory/customer/<customer_name>", methods=["DELETE"])
@handle_ansible_errors
def api_delete_customer(customer_name):
    """حذف یک مشتری از inventory"""
    inventory = load_inventory()
    
    if customer_name not in inventory.get("all", {}).get("hosts", {}):
        return not_found_response(
            message=f"مشتری '{customer_name}' یافت نشد"
        )
    
    # حذف مشتری
    del inventory["all"]["hosts"][customer_name]
    
    # ذخیره inventory
    save_inventory(inventory)
    
    logger.info(f"Customer deleted from inventory: {customer_name}")
    
    return success_response(
        message=f"مشتری '{customer_name}' با موفقیت حذف شد"
    )

# ============================================================================
# Ansible Playbook Execution
# ============================================================================

class AnsibleRunner:
    """کلاس مدیریت اجرای Ansible"""
    
    def __init__(self):
        self.running_processes = {}
        
    def run_playbook(self, customer, playbook=None, extra_vars=None, tags=None, check_mode=False):
        """اجرای پلی‌بوک Ansible"""
        if not playbook or not playbook.exists():
            playbook = DEFAULT_PLAYBOOK
        
        if not playbook.exists():
            raise FileNotFoundError(f"Playbook not found: {playbook}")
        
        # ساخت دستور Ansible
        cmd = [
            "ansible-playbook",
            "-i", str(INVENTORY_FILE),
            str(playbook),
            "--limit", customer
        ]
        
        if check_mode:
            cmd.append("--check")
        
        if extra_vars:
            extra_vars_str = " ".join(f'{k}="{v}"' for k, v in extra_vars.items())
            cmd.extend(["--extra-vars", extra_vars_str])
        
        if tags:
            cmd.extend(["--tags", tags])
        
        # اضافه کردن verbosity برای لاگ بهتر
        cmd.extend(["-v"])
        
        # اجرای دستور
        logger.info(f"Running Ansible command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        pid = process.pid
        self.running_processes[pid] = {
            "process": process,
            "customer": customer,
            "playbook": str(playbook),
            "start_time": get_current_timestamp(),
            "command": " ".join(cmd)
        }
        
        return pid
    
    def get_process_status(self, pid):
        """بررسی وضعیت یک process"""
        if pid not in self.running_processes:
            return None
        
        process_info = self.running_processes[pid]
        process = process_info["process"]
        
        # بررسی وضعیت process
        return_code = process.poll()
        
        if return_code is None:
            # هنوز در حال اجراست
            return {
                "status": "running",
                "pid": pid,
                "customer": process_info["customer"],
                "start_time": process_info["start_time"],
                "duration": self._calculate_duration(process_info["start_time"])
            }
        else:
            # تمام شده
            stdout, stderr = process.communicate()
            
            # حذف از لیست processes در حال اجرا
            del self.running_processes[pid]
            
            return {
                "status": "finished",
                "pid": pid,
                "customer": process_info["customer"],
                "return_code": return_code,
                "start_time": process_info["start_time"],
                "end_time": get_current_timestamp(),
                "duration": self._calculate_duration(process_info["start_time"]),
                "stdout": stdout[-5000:],  # فقط ۵۰۰۰ کاراکتر آخر
                "stderr": stderr[-5000:]   # فقط ۵۰۰۰ کاراکتر آخر
            }
    
    def _calculate_duration(self, start_time):
        """محاسبه مدت زمان اجرا"""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            now = datetime.now()
            duration = now - start_dt
            return str(duration)
        except:
            return "unknown"

# ایجاد نمونه runner
ansible_runner = AnsibleRunner()

# ============================================================================
# Routes for Ansible Playbooks
# ============================================================================

@ansible_bp.route("/run", methods=["POST"])
@handle_ansible_errors
def api_run():
    """اجرای پلی‌بوک Ansible"""
    data = request.json
    
    # اعتبارسنجی فیلدهای الزامی
    is_valid, error_msg = validate_required_fields(data, ['customer'])
    if not is_valid:
        return error_response(message=error_msg, status_code=400)
    
    customer = data.get("customer")
    playbook_name = data.get("playbook")
    extra_vars = data.get("extra_vars", {})
    tags = data.get("tags")
    check_mode = data.get("check_mode", False)
    
    # بررسی وجود مشتری در inventory
    inventory = load_inventory()
    if customer not in inventory.get("all", {}).get("hosts", {}):
        return error_response(
            message=f"مشتری '{customer}' در inventory وجود ندارد",
            status_code=404
        )
    
    # یافتن playbook
    playbook = None
    if playbook_name:
        playbook = PLAYBOOKS_DIR / f"{playbook_name}.yml"
        if not playbook.exists():
            playbook = PLAYBOOKS_DIR / playbook_name
    
    # اجرای playbook
    pid = ansible_runner.run_playbook(
        customer=customer,
        playbook=playbook,
        extra_vars=extra_vars,
        tags=tags,
        check_mode=check_mode
    )
    
    logger.info(f"Ansible playbook started for customer {customer}, PID: {pid}")
    
    return success_response(
        data={
            "pid": pid,
            "customer": customer,
            "playbook": playbook_name or "main.yml",
            "check_mode": check_mode
        },
        message="پلی‌بوک Ansible در حال اجراست"
    )

@ansible_bp.route("/run/status/<int:pid>", methods=["GET"])
@handle_ansible_errors
def api_run_status(pid):
    """بررسی وضعیت اجرای پلی‌بوک"""
    status = ansible_runner.get_process_status(pid)
    
    if not status:
        return error_response(
            message=f"Process با PID {pid} یافت نشد",
            status_code=404
        )
    
    return success_response(
        data=status,
        message="وضعیت اجرای پلی‌بوک"
    )

@ansible_bp.route("/run/list", methods=["GET"])
@handle_ansible_errors
def api_run_list():
    """لیست اجراهای اخیر"""
    # می‌توانید از دیتابیس یا فایل لاگ بخوانید
    # فعلاً فقط processes در حال اجرا را برمی‌گرداند
    
    running_processes = []
    for pid, info in ansible_runner.running_processes.items():
        status = ansible_runner.get_process_status(pid)
        if status:
            running_processes.append(status)
    
    # صفحه‌بندی
    page, per_page = get_pagination_params(request)
    paginated_processes, total, total_pages = paginate(running_processes, page, per_page)
    
    return success_response(
        data={
            "processes": paginated_processes,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            }
        },
        message="لیست اجراهای Ansible"
    )

@ansible_bp.route("/playbooks", methods=["GET"])
@handle_ansible_errors
def api_playbooks_list():
    """لیست playbook‌های موجود"""
    playbooks = []
    
    for playbook_file in PLAYBOOKS_DIR.glob("*.yml"):
        try:
            with open(playbook_file, "r", encoding="utf-8") as f:
                content = f.read()
                
                # استخراج نام و توضیحات از YAML
                name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                description_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
                
                playbooks.append({
                    "name": playbook_file.stem,
                    "filename": playbook_file.name,
                    "path": str(playbook_file),
                    "size": playbook_file.stat().st_size,
                    "size_formatted": format_size(playbook_file.stat().st_size),
                    "modified": datetime.fromtimestamp(playbook_file.stat().st_mtime).isoformat(),
                    "description": description_match.group(1) if description_match else "",
                    "display_name": name_match.group(1) if name_match else playbook_file.stem
                })
        except Exception as e:
            logger.warning(f"Error reading playbook {playbook_file}: {e}")
            continue
    
    return success_response(
        data={"playbooks": playbooks},
        message="لیست playbook‌های Ansible"
    )

# ============================================================================
# Backup Management
# ============================================================================

class BackupManager:
    """مدیریت بک‌اپ‌ها"""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
    
    def list_backups(self, customer=None):
        """لیست بک‌اپ‌های موجود"""
        backups = {}
        
        # اگر مشتری مشخص شده باشد
        if customer:
            customer_dir = self.backup_dir / customer
            if customer_dir.exists():
                backups[customer] = self._get_customer_backups(customer_dir, customer)
            return backups
        
        # همه مشتریان
        for customer_dir in self.backup_dir.iterdir():
            if customer_dir.is_dir():
                customer_name = customer_dir.name
                backups[customer_name] = self._get_customer_backups(customer_dir, customer_name)
        
        return backups
    
    def _get_customer_backups(self, customer_dir, customer_name):
        """دریافت بک‌اپ‌های یک مشتری"""
        customer_backups = []
        
        for backup_dir in customer_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                try:
                    # پارس کردن تاریخ از نام پوشه
                    dir_name = backup_dir.name
                    if dir_name.startswith("backup_"):
                        date_str = dir_name[7:]  # حذف "backup_"
                        
                        backup_info = {
                            "name": dir_name,
                            "path": str(backup_dir),
                            "date": date_str,
                            "timestamp": backup_dir.stat().st_mtime,
                            "datetime": datetime.fromtimestamp(backup_dir.stat().st_mtime).isoformat(),
                            "time_ago": time_ago(backup_dir.stat().st_mtime),
                            "files": self._scan_backup_files(backup_dir)
                        }
                        
                        customer_backups.append(backup_info)
                except Exception as e:
                    logger.warning(f"Error processing backup directory {backup_dir}: {e}")
                    continue
        
        # مرتب کردن بر اساس تاریخ (جدیدترین اول)
        customer_backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # محاسبه مجموع اطلاعات
        total_size = sum(f["size"] for b in customer_backups for f in b["files"])
        
        return {
            "backups": customer_backups,
            "total_backups": len(customer_backups),
            "total_size": total_size,
            "total_size_formatted": format_size(total_size)
        }
    
    def _scan_backup_files(self, backup_dir):
        """اسکن فایل‌های بک‌اپ"""
        files = []
        
        for file_path in backup_dir.rglob("*"):
            if file_path.is_file():
                try:
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path.relative_to(backup_dir)),
                        "size": file_path.stat().st_size,
                        "size_formatted": format_size(file_path.stat().st_size),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "type": self._get_file_type(file_path)
                    }
                    files.append(file_info)
                except Exception as e:
                    logger.debug(f"Error scanning file {file_path}: {e}")
        
        return files
    
    def _get_file_type(self, file_path):
        """تشخیص نوع فایل"""
        name = file_path.name.lower()
        
        if name.endswith('.sql.gz') or name.endswith('.sql'):
            return "database"
        elif name.endswith('.tar.gz') or name.endswith('.tgz'):
            return "archive"
        elif name.endswith('.log'):
            return "log"
        elif name.endswith('.yml') or name.endswith('.yaml'):
            return "config"
        else:
            return "other"

# ایجاد نمونه BackupManager
backup_manager = BackupManager()

# ============================================================================
# Routes for Backup Management
# ============================================================================

@ansible_bp.route("/backups", methods=["GET"])
@handle_ansible_errors
def api_backup_list():
    """دریافت لیست بک‌اپ‌های موجود"""
    customer = request.args.get("customer")
    
    backups = backup_manager.list_backups(customer)
    
    return success_response(
        data={
            "backups": backups,
            "backup_dir": str(BACKUP_DIR),
            "timestamp": get_current_timestamp()
        },
        message="لیست بک‌اپ‌ها با موفقیت دریافت شد"
    )

@ansible_bp.route("/backups/delete", methods=["POST"])
@handle_ansible_errors
def api_backup_delete():
    """حذف یک بک‌اپ"""
    data = request.json
    
    # اعتبارسنجی فیلدهای الزامی
    is_valid, error_msg = validate_required_fields(data, ['customer', 'backup_name'])
    if not is_valid:
        return error_response(message=error_msg, status_code=400)
    
    customer = data.get("customer")
    backup_name = data.get("backup_name")
    
    backup_path = BACKUP_DIR / customer / backup_name
    
    if not backup_path.exists():
        return not_found_response(
            message=f"بک‌اپ '{backup_name}' برای مشتری '{customer}' یافت نشد"
        )
    
    try:
        # محاسبه سایز قبل از حذف
        total_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
        
        # حذف پوشه بک‌اپ
        shutil.rmtree(backup_path)
        
        logger.info(f"Backup deleted: {customer}/{backup_name}, size: {format_size(total_size)}")
        
        return success_response(
            data={
                "customer": customer,
                "backup_name": backup_name,
                "deleted_size": total_size,
                "deleted_size_formatted": format_size(total_size)
            },
            message=f"بک‌اپ '{backup_name}' با موفقیت حذف شد"
        )
        
    except Exception as e:
        logger.error(f"Error deleting backup {backup_path}: {e}")
        return error_response(
            message=f"خطا در حذف بک‌اپ: {str(e)}",
            status_code=500
        )

@ansible_bp.route("/backups/download", methods=["GET"])
@handle_ansible_errors
def api_backup_download():
    """دانلود یک فایل بک‌اپ"""
    customer = request.args.get("customer")
    backup_name = request.args.get("backup_name")
    file_name = request.args.get("file_name")
    
    if not customer or not backup_name or not file_name:
        return error_response(
            message="پارامترهای customer, backup_name و file_name الزامی هستند",
            status_code=400
        )
    
    file_path = BACKUP_DIR / customer / backup_name / file_name
    
    if not file_path.exists():
        return not_found_response(
            message="فایل مورد نظر یافت نشد"
        )
    
    # اعتبارسنجی که فایل در مسیر بک‌اپ است
    try:
        file_path.resolve().relative_to(BACKUP_DIR.resolve())
    except ValueError:
        return forbidden_response(
            message="دسترسی به فایل مجاز نیست"
        )
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=f"{customer}_{backup_name}_{file_name}"
    )

@ansible_bp.route("/backups/clean", methods=["POST"])
@handle_ansible_errors
def api_backup_clean():
    """پاک‌سازی بک‌اپ‌های قدیمی"""
    data = request.json or {}
    customer = data.get("customer")
    keep_days = data.get("keep_days", 7)
    
    deleted_count = 0
    deleted_size = 0
    results = []
    
    # تعیین پوشه‌های مورد بررسی
    if customer:
        customer_dirs = [BACKUP_DIR / customer]
    else:
        customer_dirs = [d for d in BACKUP_DIR.iterdir() if d.is_dir()]
    
    for customer_dir in customer_dirs:
        if not customer_dir.exists():
            continue
        
        # خواندن تنظیمات از inventory
        inventory = load_inventory()
        customer_name = customer_dir.name
        
        # استفاده از تنظیمات مشتری یا پیش‌فرض
        customer_keep_days = inventory.get("all", {}).get("hosts", {}).get(
            customer_name, {}
        ).get("vars", {}).get("backup_keep_days", keep_days)
        
        cutoff_time = datetime.now().timestamp() - (customer_keep_days * 24 * 3600)
        
        for backup_dir in customer_dir.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                try:
                    if backup_dir.stat().st_mtime < cutoff_time:
                        # محاسبه سایز
                        dir_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
                        
                        # حذف
                        shutil.rmtree(backup_dir)
                        
                        deleted_count += 1
                        deleted_size += dir_size
                        
                        results.append({
                            "customer": customer_name,
                            "backup": backup_dir.name,
                            "size": dir_size,
                            "size_formatted": format_size(dir_size),
                            "age_days": int((datetime.now().timestamp() - backup_dir.stat().st_mtime) / (24 * 3600))
                        })
                        
                        logger.info(f"Cleaned old backup: {customer_name}/{backup_dir.name}")
                        
                except Exception as e:
                    logger.warning(f"Error cleaning backup {backup_dir}: {e}")
    
    return success_response(
        data={
            "deleted_count": deleted_count,
            "deleted_size": deleted_size,
            "deleted_size_formatted": format_size(deleted_size),
            "results": results,
            "keep_days": keep_days
        },
        message=f"{deleted_count} بک‌اپ قدیمی حذف شد"
    )

# ============================================================================
# Log Management
# ============================================================================

class LogManager:
    """مدیریت لاگ‌ها"""
    
    def __init__(self):
        self.log_dir = LOGS_DIR
    
    def list_logs(self):
        """لیست لاگ‌های موجود"""
        logs = {
            "ansible": [],
            "backup": [],
            "system": []
        }
        
        if not self.log_dir.exists():
            return logs
        
        for log_file in self.log_dir.rglob("*.log"):
            try:
                log_info = self._get_log_info(log_file)
                
                # دسته‌بندی لاگ‌ها
                if "ansible" in log_file.name.lower() or "playbook" in log_file.name.lower():
                    logs["ansible"].append(log_info)
                elif "backup" in log_file.name.lower():
                    logs["backup"].append(log_info)
                else:
                    logs["system"].append(log_info)
                    
            except Exception as e:
                logger.warning(f"Error processing log file {log_file}: {e}")
        
        return logs
    
    def _get_log_info(self, log_file):
        """دریافت اطلاعات یک فایل لاگ"""
        stat = log_file.stat()
        
        # تحلیل محتوای لاگ
        analysis = self._analyze_log_file(log_file)
        
        return {
            "name": log_file.name,
            "path": str(log_file),
            "size": stat.st_size,
            "size_formatted": format_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "time_ago": time_ago(stat.st_mtime),
            "line_count": analysis.get("total_lines", 0),
            "analysis": analysis
        }
    
    def _analyze_log_file(self, log_file, max_lines=1000):
        """تحلیل فایل لاگ"""
        analysis = {
            "total_lines": 0,
            "error_count": 0,
            "warning_count": 0,
            "success_count": 0,
            "last_entries": [],
            "error_patterns": []
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            analysis["total_lines"] = len(lines)
            
            # تحلیل خطوط
            error_patterns = {}
            for i, line in enumerate(lines[-100:]):  # فقط ۱۰۰ خط آخر
                line_lower = line.lower()
                
                if "error" in line_lower:
                    analysis["error_count"] += 1
                    
                    # استخراج pattern خطا
                    error_match = re.search(r'error[:\s]+([^\n]+)', line, re.IGNORECASE)
                    if error_match:
                        error_text = error_match.group(1)[:50]
                        error_patterns[error_text] = error_patterns.get(error_text, 0) + 1
                        
                elif "warning" in line_lower:
                    analysis["warning_count"] += 1
                elif "success" in line_lower or "completed" in line_lower:
                    analysis["success_count"] += 1
            
            # ذخیره خطوط آخر
            analysis["last_entries"] = [line.strip() for line in lines[-10:] if line.strip()]
            
            # محبوب‌ترین خطاها
            analysis["error_patterns"] = [
                {"pattern": pattern, "count": count}
                for pattern, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
        except Exception as e:
            logger.warning(f"Error analyzing log file {log_file}: {e}")
        
        return analysis
    
    def read_log(self, log_path, lines=100, tail=True):
        """خواندن فایل لاگ"""
        try:
            log_file = Path(log_path)
            if not log_file.exists():
                raise FileNotFoundError(f"Log file not found: {log_path}")
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                if tail:
                    # خواندن از انتها
                    all_lines = f.readlines()
                    start = max(0, len(all_lines) - lines)
                    content_lines = all_lines[start:]
                else:
                    # خواندن از ابتدا
                    content_lines = []
                    for i, line in enumerate(f):
                        if i >= lines:
                            break
                        content_lines.append(line)
            
            content = ''.join(content_lines)
            
            # تحلیل خطوط خوانده شده
            lines_analysis = self._analyze_log_lines(content_lines)
            
            return {
                "content": content,
                "lines_count": len(content_lines),
                "analysis": lines_analysis
            }
            
        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")
            raise
    
    def _analyze_log_lines(self, lines):
        """تحلیل خطوط لاگ"""
        analysis = {
            "errors": [],
            "warnings": [],
            "infos": [],
            "timestamps": []
        }
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            line_number = i + 1
            
            if "error" in line_lower:
                analysis["errors"].append({
                    "line": line_number,
                    "content": line.strip()[:200]
                })
            elif "warning" in line_lower:
                analysis["warnings"].append({
                    "line": line_number,
                    "content": line.strip()[:200]
                })
            
            # استخراج timestamp
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                analysis["timestamps"].append({
                    "line": line_number,
                    "timestamp": timestamp_match.group(1)
                })
        
        return analysis

# ایجاد نمونه LogManager
log_manager = LogManager()

# ============================================================================
# Routes for Log Management
# ============================================================================

@ansible_bp.route("/logs", methods=["GET"])
@handle_ansible_errors
def api_logs_list():
    """دریافت لیست لاگ‌های موجود"""
    logs = log_manager.list_logs()
    
    # محاسبه آمار کلی
    total_logs = sum(len(category) for category in logs.values())
    total_size = sum(
        log["size"] for category in logs.values() for log in category
    )
    
    return success_response(
        data={
            "logs": logs,
            "stats": {
                "total_logs": total_logs,
                "total_size": total_size,
                "total_size_formatted": format_size(total_size),
                "log_dir": str(LOGS_DIR)
            }
        },
        message="لیست لاگ‌ها با موفقیت دریافت شد"
    )

@ansible_bp.route("/logs/view", methods=["GET"])
@handle_ansible_errors
def api_logs_view():
    """مشاهده محتوای یک لاگ"""
    log_path = request.args.get("path")
    lines = int(request.args.get("lines", 100))
    tail = request.args.get("tail", "true").lower() == "true"
    
    if not log_path:
        return error_response(
            message="پارامتر path الزامی است",
            status_code=400
        )
    
    # اعتبارسنجی مسیر لاگ
    log_file = Path(log_path)
    if not log_file.exists() or not log_file.is_file():
        return not_found_response(
            message="فایل لاگ یافت نشد"
        )
    
    try:
        # خواندن لاگ
        log_content = log_manager.read_log(log_path, lines, tail)
        
        return success_response(
            data={
                "path": log_path,
                "filename": log_file.name,
                "content": log_content["content"],
                "lines_count": log_content["lines_count"],
                "analysis": log_content["analysis"],
                "file_info": {
                    "size": log_file.stat().st_size,
                    "size_formatted": format_size(log_file.stat().st_size),
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                }
            },
            message="محتوای لاگ دریافت شد"
        )
        
    except Exception as e:
        return error_response(
            message=f"خطا در خواندن لاگ: {str(e)}",
            status_code=500
        )

@ansible_bp.route("/logs/download", methods=["GET"])
@handle_ansible_errors
def api_logs_download():
    """دانلود فایل لاگ"""
    log_path = request.args.get("path")
    
    if not log_path:
        return error_response(
            message="پارامتر path الزامی است",
            status_code=400
        )
    
    log_file = Path(log_path)
    
    if not log_file.exists():
        return not_found_response(
            message="فایل لاگ یافت نشد"
        )
    
    # اطمینان از اینکه فایل در مسیر logs است
    try:
        log_file.resolve().relative_to(LOGS_DIR.resolve())
    except ValueError:
        return forbidden_response(
            message="دسترسی به فایل مجاز نیست"
        )
    
    return send_file(
        str(log_file),
        as_attachment=True,
        download_name=log_file.name
    )

@ansible_bp.route("/logs/clear", methods=["POST"])
@handle_ansible_errors
def api_logs_clear():
    """پاک کردن فایل لاگ"""
    data = request.json
    
    if not data or "path" not in data:
        return error_response(
            message="پارامتر path الزامی است",
            status_code=400
        )
    
    log_path = data.get("path")
    log_file = Path(log_path)
    
    if not log_file.exists():
        return not_found_response(
            message="فایل لاگ یافت نشد"
        )
    
    try:
        # ذخیره سایز قبل از پاک کردن
        file_size = log_file.stat().st_size
        
        # پاک کردن محتوای فایل
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"# Log cleared at {datetime.now().isoformat()}\n")
            f.write(f"# Previous size: {format_size(file_size)}\n")
        
        logger.info(f"Log file cleared: {log_path}, previous size: {format_size(file_size)}")
        
        return success_response(
            data={
                "path": log_path,
                "previous_size": file_size,
                "previous_size_formatted": format_size(file_size)
            },
            message="فایل لاگ پاک شد"
        )
        
    except Exception as e:
        logger.error(f"Error clearing log file {log_path}: {e}")
        return error_response(
            message=f"خطا در پاک کردن لاگ: {str(e)}",
            status_code=500
        )

@ansible_bp.route("/logs/analyze", methods=["GET"])
@handle_ansible_errors
def api_logs_analyze():
    """تحلیل لاگ‌های سیستم"""
    days = int(request.args.get("days", 1))
    log_type = request.args.get("type", "all")  # all, error, warning
    
    analysis = {
        "timestamp": get_current_timestamp(),
        "period_days": days,
        "log_type": log_type,
        "summary": {
            "total_logs": 0,
            "total_errors": 0,
            "total_warnings": 0,
            "largest_log": None,
            "recent_logs": []
        },
        "error_patterns": [],
        "warning_patterns": []
    }
    
    try:
        logs = log_manager.list_logs()
        
        for category, log_list in logs.items():
            for log_info in log_list:
                analysis["summary"]["total_logs"] += 1
                analysis["summary"]["total_errors"] += log_info["analysis"].get("error_count", 0)
                analysis["summary"]["total_warnings"] += log_info["analysis"].get("warning_count", 0)
                
                # پیدا کردن بزرگترین لاگ
                if (not analysis["summary"]["largest_log"] or 
                    log_info["size"] > analysis["summary"]["largest_log"]["size"]):
                    analysis["summary"]["largest_log"] = {
                        "name": log_info["name"],
                        "size": log_info["size"],
                        "size_formatted": log_info["size_formatted"],
                        "category": category
                    }
        
        return success_response(
            data=analysis,
            message="تحلیل لاگ‌های سیستم"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing logs: {e}")
        return error_response(
            message=f"خطا در تحلیل لاگ‌ها: {str(e)}",
            status_code=500
        )

# ============================================================================
# Utility Routes
# ============================================================================

@ansible_bp.route("/health", methods=["GET"])
@handle_ansible_errors
def api_ansible_health():
    """بررسی سلامت ماژول Ansible"""
    health_status = {
        "timestamp": get_current_timestamp(),
        "status": "healthy",
        "components": {}
    }
    
    # بررسی inventory
    try:
        inventory = load_inventory()
        health_status["components"]["inventory"] = {
            "status": "healthy",
            "path": str(INVENTORY_FILE),
            "exists": INVENTORY_FILE.exists(),
            "customer_count": len(inventory.get("all", {}).get("hosts", {}))
        }
    except Exception as e:
        health_status["components"]["inventory"] = {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
        health_status["status"] = "unhealthy"
    
    # بررسی playbooks
    try:
        playbooks = list(PLAYBOOKS_DIR.glob("*.yml"))
        health_status["components"]["playbooks"] = {
            "status": "healthy",
            "path": str(PLAYBOOKS_DIR),
            "exists": PLAYBOOKS_DIR.exists(),
            "count": len(playbooks),
            "main_playbook_exists": DEFAULT_PLAYBOOK.exists()
        }
    except Exception as e:
        health_status["components"]["playbooks"] = {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
        health_status["status"] = "unhealthy"
    
    # بررسی backup directory
    try:
        health_status["components"]["backup"] = {
            "status": "healthy",
            "path": str(BACKUP_DIR),
            "exists": BACKUP_DIR.exists(),
            "writable": os.access(BACKUP_DIR, os.W_OK)
        }
    except Exception as e:
        health_status["components"]["backup"] = {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
        health_status["status"] = "unhealthy"
    
    # بررسی logs directory
    try:
        health_status["components"]["logs"] = {
            "status": "healthy",
            "path": str(LOGS_DIR),
            "exists": LOGS_DIR.exists(),
            "writable": os.access(LOGS_DIR, os.W_OK)
        }
    except Exception as e:
        health_status["components"]["logs"] = {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
        health_status["status"] = "unhealthy"
    
    # بررسی دسترسی Ansible
    try:
        result = subprocess.run(
            ["ansible", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        health_status["components"]["ansible"] = {
            "status": "healthy" if result.returncode == 0 else "unhealthy",
            "installed": result.returncode == 0,
            "version": result.stdout.split('\n')[0] if result.stdout else "unknown"
        }
    except Exception as e:
        health_status["components"]["ansible"] = {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
        health_status["status"] = "unhealthy"
    
    return jsonify(health_status), 200 if health_status["status"] == "healthy" else 503