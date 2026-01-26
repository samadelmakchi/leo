"""
ماژول مدیریت Ansible - Inventory - Backup - Logs
"""

import os
import re
import yaml
from datetime import datetime
import subprocess
from flask import Blueprint, jsonify, request, send_file

# ایجاد Blueprint برای Ansible
ansible_bp = Blueprint('ansible', __name__, url_prefix='/api')

# مسیرهای فایل‌ها
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INVENTORY_FILE = os.path.join(BASE_DIR, "inventory.yml")
PLAYBOOK_FILE = os.path.join(BASE_DIR, "playbook.yml")

def load_inventory():
    """بارگذاری فایل inventory"""
    try:
        with open(INVENTORY_FILE, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"all": {"hosts": {}, "vars": {}}}
    except Exception as e:
        raise Exception(f"خطا در خواندن فایل inventory: {str(e)}")

def save_inventory(data):
    """ذخیره فایل inventory"""
    try:
        with open(INVENTORY_FILE, "w") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        raise Exception(f"خطا در ذخیره فایل inventory: {str(e)}")

# ============================================================================
# Routes for Inventory
# ============================================================================

@ansible_bp.route("/inventory", methods=["GET"])
def api_inventory():
    """دریافت کل inventory"""
    try:
        inventory = load_inventory()
        return jsonify(inventory)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/inventory/save", methods=["POST"])
