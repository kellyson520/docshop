#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backup/docshop}"
DATA_DIR="${DATA_DIR:-/app/data}"
TARGET="${1:-}"
RESTORE_DB=""
RESTORE_UPLOADS=""
RESTORE_COVERS=""

log() { echo "[restore] $*"; }
fail() { echo "[restore] $*" >&2; exit 1; }

latest_file() {
  local pattern="$1"
  ls -t $pattern 2>/dev/null | head -1 || true
}

if [[ -n "$TARGET" ]]; then
  if [[ -f "$TARGET" ]]; then
    case "$TARGET" in
      *.db) RESTORE_DB="$TARGET" ;;
      uploads_*.tar.gz) RESTORE_UPLOADS="$TARGET" ;;
      covers_*.tar.gz) RESTORE_COVERS="$TARGET" ;;
      *.tar.gz) RESTORE_UPLOADS="$TARGET" ;;
      *) fail "不支持的备份文件：$TARGET，只支持 .db 或 .tar.gz" ;;
    esac
  elif [[ -d "$TARGET" ]]; then
    BACKUP_DIR="$TARGET"
  else
    fail "目标不存在：$TARGET"
  fi
fi

if [[ -z "$RESTORE_DB" ]]; then
  RESTORE_DB="$(latest_file "${BACKUP_DIR}/docshop_*.db")"
fi
if [[ -z "$RESTORE_UPLOADS" ]]; then
  RESTORE_UPLOADS="$(latest_file "${BACKUP_DIR}/uploads_*.tar.gz")"
fi
if [[ -z "$RESTORE_COVERS" ]]; then
  RESTORE_COVERS="$(latest_file "${BACKUP_DIR}/covers_*.tar.gz")"
fi

if [[ -z "$RESTORE_DB" && -z "$RESTORE_UPLOADS" && -z "$RESTORE_COVERS" ]]; then
  fail "未找到可恢复的备份：$BACKUP_DIR"
fi

cat <<EOF
==========================================
DocShop 恢复确认
数据库备份: ${RESTORE_DB:-跳过}
上传文件:   ${RESTORE_UPLOADS:-跳过}
封面文件:   ${RESTORE_COVERS:-跳过}
目标目录:   ${DATA_DIR}
==========================================
EOF

if [[ "${RESTORE_ASSUME_YES:-false}" != "true" ]]; then
  read -rp "继续恢复会覆盖当前数据，是否继续？(y/N): " CONFIRM
  [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]] || { log "已取消"; exit 0; }
fi

mkdir -p "$DATA_DIR" "$BACKUP_DIR/pre_restore"
PRE_DATE="$(date +%Y%m%d_%H%M%S)"

if [[ -f "$DATA_DIR/docshop.db" ]]; then
  PRE_DB="$BACKUP_DIR/pre_restore/docshop_pre_${PRE_DATE}.db"
  log "恢复前备份当前数据库：$PRE_DB"
  sqlite3 "$DATA_DIR/docshop.db" ".backup '$PRE_DB'"
fi

if [[ -d "$DATA_DIR/uploads" ]]; then
  PRE_UPLOADS="$BACKUP_DIR/pre_restore/uploads_pre_${PRE_DATE}.tar.gz"
  log "恢复前备份当前上传文件：$PRE_UPLOADS"
  tar -czf "$PRE_UPLOADS" -C "$DATA_DIR" uploads
fi

if [[ -n "$RESTORE_DB" ]]; then
  INTEGRITY="$(sqlite3 "$RESTORE_DB" 'PRAGMA integrity_check;' 2>&1)"
  [[ "$INTEGRITY" == "ok" ]] || fail "备份数据库完整性检查失败：$INTEGRITY"

  log "恢复数据库：$RESTORE_DB -> $DATA_DIR/docshop.db"
  sqlite3 "$DATA_DIR/docshop.db" 'PRAGMA wal_checkpoint(TRUNCATE);' 2>/dev/null || true
  rm -f "$DATA_DIR/docshop.db" "$DATA_DIR/docshop.db-wal" "$DATA_DIR/docshop.db-shm"
  sqlite3 "$RESTORE_DB" ".restore '$DATA_DIR/docshop.db'"
fi

if [[ -n "$RESTORE_UPLOADS" ]]; then
  log "恢复上传文件：$RESTORE_UPLOADS"
  mkdir -p "$DATA_DIR/uploads"
  tar -xzf "$RESTORE_UPLOADS" -C "$DATA_DIR"
fi

if [[ -n "$RESTORE_COVERS" ]]; then
  log "恢复封面/预览文件：$RESTORE_COVERS"
  mkdir -p "$DATA_DIR/covers"
  tar -xzf "$RESTORE_COVERS" -C "$DATA_DIR"
fi

if [[ -f "$DATA_DIR/docshop.db" ]]; then
  FINAL_INTEGRITY="$(sqlite3 "$DATA_DIR/docshop.db" 'PRAGMA integrity_check;' 2>&1)"
  [[ "$FINAL_INTEGRITY" == "ok" ]] || fail "恢复后数据库完整性检查失败：$FINAL_INTEGRITY"
fi

log "恢复完成。建议重启服务：docker compose restart docshop"
