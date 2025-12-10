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

<!-- ردیف اول: زیرساخت -->
![Ansible](https://img.shields.io/badge/Ansible-2.16+-ee0000?logo=ansible&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-27.3+-2496ED?logo=docker&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04_LTS-E95420?logo=ubuntu&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white)
<br>
<!-- ردیف دوم: بک‌اند -->
![PHP](https://img.shields.io/badge/PHP-8.3-777BB4?logo=php&logoColor=white)
![Laravel](https://img.shields.io/badge/Laravel-11-ff2d20?logo=laravel&logoColor=white)
![Symfony](https://img.shields.io/badge/Symfony-7-000000?logo=symfony&logoColor=white)
![CodeIgniter](https://img.shields.io/badge/CodeIgniter-4-DD4814?logo=codeigniter&logoColor=white)
<br>
<!-- ردیف سوم: فرانت‌اند و ابزارها -->
![Vue.js](https://img.shields.io/badge/Vue.js-3-4fc08d?logo=vuedotjs&logoColor=white)
![Pinia](https://img.shields.io/badge/Pinia-2-fbbf24?logo=pinia&logoColor=black)
![Axios](https://img.shields.io/badge/Axios-0.28-5a29e4?logo=axios&logoColor=white)
![Socket.io](https://img.shields.io/badge/Socket.io-4-010101?logo=socket.io&logoColor=white)
<br>
<!-- ردیف چهارم: ابزارها و دیتابیس -->
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-563d7c?logo=bootstrap&logoColor=white)
![Composer](https://img.shields.io/badge/Composer-2.7-885630?logo=composer&logoColor=white)
![NPM](https://img.shields.io/badge/NPM-10-CB3837?logo=npm&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.56-45ba4b?logo=playwright&logoColor=white)

---

### دانلود پروژه

```bash
git clone https://github.com/samadelmakchi/leo.git
cd leo
```

---

### ساخت کلید SSH (id_rsa)

```bash
ssh-keygen -t ed25519 -C "leo@deploy" -f id_rsa -N ""
```

---

### افزودن کلید به GitHub
```bash
cat id_rsa.pub
```
محتوای بالا رو کپی کن → به GitHub → Settings → SSH and GPG keys → New SSH key اضافه کن

---

### ساختار پروژه

```text
leo/
├── playbook.yml
├── inventory.yml
├── id_rsa + id_rsa.pub
├── sql/
│   ├── simnad_lms.sql
│   ├── simnad_file.env
│   └── ...
├── tasks/
│   ├── 09-deploy-containers.yml
│   ├── 10-run-migrations.yml
│   └── 99-run-tests.yml
├── tests/
└── templates/
```
---

### اجرای پروژه

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

# فقط میگریشن lms و file
ansible-playbook -i inventory.yml playbook.yml --limit simnad -e "customer_lms_update=true customer_file_update=true"

# فقط تست
ansible-playbook -i inventory.yml playbook.yml --limit simnad --tags test

# فقط بکاپ بگیر (بدون تست)
ansible-playbook -i inventory.yml playbook.yml --limit simnad --tags backup
```

### آپدیت فقط یک سرویس خاص

در `inventory.yml` برای مشتری موردنظر:
```bash
customer_gateway_update: true
customer_portal_update: false
customer_portal_frontend_update: true
```

---

### تنظیمات مهم در inventory.yml

```bash
customer_state: "up"               # یا "down"

# کنترل آپدیت سرویس‌ها
customer_gateway_update: true
customer_portal_update: true
customer_portal_frontend_update: true

# کنترل بکاپ
customer_backup_enabled: true                     # فعال/غیرفعال کردن بکاپ
customer_backup_keep: 7                           # چند تا بکاپ آخر نگه داشته شود
customer_backup_cron_volumes: "0 3 * * 0"         # یکشنبه‌ها ساعت 03:00
customer_backup_cron_databases: "30 1,9,17 * * *" # هر روز 01:30، 09:30، 17:30
```

---

### ساختار ریستور خودکار (پوشه sql/)

```bash
sql/
├── simnad_gateway.sql
├── simnad_portal.sql
├── simnad_lms.sql
├── simnad_file.sql
├── simnad_gateway_uploads.zip
├── simnad_portal_uploads.zip
├── simnad_lms_uploads.zip
├── simnad_file_uploads.zip
├── simnad_lms.env
├── simnad_file.env
└── default_gateway.sql   # فقط برای gateway
```
اگر فایل مشتری وجود داشته باشد → ریستور می‌شود

اگر نبود → میگریشن خودش دیتابیس را می‌سازد

---

### اجرای تست فقط برای یک مشتری خاص

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

## گزارش‌ها

| نوع گزارش            | مسیر                                                 |
| -------------------- | ---------------------------------------------------- |
| گزارش تست HTML       | `/home/calibri/log/test-reports/[مشتری]/report.html` |
| گزارش تست JUnit (CI) | `/home/calibri/log/test-reports/[مشتری]/junit.xml`   |
| لاگ بکاپ دیتابیس     | `/home/calibri/log/backup/[مشتری]_databases.log`     |
| لاگ بکاپ فایل‌ها      | `/home/calibri/log/backup/[مشتری]_volumes.log`       |
| لاگ نصب Playwright   | `/var/log/playwright-install.log`                    |

> مثال برای مشتری `simnad`:
> - گزارش تست: `/home/calibri/log/test-reports/simnad/report.html`
> - لاگ بکاپ: `/home/calibri/log/backup/simnad_databases.log`

---

## تنظیم ساب‌دامین در DirectAdmin

| سرویس           | پورت پیش‌فرض | مثال ساب‌دامین              | توضیحات               |
| --------------- | ----------- | -------------------------- | --------------------- |
| Gateway         | 8061+       | `calibri.simnad.com`       | پنل مدیریت اصلی       |
| Portal Backend  | 7061+       | `backendportal.simnad.com` | بک‌اند Symfony         |
| Portal Frontend | 6061+       | `portal.simnad.com`        | فرانت‌اند React/Vue    |
| LMS             | 9061+       | `lms.simnad.com`           | سیستم مدیریت یادگیری  |
| File Storage    | 10061+      | `files.simnad.com`         | فایل‌منیجر و ذخیره‌سازی |

### نحوه اضافه کردن در DirectAdmin:
1. وارد پنل DirectAdmin شوید → **DNS Management**  
2. روی **Add Record** کلیک کنید  
3. نوع: `A` → Name: `calibri` → Value: `185.255.89.160` → ذخیره  
4. همین کار رو برای بقیه ساب‌دامین‌ها تکرار کنید

DNS معمولاً بین ۱ تا ۱۰ دقیقه پروپاگیت می‌شود.

---

### مسیر ذخیره بکاپ‌ها

```
/home/calibri/backup/[customer_name]/2025-12-02-10-30-00/
```

---

**ساخته شده با عشق توسط صمد المکچی**  
