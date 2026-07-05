#!/usr/bin/env bash
set -Eeuo pipefail

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"
APP_STARTUP_TIMEOUT="${APP_STARTUP_TIMEOUT:-90}"
export APP_HOST APP_PORT UVICORN_WORKERS APP_STARTUP_TIMEOUT

export ENVIRONMENT="${ENVIRONMENT:-production}"
if [[ -z "${SECRET_KEY:-}" || "${SECRET_KEY:-}" == "auto" ]]; then
  export SECRET_KEY="$(python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  echo "[entrypoint] 已生成临时 SECRET_KEY（generated ephemeral SECRET_KEY）；容器重启后旧登录 token 会失效"
else
  export SECRET_KEY
fi

export DATABASE_URL="${DATABASE_URL:-sqlite:////app/data/docshop.db}"
export STORAGE_ROOT="${STORAGE_ROOT:-/app/data}"
export UPLOAD_DIR="${UPLOAD_DIR:-/app/data/uploads}"
export LOG_DIR="${LOG_DIR:-/app/data/logs}"
export TEMP_DIR="${TEMP_DIR:-/app/data/temp}"
export MOBILE_MODEL_CACHE_DIR="${MOBILE_MODEL_CACHE_DIR:-/app/data/cache}"
export DOCX2PDF_TIMEOUT_SECONDS="${DOCX2PDF_TIMEOUT_SECONDS:-300}"
export PREVIEW_PDF_TIMEOUT_SECONDS="${PREVIEW_PDF_TIMEOUT_SECONDS:-300}"
export PREVIEW_IMAGE_MAX_WORKERS="${PREVIEW_IMAGE_MAX_WORKERS:-1}"
export SAL_USE_VCLPLUGIN="${SAL_USE_VCLPLUGIN:-svp}"
export HOME="${HOME:-/app}"

cd /app


ensure_writable_dirs() {
  mkdir -p \
    "$UPLOAD_DIR" \
    "$LOG_DIR" \
    "$TEMP_DIR" \
    "$MOBILE_MODEL_CACHE_DIR" \
    /app/data/cache \
    /app/data/covers \
    /app/data/avatars \
    /app/data/documents \
    /app/data/objects \
    /app/data/trash \
    /app/.cache \
    /app/.config \
    /tmp/nginx/client_body \
    /tmp/nginx/proxy \
    /tmp/nginx/fastcgi \
    /tmp/nginx/uwsgi \
    /tmp/nginx/scgi

  if [[ "$(id -u)" == "0" ]]; then
    chown -R docshop:docshop \
      "$UPLOAD_DIR" \
      "$LOG_DIR" \
      "$TEMP_DIR" \
      "$MOBILE_MODEL_CACHE_DIR" \
      /app/data \
      /app/.cache \
      /app/.config \
      /tmp/nginx \
      /var/log/nginx \
      /var/lib/nginx \
      /run/nginx
  fi
}

run_as_app_user() {
  if [[ "$(id -u)" == "0" ]]; then
    gosu docshop "$@"
  else
    "$@"
  fi
}

ensure_writable_dirs

if [[ "${DATABASE_URL}" == "sqlite:////app/data/docshop.db" ]]; then
  echo "[entrypoint] 检查 SQLite 布局迁移：/app/data/docdist.db；docdist.db -> /app/data/docshop.db；/app/backend/data/docshop.db -> /app/data/docshop.db；not overwrite"
  run_as_app_user python /app/scripts/migrate_sqlite_layout.py --root /app --database-url "$DATABASE_URL"
fi

shutdown() {
  local exit_code=$?
  echo "[entrypoint] 正在退出，exit=${exit_code}"
  if [[ -n "${NGINX_PID:-}" ]] && kill -0 "$NGINX_PID" 2>/dev/null; then
    nginx -s quit 2>/dev/null || kill "$NGINX_PID" 2>/dev/null || true
  fi
  if [[ -n "${APP_PID:-}" ]] && kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  exit "$exit_code"
}
trap shutdown INT TERM EXIT

echo "[entrypoint] 初始化数据库"
run_as_app_user python - <<'PY'
from app.database import init_db
import app.models  # noqa: F401

init_db()
PY

if [[ -n "${ADMIN_USERNAME:-}" && -n "${ADMIN_PASSWORD:-}" ]]; then
  echo "[entrypoint] 检查管理员账号：${ADMIN_USERNAME}"
  run_as_app_user python - <<'PY'
import os
from app.database import SessionLocal
from app.models.user import User
from app.utils.security import get_password_hash

admin_user = os.environ.get("ADMIN_USERNAME", "").strip()
admin_pass = os.environ.get("ADMIN_PASSWORD", "")
if not admin_user or not admin_pass:
    print("[entrypoint] 管理员账号或密码为空，跳过")
    raise SystemExit(0)

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == admin_user).first()
    if admin:
        print("[entrypoint] 管理员账号已存在，不覆盖密码")
    else:
        db.add(User(username=admin_user, password_hash=get_password_hash(admin_pass), role="admin"))
        db.commit()
        print("[entrypoint] 管理员账号已创建")
finally:
    db.close()
PY
else
  echo "[entrypoint] 未设置 ADMIN_USERNAME/ADMIN_PASSWORD，跳过管理员初始化"
fi

echo "[entrypoint] 检查 Nginx 配置"
run_as_app_user nginx -t

echo "[entrypoint] 启动 Uvicorn ${APP_HOST}:${APP_PORT} workers=${UVICORN_WORKERS}"
run_as_app_user uvicorn app.main:app \
  --host "$APP_HOST" \
  --port "$APP_PORT" \
  --workers "$UVICORN_WORKERS" \
  --proxy-headers \
  --forwarded-allow-ips='*' &
APP_PID=$!

run_as_app_user python - <<'PY'
import os
import sys
import time
import urllib.request

host = os.environ.get("APP_HOST", "127.0.0.1")
port = os.environ.get("APP_PORT", "8000")
timeout = int(os.environ.get("APP_STARTUP_TIMEOUT", "90"))
url = f"http://{host}:{port}/health"
deadline = time.time() + timeout
last_error = None

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status < 500:
                print(f"[entrypoint] 后端就绪：HTTP {response.status}")
                sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last_error = exc
    time.sleep(1)

print(f"[entrypoint] 后端 {timeout}s 内未就绪：{last_error}", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] 启动 Nginx"
run_as_app_user nginx -g 'daemon off;' &
NGINX_PID=$!

wait -n "$APP_PID" "$NGINX_PID"
