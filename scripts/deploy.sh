#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

COMPOSE="${COMPOSE:-docker compose}"
SERVICE="${SERVICE:-docshop}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${DOCSHOP_PORT:-8080}/health}"
MAX_WAIT="${MAX_WAIT:-180}"

if [[ ! -f .env ]]; then
  echo "[deploy] .env 不存在，已从 .env.example 创建。请按需修改后重新执行。" >&2
  cp .env.example .env
  exit 1
fi

SECRET_KEY_VALUE="$(awk -F= '/^SECRET_KEY=/{sub(/\r$/, "", $2); print $2; exit}' .env)"
if [[ -z "${SECRET_KEY_VALUE}" || "${SECRET_KEY_VALUE}" == "auto" ]]; then
  echo "[deploy] SECRET_KEY=auto：容器每次启动会生成临时密钥，重启后旧 token 会失效"
elif [[ "${#SECRET_KEY_VALUE}" -lt 32 ]]; then
  echo "[deploy] .env 中固定 SECRET_KEY 少于 32 字符" >&2
  exit 1
fi

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"
export COMPOSE_DOCKER_CLI_BUILD="${COMPOSE_DOCKER_CLI_BUILD:-1}"
export PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"

echo "[deploy] 校验 Compose 配置"
$COMPOSE config >/dev/null

echo "[deploy] 构建 ${SERVICE}"
$COMPOSE build "$SERVICE"

echo "[deploy] 启动 ${SERVICE}"
$COMPOSE up -d "$SERVICE"

echo "[deploy] 等待健康检查：${HEALTH_URL}"
start_time="$(date +%s)"
while (( $(date +%s) - start_time < MAX_WAIT )); do
  if "$SCRIPT_DIR/health_check.sh" "$HEALTH_URL"; then
    echo "[deploy] 部署完成：${HEALTH_URL}"
    exit 0
  fi
  sleep 3
done

echo "[deploy] ${MAX_WAIT}s 内服务未健康" >&2
$COMPOSE ps >&2 || true
$COMPOSE logs --tail=120 "$SERVICE" >&2 || true
exit 1
