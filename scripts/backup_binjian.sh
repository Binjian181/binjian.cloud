#!/bin/bash
# Auto backup binjian.cloud (website + database) to GitHub
cd /var/www/binjian.cloud/

# --- Database backup ---
DB_NAME="articles"
DB_USER="root"
DB_PASSWORD="19930107ZBj"
DB_DIR="db"
DATE=$(date +%Y%m%d)

mkdir -p ${DB_DIR}

# Dump database (only keep the latest dump in git)
mysqldump -u${DB_USER} -p${DB_PASSWORD} --single-transaction --quick \
    --lock-tables=false ${DB_NAME} | gzip > ${DB_DIR}/${DB_NAME}_${DATE}.sql.gz

# Remove old dumps in db/ (keep only today's)
find ${DB_DIR} -name "${DB_NAME}_*.sql.gz" -type f ! -name "${DB_NAME}_${DATE}.sql.gz" -delete

# Also keep local backup with 7-day retention
LOCAL_BACKUP_DIR="/home/ubuntu/database_backups"
mkdir -p ${LOCAL_BACKUP_DIR}
cp ${DB_DIR}/${DB_NAME}_${DATE}.sql.gz ${LOCAL_BACKUP_DIR}/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql.gz
find ${LOCAL_BACKUP_DIR} -name "${DB_NAME}_*.sql.gz" -type f -mtime +7 -delete

# --- Git backup ---
# Add all changes (website files + database dump)
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "[$(date)] No changes to backup"
    exit 0
fi

# Commit and push
git commit -m "auto backup: $(date '+%Y-%m-%d %H:%M')"
git push origin main

echo "[$(date)] Backup completed (website + database)"
