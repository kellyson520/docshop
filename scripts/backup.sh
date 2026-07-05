#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backup/docshop}"
DATA_DIR="${DATA_DIR:-/app/data}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE="$(date +%Y%m%d_%H%M%S)"
DB_PATH="${DB_PATH:-$DATA_DIR/docshop.db}"
LEGACY_DB_NAME="${LEGACY_DB_NAME:-doc""dist.db}"

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_PATH" && -f "$DATA_DIR/$LEGACY_DB_NAME" ]]; then
  echo "[backup] 未找到 docshop.db，使用兼容旧库"
  DB_PATH="$DATA_DIR/$LEGACY_DB_NAME"
fi

if [[ ! -f "$DB_PATH" ]]; then
  echo "[backup] 数据库不存在：$DB_PATH" >&2
  exit 1
fi

BACKUP_DB="$BACKUP_DIR/docshop_${DATE}.db"
echo "[backup] 备份数据库：$DB_PATH -> $BACKUP_DB"
sqlite3 "$DB_PATH" ".backup '$BACKUP_DB'"

INTEGRITY="$(sqlite3 "$BACKUP_DB" 'PRAGMA integrity_check;' 2>&1)"
if [[ "$INTEGRITY" != "ok" ]]; then
  echo "[backup] 数据库备份完整性检查失败：$INTEGRITY" >&2
  rm -f "$BACKUP_DB"
  exit 1
fi

echo "[backup] 数据库完整性检查通过"

if [[ -d "$DATA_DIR/uploads" ]]; then
  UPLOADS_ARCHIVE="$BACKUP_DIR/uploads_${DATE}.tar.gz"
  echo "[backup] 备份上传文件：$UPLOADS_ARCHIVE"
  tar -czf "$UPLOADS_ARCHIVE" -C "$DATA_DIR" uploads
else
  echo "[backup] 上传目录不存在，跳过 uploads"
fi

if [[ -d "$DATA_DIR/covers" ]]; then
  COVERS_ARCHIVE="$BACKUP_DIR/covers_${DATE}.tar.gz"
  echo "[backup] 备份封面/预览文件：$COVERS_ARCHIVE"
  tar -czf "$COVERS_ARCHIVE" -C "$DATA_DIR" covers
fi

if [[ "$RETENTION_DAYS" =~ ^[0-9]+$ && "$RETENTION_DAYS" -gt 0 ]]; then
  find "$BACKUP_DIR" -name '*.db' -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true
  find "$BACKUP_DIR" -name '*.tar.gz' -mtime +"$RETENTION_DAYS" -delete 2>/dev/null || true
fi

echo "[backup] 完成：$DATE"
