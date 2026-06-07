#!/bin/bash
# ============================================================
# 数据库和文件恢复脚本
# 用法: ./restore.sh [备份文件路径]
#   - 不指定参数时，自动选择最新的备份
#   - 指定 .db 文件时，仅恢复数据库
#   - 指定 .tar.gz 文件时，仅恢复上传文件
#   - 指定目录时，从该目录恢复数据库和文件
# ============================================================

set -e

BACKUP_DIR="/backup/docdist"
DATA_DIR="/app/data"
RESTORE_DB=""
RESTORE_UPLOADS=""

# 颜色输出（仅在终端中启用，CI/CD 环境自动禁用）
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' NC=''
fi

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --------------------------------------------------
# 参数解析
# --------------------------------------------------
if [ -n "$1" ]; then
    TARGET="$1"

    if [ -f "$TARGET" ]; then
        # 根据文件扩展名判断恢复类型
        case "$TARGET" in
            *.db)
                RESTORE_DB="$TARGET"
                ;;
            *.tar.gz)
                RESTORE_UPLOADS="$TARGET"
                ;;
            *)
                log_error "不支持的文件格式: $TARGET（仅支持 .db 和 .tar.gz）"
                exit 1
                ;;
        esac
    elif [ -d "$TARGET" ]; then
        # 从指定目录中查找最新的数据库和文件备份
        RESTORE_DB=$(ls -t "$TARGET"/docdist_*.db 2>/dev/null | head -1)
        RESTORE_UPLOADS=$(ls -t "$TARGET"/uploads_*.tar.gz 2>/dev/null | head -1)
        if [ -z "$RESTORE_DB" ] && [ -z "$RESTORE_UPLOADS" ]; then
            log_error "目录 $TARGET 中未找到备份文件"
            exit 1
        fi
    else
        log_error "文件或目录不存在: $TARGET"
        exit 1
    fi
else
    # 未指定参数，从默认备份目录选取最新备份
    RESTORE_DB=$(ls -t "$BACKUP_DIR"/docdist_*.db 2>/dev/null | head -1)
    RESTORE_UPLOADS=$(ls -t "$BACKUP_DIR"/uploads_*.tar.gz 2>/dev/null | head -1)
    if [ -z "$RESTORE_DB" ] && [ -z "$RESTORE_UPLOADS" ]; then
        log_error "默认备份目录 $BACKUP_DIR 中未找到备份文件"
        exit 1
    fi
fi

# --------------------------------------------------
# 确认恢复操作
# --------------------------------------------------
echo ""
echo "=========================================="
echo "  DocDist 数据恢复"
echo "=========================================="
[ -n "$RESTORE_DB" ]      && echo "  数据库备份: $RESTORE_DB"
[ -n "$RESTORE_UPLOADS" ] && echo "  文件备份:   $RESTORE_UPLOADS"
echo "  目标目录:   $DATA_DIR"
echo "=========================================="
echo ""
read -rp "确认恢复？此操作将覆盖当前数据 (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    log_warn "用户取消恢复操作"
    exit 0
fi

# --------------------------------------------------
# 恢复前：自动备份当前状态
# --------------------------------------------------
PRE_BACKUP_DIR="$BACKUP_DIR/pre_restore"
PRE_DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$PRE_BACKUP_DIR"

log_info "恢复前备份当前数据..."

if [ -f "$DATA_DIR/docdist.db" ]; then
    sqlite3 "$DATA_DIR/docdist.db" ".backup '$PRE_BACKUP_DIR/docdist_pre_${PRE_DATE}.db'"
    log_info "数据库已备份至: $PRE_BACKUP_DIR/docdist_pre_${PRE_DATE}.db"
fi

if [ -d "$DATA_DIR/uploads" ]; then
    tar -czf "$PRE_BACKUP_DIR/uploads_pre_${PRE_DATE}.tar.gz" -C "$DATA_DIR" uploads
    log_info "上传文件已备份至: $PRE_BACKUP_DIR/uploads_pre_${PRE_DATE}.tar.gz"
fi

# --------------------------------------------------
# 执行恢复
# --------------------------------------------------
RESTORE_OK=true

# 恢复数据库（使用 sqlite3 .restore 替代 cp，支持 WAL 模式安全恢复）
if [ -n "$RESTORE_DB" ]; then
    log_info "正在恢复数据库..."
    mkdir -p "$DATA_DIR"
    # 先验证备份文件完整性
    BACKUP_INTEGRITY=$(sqlite3 "$RESTORE_DB" "PRAGMA integrity_check;" 2>&1)
    if [ "$BACKUP_INTEGRITY" != "ok" ]; then
        log_error "备份数据库损坏: $BACKUP_INTEGRITY"
        RESTORE_OK=false
    else
        # 如果目标已有数据库，先关闭 WAL 再覆盖
        if [ -f "$DATA_DIR/docdist.db" ]; then
            sqlite3 "$DATA_DIR/docdist.db" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
            rm -f "$DATA_DIR/docdist.db" "$DATA_DIR/docdist.db-wal" "$DATA_DIR/docdist.db-shm"
        fi
        sqlite3 "$RESTORE_DB" ".restore '$DATA_DIR/docdist.db'"
        log_info "数据库恢复完成"
    fi
fi

# 恢复上传文件
if [ -n "$RESTORE_UPLOADS" ]; then
    log_info "正在恢复上传文件..."
    mkdir -p "$DATA_DIR/uploads"
    tar -xzf "$RESTORE_UPLOADS" -C "$DATA_DIR"
    log_info "上传文件恢复完成"
fi

# --------------------------------------------------
# 恢复后：验证数据完整性
# --------------------------------------------------
log_info "正在验证数据完整性..."

ERRORS=0

# 验证数据库
if [ -f "$DATA_DIR/docdist.db" ]; then
    # 检查数据库是否可读且未损坏
    INTEGRITY=$(sqlite3 "$DATA_DIR/docdist.db" "PRAGMA integrity_check;" 2>&1)
    if [ "$INTEGRITY" = "ok" ]; then
        TABLE_COUNT=$(sqlite3 "$DATA_DIR/docdist.db" "SELECT count(*) FROM sqlite_master WHERE type='table';")
        log_info "数据库完整性检查通过（共 $TABLE_COUNT 张表）"
    else
        log_error "数据库完整性检查失败: $INTEGRITY"
        ERRORS=$((ERRORS + 1))
    fi
else
    log_warn "数据库文件不存在，跳过验证"
fi

# 验证上传文件目录
if [ -d "$DATA_DIR/uploads" ]; then
    FILE_COUNT=$(find "$DATA_DIR/uploads" -type f | wc -l)
    log_info "上传文件目录验证通过（共 $FILE_COUNT 个文件）"
else
    log_warn "上传文件目录不存在"
fi

# --------------------------------------------------
# 输出结果
# --------------------------------------------------
echo ""
if [ $ERRORS -eq 0 ]; then
    log_info "数据恢复完成，所有验证通过"
    echo ""
    log_info "如需回滚，可使用恢复前备份:"
    echo "  数据库: $PRE_BACKUP_DIR/docdist_pre_${PRE_DATE}.db"
    echo "  文件:   $PRE_BACKUP_DIR/uploads_pre_${PRE_DATE}.tar.gz"
    exit 0
else
    log_error "数据恢复完成，但存在 $ERRORS 个验证错误，请检查日志"
    exit 1
fi
