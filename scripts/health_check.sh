#!/bin/bash
# 健康检查脚本

API_URL="${API_URL:-http://localhost:80/api/v1/health}"
LOG_DIR="/var/log/docdist"
LOG_FILE="$LOG_DIR/health.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR" 2>/dev/null || true

response=$(curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 \
    --max-time 10 \
    "$API_URL")

if [ "$response" -ge 200 ] 2>/dev/null && [ "$response" -lt 300 ] 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Health check PASSED (HTTP $response)"
    exit 0
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Health check FAILED (HTTP $response)" >> "$LOG_FILE"
    exit 1
fi