def api_inventory_save():
    """ذخیره تغییرات در inventory"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "دیتا ارسال نشده است"
            }), 400
        
        customer = data.get("customer")
        new_vars = data.get("vars", {})
        
        if not customer:
            return jsonify({
                "status": "error",
                "message": "نام مشتری الزامی است"
            }), 400
        
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
            inventory["all"]["hosts"][customer] = {"vars": {}}
        
        # اگر vars برای مشتری وجود ندارد، ایجاد آن
        if "vars" not in inventory["all"]["hosts"][customer]:
            inventory["all"]["hosts"][customer]["vars"] = {}
        
        # آپدیت متغیرها
        inventory["all"]["hosts"][customer]["vars"].update(new_vars)
        
        # ذخیره inventory
        save_inventory(inventory)
        
        return jsonify({
            "status": "success",
            "message": "تغییرات با موفقیت ذخیره شد"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/inventory/customers", methods=["GET"])
def api_inventory_customers():
    """دریافت لیست مشتریان"""
    try:
        inventory = load_inventory()
        customers = {}
        
        for host, data in inventory.get("all", {}).get("hosts", {}).items():
            customers[host] = {
                "name": data.get("vars", {}).get("customer_name", host),
                "state": data.get("vars", {}).get("customer_state", "down")
            }
        
        return jsonify({
            "status": "success",
            "customers": customers
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/inventory/customer/<customer_name>", methods=["GET"])
def api_inventory_customer(customer_name):
    """دریافت اطلاعات یک مشتری خاص"""
    try:
        inventory = load_inventory()
        
        if customer_name not in inventory.get("all", {}).get("hosts", {}):
            return jsonify({
                "status": "error",
                "message": f"مشتری '{customer_name}' یافت نشد"
            }), 404
        
        customer_data = inventory["all"]["hosts"][customer_name]
        
        # ادغام متغیرهای global با متغیرهای مشتری
        global_vars = inventory.get("all", {}).get("vars", {})
        customer_vars = customer_data.get("vars", {})
        merged_vars = {**global_vars, **customer_vars}
        
        return jsonify({
            "status": "success",
            "customer": customer_name,
            "vars": merged_vars,
            "raw_data": customer_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================================================
# Routes for Ansible Playbooks
# ============================================================================

@ansible_bp.route("/run", methods=["POST"])
def api_run():
    """اجرای پلی‌بوک Ansible"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "دیتا ارسال نشده است"
            }), 400
        
        customer = data.get("customer")
        
        if not customer:
            return jsonify({
                "status": "error",
                "message": "نام مشتری الزامی است"
            }), 400
        
        extra_vars = data.get("extra_vars", {})
        tags = data.get("tags")
        
        # ساخت دستور Ansible
        cmd = [
            "ansible-playbook",
            "-i", INVENTORY_FILE,
            PLAYBOOK_FILE,
            "--limit", customer
        ]
        
        # اضافه کردن extra_vars اگر وجود دارد
        if extra_vars:
            extra_vars_str = " ".join(f"{k}='{v}'" for k, v in extra_vars.items())
            cmd += ["--extra-vars", extra_vars_str]
        
        # اضافه کردن tags اگر وجود دارد
        if tags:
            cmd += ["--tags", tags]
        
        # اجرای دستور در background
        process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # ذخیره PID برای رهگیری
        pid = process.pid
        
        return jsonify({
            "status": "started",
            "pid": pid,
            "customer": customer,
            "command": " ".join(cmd),
            "message": "پلی‌بوک در حال اجرا است"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/run/status/<int:pid>", methods=["GET"])
def api_run_status(pid):
    """بررسی وضعیت اجرای پلی‌بوک"""
    try:
        # بررسی اینکه process هنوز در حال اجراست
        import psutil
        try:
            process = psutil.Process(pid)
            status = process.status()
            
            return jsonify({
                "status": "running",
                "pid": pid,
                "process_status": status
            })
        except psutil.NoSuchProcess:
            return jsonify({
                "status": "finished",
                "pid": pid,
                "message": "پروسه به پایان رسیده است"
            })
            
    except ImportError:
        return jsonify({
            "status": "unknown",
            "pid": pid,
            "message": "امکان بررسی وضعیت وجود ندارد (psutil نصب نشده)"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/run/list", methods=["GET"])
def api_run_list():
    """لیست اجراهای اخیر"""
    # این endpoint می‌تواند لاگ‌های اجرا را برگرداند
    return jsonify({
        "status": "success",
        "runs": [],
        "message": "این endpoint نیاز به پیاده‌سازی دارد"
    })

# ============================================================================
# Helper Functions
# ============================================================================

def validate_inventory_structure(inventory):
    """اعتبارسنجی ساختار inventory"""
    required_keys = ["all"]
    
    for key in required_keys:
        if key not in inventory:
            return False, f"کلید '{key}' در inventory یافت نشد"
    
    return True, "ساختار معتبر است"

def get_customer_vars(customer_name):
    """دریافت متغیرهای یک مشتری با ادغام global vars"""
    inventory = load_inventory()
    
    if customer_name not in inventory.get("all", {}).get("hosts", {}):
        return {}
    
    global_vars = inventory.get("all", {}).get("vars", {})
    customer_vars = inventory["all"]["hosts"][customer_name].get("vars", {})
    
    return {**global_vars, **customer_vars}

def get_available_modules():
    """دریافت لیست ماژول‌های موجود"""
    # این لیست می‌تواند از inventory یا فایل config خوانده شود
    return ["gateway", "portal", "portal_frontend", "lms", "file"]

# ============================================================================
# Routes for Backup Management
# ============================================================================

@ansible_bp.route("/backup/list", methods=["GET"])
def api_backup_list():
    """دریافت لیست بک‌اپ‌های موجود"""
    try:
        inventory = load_inventory()
        backup_path = inventory.get("all", {}).get("vars", {}).get("backup_path", "/home/calibri/backup")
        project_path = inventory.get("all", {}).get("vars", {}).get("project_path", "/home/calibri")
        
        # اگر backup_path تعریف نشده، از project_path استفاده کن
        if not os.path.isabs(backup_path):
            backup_path = os.path.join(project_path, backup_path)
        
        backup_data = {}
        
        # بررسی پوشه backup
        if not os.path.exists(backup_path):
            return jsonify({
                "status": "success",
                "message": "پوشه بک‌اپ یافت نشد",
                "backup_path": backup_path,
                "backups": {}
            })
        
        # لیست مشتریان از inventory
        customers = inventory.get("all", {}).get("hosts", {}).keys()
        
        for customer in customers:
            customer_backup_dir = os.path.join(backup_path, customer)
            
            if os.path.exists(customer_backup_dir) and os.path.isdir(customer_backup_dir):
                customer_backups = []
                
                # لیست پوشه‌های بک‌اپ
                for item in os.listdir(customer_backup_dir):
                    item_path = os.path.join(customer_backup_dir, item)
                    
                    if os.path.isdir(item_path) and item.startswith("202"):
                        try:
                            # پارس کردن تاریخ از نام پوشه
                            date_parts = item.split('-')
                            if len(date_parts) >= 3:
                                date_str = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
                                time_str = f"{date_parts[3]}:{date_parts[4]}:{date_parts[5]}" if len(date_parts) >= 6 else "00:00:00"
                                
                                # محاسبه سایز پوشه
                                total_size = 0
                                file_count = 0
                                backup_files = []
                                
                                for root, dirs, files in os.walk(item_path):
                                    for file in files:
                                        if not (file.endswith('.sh') or 'backup_' in file):
                                            file_path = os.path.join(root, file)
                                            file_size = os.path.getsize(file_path)
                                            total_size += file_size
                                            file_count += 1
                                            
                                            # جزئیات فایل
                                            rel_path = os.path.relpath(file_path, item_path)
                                            backup_files.append({
                                                "name": file,
                                                "path": rel_path,
                                                "size": file_size,
                                                "size_formatted": f"{file_size / 1024:.2f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.2f} MB"
                                            })
                                
                                # مرتب کردن فایل‌ها بر اساس نوع
                                database_files = [f for f in backup_files if f["name"].endswith('.sql.gz')]
                                volume_files = [f for f in backup_files if f["name"].endswith('.tar.gz')]
                                other_files = [f for f in backup_files if f not in database_files + volume_files]
                                
                                customer_backups.append({
                                    "name": item,
                                    "path": item_path,
                                    "date": date_str,
                                    "time": time_str,
                                    "full_date": f"{date_str} {time_str}",
                                    "timestamp": os.path.getmtime(item_path),
                                    "size": total_size,
                                    "size_formatted": f"{total_size / (1024*1024):.2f} MB",
                                    "file_count": file_count,
                                    "files": {
                                        "databases": database_files,
                                        "volumes": volume_files,
                                        "others": other_files
                                    }
                                })
                        except Exception as e:
                            print(f"Error processing backup folder {item}: {e}")
                            continue
                
                # مرتب کردن بر اساس تاریخ (جدیدترین اول)
                customer_backups.sort(key=lambda x: x["timestamp"], reverse=True)
                
                # محاسبه مجموع اطلاعات
                total_backups = len(customer_backups)
                total_size_all = sum(b["size"] for b in customer_backups)
                
                backup_data[customer] = {
                    "name": inventory["all"]["hosts"][customer].get("vars", {}).get("customer_name", customer),
                    "backup_enabled": inventory["all"]["hosts"][customer].get("vars", {}).get("customer_backup_enabled", inventory.get("all", {}).get("vars", {}).get("customer_backup_enabled", False)),
                    "backup_path": customer_backup_dir,
                    "backups": customer_backups,
                    "total_backups": total_backups,
                    "total_size": total_size_all,
                    "total_size_formatted": f"{total_size_all / (1024*1024*1024):.2f} GB" if total_size_all > 1024*1024*1024 else f"{total_size_all / (1024*1024):.2f} MB"
                }
        
        return jsonify({
            "status": "success",
            "backup_path": backup_path,
            "customers": backup_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/backup/delete", methods=["POST"])
def api_backup_delete():
    """حذف یک بک‌اپ"""
    try:
        data = request.json
        customer = data.get("customer")
        backup_name = data.get("backup_name")
        
        if not customer or not backup_name:
            return jsonify({
                "status": "error",
                "message": "مشتری و نام بک‌اپ الزامی است"
            }), 400
        
        inventory = load_inventory()
        backup_path = inventory.get("all", {}).get("vars", {}).get("backup_path", "/home/calibri/backup")
        project_path = inventory.get("all", {}).get("vars", {}).get("project_path", "/home/calibri")
        
        if not os.path.isabs(backup_path):
            backup_path = os.path.join(project_path, backup_path)
        
        backup_dir = os.path.join(backup_path, customer, backup_name)
        
        if not os.path.exists(backup_dir):
            return jsonify({
                "status": "error",
                "message": f"بک‌اپ {backup_name} برای مشتری {customer} یافت نشد"
            }), 404
        
        # حذف پوشه بک‌اپ
        import shutil
        shutil.rmtree(backup_dir)
        
        return jsonify({
            "status": "success",
            "message": f"بک‌اپ {backup_name} با موفقیت حذف شد"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/backup/download", methods=["GET"])
def api_backup_download():
    """دانلود یک فایل بک‌اپ"""
    try:
        customer = request.args.get("customer")
        backup_name = request.args.get("backup_name")
        file_name = request.args.get("file_name")
        
        if not customer or not backup_name or not file_name:
            return jsonify({
                "status": "error",
                "message": "پارامترهای لازم ارسال نشده"
            }), 400
        
        inventory = load_inventory()
        backup_path = inventory.get("all", {}).get("vars", {}).get("backup_path", "/home/calibri/backup")
        project_path = inventory.get("all", {}).get("vars", {}).get("project_path", "/home/calibri")
        
        if not os.path.isabs(backup_path):
            backup_path = os.path.join(project_path, backup_path)
        
        file_path = os.path.join(backup_path, customer, backup_name, file_name)
        
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": "فایل یافت نشد"
            }), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/backup/run-all", methods=["POST"])
def api_backup_run_all():
    """اجرای بک‌اپ برای همه مشتریان"""
    try:
        inventory = load_inventory()
        customers = inventory.get("all", {}).get("hosts", {})
        
        # فقط مشتریانی که بک‌اپ فعال دارند
        active_customers = []
        for customer, data in customers.items():
            if data.get("vars", {}).get("customer_backup_enabled", 
                   inventory.get("all", {}).get("vars", {}).get("customer_backup_enabled", False)):
                active_customers.append(customer)
        
        # در اینجا می‌توانید دستورات اجرای بک‌اپ را اضافه کنید
        # فعلاً فقط نمونه است
        
        return jsonify({
            "status": "success",
            "message": f"بک‌اپ برای {len(active_customers)} مشتری فعال در صف اجرا قرار گرفت",
            "active_customers": active_customers
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/backup/clean", methods=["POST"])
def api_backup_clean():
    """پاک‌سازی بک‌اپ‌های قدیمی"""
    try:
        inventory = load_inventory()
        backup_path = inventory.get("all", {}).get("vars", {}).get("backup_path", "/home/calibri/backup")
        project_path = inventory.get("all", {}).get("vars", {}).get("project_path", "/home/calibri")
        
        if not os.path.isabs(backup_path):
            backup_path = os.path.join(project_path, backup_path)
        
        deleted_count = 0
        
        import shutil
        import glob
        
        for customer_dir in glob.glob(os.path.join(backup_path, "*")):
            if os.path.isdir(customer_dir):
                customer = os.path.basename(customer_dir)
                keep = inventory.get("all", {}).get("hosts", {}).get(customer, {}).get("vars", {}).get("customer_backup_keep", 
                       inventory.get("all", {}).get("vars", {}).get("customer_backup_keep", 7))
                
                # لیست پوشه‌های بک‌اپ
                backup_dirs = []
                for item in os.listdir(customer_dir):
                    item_path = os.path.join(customer_dir, item)
                    if os.path.isdir(item_path) and item.startswith("202"):
                        backup_dirs.append({
                            "path": item_path,
                            "name": item,
                            "mtime": os.path.getmtime(item_path)
                        })
                
                # مرتب کردن بر اساس تاریخ (جدیدترین اول)
                backup_dirs.sort(key=lambda x: x["mtime"], reverse=True)
                
                # حذف بک‌اپ‌های قدیمی
                for backup in backup_dirs[keep:]:
                    shutil.rmtree(backup["path"])
                    deleted_count += 1
        
        return jsonify({
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"{deleted_count} بک‌اپ قدیمی حذف شد"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
    # ============================================================================
# Routes for Log Management
# ============================================================================

@ansible_bp.route("/logs/list", methods=["GET"])
def api_logs_list():
    """دریافت لیست لاگ‌های موجود"""
    try:
        inventory = load_inventory()
        project_path = inventory.get("all", {}).get("vars", {}).get("project_path", "/home/calibri")
        log_path = os.path.join(project_path, "log")
        
        if not os.path.exists(log_path):
            return jsonify({
                "status": "success",
                "message": "پوشه لاگ یافت نشد",
                "log_path": log_path,
                "logs": {}
            })
        
        log_data = {
            "cron": {},
            "backup": {},
            "customers": {}
        }
        
        # لاگ cron (مشترک)
        cron_log_path = os.path.join(log_path, "cron.log")
        if os.path.exists(cron_log_path):
            cron_stats = get_file_stats(cron_log_path)
            log_data["cron"] = {
                "name": "cron.log",
                "path": cron_log_path,
                "size": cron_stats["size"],
                "size_formatted": cron_stats["size_formatted"],
                "modified": cron_stats["modified"],
                "line_count": cron_stats["line_count"]
            }
        
        # پوشه backup logs
        backup_log_path = os.path.join(log_path, "backup")
        if os.path.exists(backup_log_path) and os.path.isdir(backup_log_path):
            backup_logs = {}
            
            for log_file in os.listdir(backup_log_path):
                if log_file.endswith('.log'):
                    log_file_path = os.path.join(backup_log_path, log_file)
                    stats = get_file_stats(log_file_path)
                    
                    backup_logs[log_file] = {
                        "name": log_file,
                        "path": log_file_path,
                        "size": stats["size"],
                        "size_formatted": stats["size_formatted"],
                        "modified": stats["modified"],
                        "line_count": stats["line_count"]
                    }
            
            log_data["backup"] = backup_logs
        
        # لاگ‌های مشتریان
        customers = inventory.get("all", {}).get("hosts", {}).keys()
        
        for customer in customers:
            customer_logs = []
            
            # جستجوی لاگ‌های مربوط به این مشتری در پوشه backup
            for log_name, log_info in log_data["backup"].items():
                if customer in log_name:
                    # تشخیص نوع لاگ
                    log_type = "databases" if "databases" in log_name else "volumes" if "volumes" in log_name else "unknown"
                    
                    # تحلیل محتوای لاگ
                    analysis = analyze_log_file(log_info["path"])
                    
                    customer_logs.append({
                        "name": log_name,
                        "type": log_type,
                        "path": log_info["path"],
                        "size": log_info["size"],
                        "size_formatted": log_info["size_formatted"],
                        "modified": log_info["modified"],
                        "line_count": log_info["line_count"],
                        "analysis": analysis
                    })
            
            if customer_logs:
                log_data["customers"][customer] = {
                    "name": inventory["all"]["hosts"][customer].get("vars", {}).get("customer_name", customer),
                    "logs": customer_logs,
                    "total_logs": len(customer_logs)
                }
        
        return jsonify({
            "status": "success",
            "log_path": log_path,
            "backup_log_path": backup_log_path,
            "logs": log_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/logs/view", methods=["GET"])
def api_logs_view():
    """مشاهده محتوای یک لاگ"""
    try:
        log_path = request.args.get("path")
        lines = int(request.args.get("lines", 100))  # تعداد خطوط پیش‌فرض
        tail = request.args.get("tail", "false").lower() == "true"  # آیا tail بخوانیم؟
        
        if not log_path:
            return jsonify({
                "status": "error",
                "message": "مسیر لاگ الزامی است"
            }), 400
        
        if not os.path.exists(log_path):
            return jsonify({
                "status": "error",
                "message": "فایل لاگ یافت نشد"
            }), 404
        
        # خواندن لاگ
        content = read_log_file(log_path, lines, tail)
        
        # تحلیل خطوط
        lines_analysis = analyze_log_lines(content.split('\n'))
        
        return jsonify({
            "status": "success",
            "path": log_path,
            "filename": os.path.basename(log_path),
            "total_lines": len(content.split('\n')),
            "content": content,
            "analysis": lines_analysis
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/logs/download", methods=["GET"])
def api_logs_download():
    """دانلود فایل لاگ"""
    try:
        log_path = request.args.get("path")
        
        if not log_path:
            return jsonify({
                "status": "error",
                "message": "مسیر لاگ الزامی است"
            }), 400
        
        if not os.path.exists(log_path):
            return jsonify({
                "status": "error",
                "message": "فایل لاگ یافت نشد"
            }), 404
        
        return send_file(log_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@ansible_bp.route("/logs/clear", methods=["POST"])
def api_logs_clear():
    """پاک کردن فایل لاگ"""
    try:
        data = request.json
        log_path = data.get("path")
        
        if not log_path:
            return jsonify({
                "status": "error",
                "message": "مسیر لاگ الزامی است"
            }), 400
        
        if not os.path.exists(log_path):
            return jsonify({
                "status": "error",
                "message": "فایل لاگ یافت نشد"
            }), 404
        
        # پاک کردن محتوای فایل (نه حذف فایل)
        with open(log_path, 'w') as f:
            f.write(f"# Log cleared at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        return jsonify({
            "status": "success",
            "message": "فایل لاگ پاک شد"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================================================
# Helper Functions for Logs
# ============================================================================

def get_file_stats(file_path):
    """دریافت آمار فایل"""
    stats = os.stat(file_path)
    
    size = stats.st_size
    if size < 1024:
        size_formatted = f"{size} B"
    elif size < 1024 * 1024:
        size_formatted = f"{size / 1024:.2f} KB"
    else:
        size_formatted = f"{size / (1024 * 1024):.2f} MB"
    
    modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    
    # شمارش خطوط
    line_count = 0
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            line_count = sum(1 for _ in f)
    except:
        line_count = 0
    
    return {
        "size": size,
        "size_formatted": size_formatted,
        "modified": modified,
        "line_count": line_count
    }

def read_log_file(file_path, lines=100, tail=False):
    """خواندن فایل لاگ"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            if tail:
                # خواندن خطوط آخر
                all_lines = f.readlines()
                start = max(0, len(all_lines) - lines)
                content = ''.join(all_lines[start:])
            else:
                # خواندن خطوط اول
                content_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    content_lines.append(line)
                content = ''.join(content_lines)
        
        return content
    except Exception as e:
        return f"Error reading log file: {str(e)}"

def analyze_log_file(log_path):
    """تحلیل فایل لاگ"""
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        analysis = {
            "total_lines": len(lines),
            "error_count": 0,
            "success_count": 0,
            "warning_count": 0,
            "start_count": 0,
            "finish_count": 0,
            "last_entry": None,
            "first_entry": None
        }
        
        if lines:
            analysis["first_entry"] = lines[0].strip()
            analysis["last_entry"] = lines[-1].strip()
        
        for line in lines:
            line_lower = line.lower()
            if "error" in line_lower:
                analysis["error_count"] += 1
            elif "success" in line_lower:
                analysis["success_count"] += 1
            elif "warning" in line_lower:
                analysis["warning_count"] += 1
            
            if "start" in line_lower:
                analysis["start_count"] += 1
            elif "finish" in line_lower:
                analysis["finish_count"] += 1
        
        return analysis
    except:
        return {}

def analyze_log_lines(lines):
    """تحلیل خطوط لاگ"""
    analysis = {
        "errors": [],
        "warnings": [],
        "successes": [],
        "starts": [],
        "finishes": []
    }
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        if "error" in line_lower:
            analysis["errors"].append({
                "line_number": i + 1,
                "content": line.strip()
            })
        elif "warning" in line_lower:
            analysis["warnings"].append({
                "line_number": i + 1,
                "content": line.strip()
            })
        elif "success" in line_lower:
            analysis["successes"].append({
                "line_number": i + 1,
                "content": line.strip()
            })
        
        if "start" in line_lower and ("backup" in line_lower or "database" in line_lower or "volume" in line_lower):
            analysis["starts"].append({
                "line_number": i + 1,
                "content": line.strip()
            })
        elif "finish" in line_lower:
            analysis["finishes"].append({
                "line_number": i + 1,
                "content": line.strip()
            })
    
    return analysis