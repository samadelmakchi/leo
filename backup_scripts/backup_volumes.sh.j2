#!/bin/bash
# بکاپ از فولدرهای مهم پروژه

BACKUP_DIR="{{ backup_path }}/{{ inventory_hostname }}/$(date +'%Y-%m-%d-%H-%M-%S')"
mkdir -p "$BACKUP_DIR"
chmod 777 "$BACKUP_DIR"

LOG="{{ log_path }}/backup/{{ inventory_hostname }}_volumes.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') | START volume backup" >> "$LOG"

# لیست فولدرها
VOLUMES="gateway/admin/uploads
          gateway/admin/captcha_images
          gateway/admin
          portal
          portal-frontend"

BASE="{{ project_path }}/{{ inventory_hostname }}"

for dir in $VOLUMES; do
  full_path="$BASE/$dir"
  [[ ! -d "$full_path" ]] && continue

  archive_name=$(echo "$dir" | tr '/' '_').tar.gz
  tar -czf "$BACKUP_DIR/$archive_name" -C "$(dirname "$full_path")" "$(basename "$full_path")" >> "$LOG" 2>&1
  echo "$(date '+%Y-%m-%d %H:%M:%S') | SUCCESS $dir → $archive_name" >> "$LOG"
done

# پاک کردن بکاپ‌های قدیمی (نگه داشتن فقط N تا آخر)
KEEP={{ customer_backup_keep | default(7) }}
find "{{ backup_path }}/{{ inventory_hostname }}" -maxdepth 1 -type d -name "202*" | sort -r | tail -n +$((KEEP+1)) | xargs rm -rf

echo "$(date '+%Y-%m-%d %H:%M:%S') | FINISH volume backup" >> "$LOG"