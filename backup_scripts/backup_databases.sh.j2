#!/bin/bash
# بکاپ از دیتابیس‌ها

BACKUP_DIR="{{ backup_path }}/{{ inventory_hostname }}/$(date +'%Y-%m-%d-%H-%M-%S')"
mkdir -p "$BACKUP_DIR"
chmod 777 "$BACKUP_DIR"

LOG="{{ log_path }}/backup/{{ inventory_hostname }}_databases.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') | START database backup" >> "$LOG"

DB_FILE="{{ info_path }}/databases/{{ inventory_hostname }}.txt"

while IFS=',' read -r type name user pass container; do
  [[ -z "$name" || "$name" == "mysql" ]] && continue

  file="${name}_$(date +%Y%m%d_%H%M%S).sql.gz"
  docker exec "$container" mysqldump -u"$user" -p"$pass" --single-transaction --quick "$name" 2>>"$LOG" | gzip > "$BACKUP_DIR/$file"

  if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | SUCCESS $name → $file" >> "$LOG"
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') | FAILED $name" >> "$LOG"
  fi
done < "$DB_FILE"

# پاک کردن بکاپ‌های قدیمی
KEEP={{ customer_backup_keep | default(7) }}
find "{{ backup_path }}/{{ inventory_hostname }}" -maxdepth 1 -type d -name "202*" | sort -r | tail -n +$((KEEP+1)) | xargs rm -rf

echo "$(date '+%Y-%m-%d %H:%M:%S') | FINISH database backup" >> "$LOG"