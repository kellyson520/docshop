#!/bin/bash
# 部署脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== DocDist Deployment ==="

# 检查工作区是否干净
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    echo "警告: 工作区有未提交的修改，正在 stash..."
    git stash push -m "deploy-auto-stash-$(date +%Y%m%d_%H%M%S)"
fi

# 拉取最新代码
if ! git pull origin main; then
    echo "错误: git pull 失败，取消部署"
    exit 1
fi

# 停止现有服务
docker-compose down

# 备份数据
"$SCRIPT_DIR/backup.sh"

# 构建并启动
docker-compose up -d --build

# 轮询健康检查（最多等待 60 秒）
echo "等待服务启动..."
MAX_WAIT=60
START_TIME=$(date +%s)
HEALTHY=false

while [ $(($(date +%s) - START_TIME)) -lt $MAX_WAIT ]; do
    if "$SCRIPT_DIR/health_check.sh"; then
        HEALTHY=true
        break
    fi
    sleep 2
done

if $HEALTHY; then
    echo "部署成功!"
else
    echo "部署失败，正在回滚..."
    docker-compose down
    # 恢复最新备份
    LATEST_BACKUP=$(ls -t /backup/docdist/docdist_backup_*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        echo "正在从 $LATEST_BACKUP 恢复..."
        "$SCRIPT_DIR/restore.sh" --file "$LATEST_BACKUP"
    else
        echo "警告: 未找到备份文件，无法自动恢复"
    fi
    exit 1
fi
