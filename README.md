# LEO - سیستم استقرار خودکار پروژه‌های کالیبری

یک سیستم CI/CD کاملاً هوشمند و انعطاف‌پذیر برای استقرار، مدیریت و بکاپ‌گیری خودکار از پروژه‌های **Gateway + Portal + Portal-Frontend** با Docker Compose و Ansible.

### ویژگی‌های کلیدی
- استقرار انتخابی سرویس‌ها (فقط gateway، فقط frontend و ...)
- حالت کامل `up` / `down` برای هر مشتری (حذف کامل کانتینرها + کرون جاب‌ها)
- بکاپ‌گیری هوشمند از فایل‌ها و دیتابیس‌ها با قابلیت فعال/غیرفعال کردن
- مدیریت خودکار کرون جاب‌های بکاپ بر اساس تنظیمات inventory
- پشتیبانی کامل از Git Branch و Tag
- تست کامل خودکار (Smoke, API, UI, Security, Performance, Load, Stress, Regression)
- گزارش HTML زیبا بعد از هر تست
- اگر تست fail شد → دپلوی متوقف میشه (fail-fast)

---

## دانلود پروژه

```bash
git clone https://github.com/samadelmakchi/leo.git
cd leo
```

## ساخت کلید SSH (id_rsa)

```bash
ssh-keygen -t ed25519 -C "leo@deploy" -f id_rsa -N ""
```

---

## افزودن کلید به GitHub
```bash
cat id_rsa.pub
```
محتوای بالا رو کپی کن → به GitHub → Settings → SSH and GPG keys → New SSH key اضافه کن


---

## اجرای پروژه

```bash
# آپدیت همه مشتریان
ansible-playbook -i inventory.yml playbook.yml

# آپدیت فقط یک مشتری
ansible-playbook -i inventory.yml playbook.yml --limit simnad

# خاموش کردن کامل یک مشتری (حذف کانتینرها + کرون جاب‌ها)
ansible-playbook -i inventory.yml playbook.yml --limit test --extra-vars "customer_state=down"

# دپلوی + تست کامل برای یک مشتری
ansible-playbook -i inventory.yml playbook.yml --limit simnad --extra-vars "customer_test_enabled=true"

# فقط تست اجرا کن (بدون دپلوی مجدد)
ansible-playbook -i inventory.yml playbook.yml --limit simnad --tags test --extra-vars "customer_test_enabled=true"

# همه تست‌ها با گزارش HTML
ansible-playbook -i inventory.yml playbook.yml --limit simnad --extra-vars "customer_test_enabled=true"

# فقط تست‌های خاص
pytest -m "smoke or regression" tests/

```

# آپدیت فقط یک سرویس خاص
در `inventory.yml` برای مشتری موردنظر:
```bash
customer_gateway_update: true
customer_portal_update: false
customer_portal_frontend_update: true
```

---

## تنظیمات مهم در inventory.yml

```bash
customer_state: "up"               # یا "down"

# کنترل آپدیت سرویس‌ها
customer_gateway_update: true
customer_portal_update: true
customer_portal_frontend_update: true

# کنترل بکاپ
customer_backup_enabled: true      # فعال/غیرفعال کردن بکاپ
customer_backup_keep: 7            # چند تا بکاپ آخر نگه داشته شود
customer_backup_cron_volumes: "0 3 * * 0"        # یکشنبه‌ها ساعت 03:00
customer_backup_cron_databases: "30 1,9,17 * * *" # هر روز 01:30، 09:30، 17:30
```

---

## اجرای تست فقط برای یک مشتری خاص

```bash
# فقط simnad رو دپلوی کن و تست کامل اجرا کن
ansible-playbook -i inventory.yml playbook.yml \
  --limit simnad \
  --extra-vars "customer_test_enabled=true customer_test_fail_fast=true"

# فقط تست اجرا کن (بدون دپلوی مجدد)
ansible-playbook -i inventory.yml playbook.yml \
  --limit simnad \
  --extra-vars "customer_test_enabled=true" \
  --tags "test"
```

---

### اختصاص ساب‌دامین در DirectAdmin

| سرویس           | پورت پیش‌فرض | مثال ساب‌دامین              |
| --------------- | ----------- | -------------------------- |
| Gateway         | 8061+       | `calibri.simnad.com`       |
| Portal Backend  | 7061+       | `backendportal.simnad.com` |
| Portal Frontend | 6061+       | `portal.simnad.com`        |

#### مراحل اضافه کردن رکورد:
1. وارد DirectAdmin شوید → **DNS Management**  
2. روی **Add Record** کلیک کنید → نوع: **A**  
3. مثال:  
   - **Name:** `calibri`  
   - **Value:** `185.255.89.160`  
4. ذخیره کنید → چند دقیقه صبر کنید تا DNS پروپاگیت شود

---

### سرویس‌های مشتریان (نمونه)

| مشتری  | Gateway                  | Portal Backend                 | Portal Frontend         |
| ------ | ------------------------ | ------------------------------ | ----------------------- |
| سیمناد | `calibri.simnad.com`     | `backendportal.simnad.com`     | `portal.simnad.com`     |
| نیکان  | `calibri.nikan.ir`       | `backendportal.nikan.ir`       | `portal.nikan.ir`       |
| تست    | `testcalibri.test.local` | `testbackendportal.test.local` | `testportal.test.local` |

---

### مسیر ذخیره بکاپ‌ها

```
/home/calibri/backup/[customer_name]/2025-12-02-10-30-00/
```

---

### گزارش تست‌ها

```
/home/calibri/log/test-reports/[customer_name]/report.html
```

---

**ساخته شده با عشق توسط صمد المکچی**  


sudo rm -rf /home/calibri/ 
clear 
ansible-playbook -i inventory.yml playbook.yml --limit simnad