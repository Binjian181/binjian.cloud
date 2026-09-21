#!/bin/bash
set -eo pipefail
#
# 数据库备份脚本
# 功能：备份 MySQL 数据库到本地，保留最近 7 天的备份
# 定时任务：每天凌晨 3 点执行
#

# 配置
DB_NAME="articles"
DB_USER="root"
DB_PASSWORD="19930107ZBj"
BACKUP_DIR="/home/ubuntu/database_backups"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

echo "=========================================="
echo "🕒 开始时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo "💾 正在备份数据库：${DB_NAME}"

# 执行备份
# 密码通过 MYSQL_PWD 环境变量传入，避免出现在进程列表 (ps) 中
if MYSQL_PWD="${DB_PASSWORD}" mysqldump -u${DB_USER} --single-transaction \
    --quick --lock-tables=false ${DB_NAME} | gzip > ${BACKUP_FILE}; then
    
    BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
    echo "✅ 备份成功：${BACKUP_FILE}"
    echo "📦 备份大小：${BACKUP_SIZE}"
    
    # 删除旧备份
    echo ""
    echo "🧹 清理 ${RETENTION_DAYS} 天前的备份..."
    find ${BACKUP_DIR} -name "${DB_NAME}_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    REMAINING=$(ls -1 ${BACKUP_DIR}/${DB_NAME}_*.sql.gz 2>/dev/null | wc -l)
    echo "📁 剩余备份数量：${REMAINING}"
    
else
    echo "❌ 备份失败！"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 完成时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
