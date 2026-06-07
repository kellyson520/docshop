#!/bin/bash
# 数据库和文件备份脚本

BACKUP_DIR="${BACKUP_DIR:-/backup/docdist}"
DATA_DIR="${DATA_DIR:-/app/data}"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# 备份数据库（先检查源文件是否存在）
DB_PATH="$DATA_DIR/docdist.db"
if [ ! -f "$DB_PATH" ]; then
    echo "错误: 数据库文件不存在: $DB_PATH"
    exit 1
fi

BACKUP_DB="$BACKUP_DIR/docdist_$DATE.db"
sqlite3 "$DB_PATH" ".backup '$BACKUP_DB'"

# 验证备份完整性
INTEGRITY=$(sqlite3 "$BACKUP_DB" "PRAGMA integrity_check;" 2>&1)
if [ "$INTEGRITY" != "ok" ]; then
    echo "错误: 备份完整性检查失败: $INTEGRITY"
    rm -f "$BACKUP_DB"
    exit 1
fi
echo "数据库备份完成: $BACKUP_DB (完整性: $INTEGRITY)"

# 备份上传文件
if [ -d "$DATA_DIR/uploads" ]; then
    tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" -C "$DATA_DIR" uploads
    echo "文件备份完成: $BACKUP_DIR/uploads_$DATE.tar.gz"
else
    echo "警告: 上传目录不存在，跳过文件备份"
fi

# 清理 30 天前的备份
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete 2>/dev/null
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null

echo "备份完成: $DATE"
