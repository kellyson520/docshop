#!/usr/bin/env bash
set -Eeuo pipefail

# DocDist VPS production build helper.
# Default behavior: generate/check .env, enable BuildKit, then build the Docker image.
# It does NOT start the service unless --up is provided.

trap 'echo "[docdist-vps] failed at line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SERVICE="${SERVICE:-docdist}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/.env}"

CALLER_DOCDIST_IMAGE_SET="${DOCDIST_IMAGE+x}"
CALLER_DOCDIST_PORT_SET="${DOCDIST_PORT+x}"
CALLER_NODE_IMAGE_SET="${NODE_IMAGE+x}"
CALLER_PYTHON_IMAGE_SET="${PYTHON_IMAGE+x}"

DOCDIST_IMAGE="${DOCDIST_IMAGE:-docdist:latest}"
DOCDIST_PORT="${DOCDIST_PORT:-80}"
NODE_IMAGE="${NODE_IMAGE:-node:18.20.8-alpine3.20}"
PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.11.11-slim-bookworm}"

PULL=0
NO_CACHE=0
UP=0
PRUNE=0
INSTALL_DOCKER=0
RECREATE_ENV=0
USE_SUDO_DOCKER=0

log() {
  printf '[docdist-vps] %s\n' "$*"
}

die() {
  printf '[docdist-vps] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
DocDist VPS build script

Usage:
  bash scripts/vps-build.sh [options]

Options:
  --pull             Build with latest base images.
  --no-cache         Disable Docker layer cache for this build.
  --up               Start/recreate the service after build.
  --prune            Remove old BuildKit builder cache older than 72h after build.
  --install-docker   Install Docker Engine + Compose plugin on Ubuntu/Debian if missing.
  --recreate-env     Regenerate .env; existing file is backed up first.
  -h, --help         Show this help.

Environment overrides:
  APP_DIR=/opt/docdist
  SERVICE=docdist
  ENV_FILE=/opt/docdist/.env
  DOCDIST_IMAGE=docdist:latest
  DOCDIST_PORT=80
  NODE_IMAGE=node:18.20.8-alpine3.20
  PYTHON_IMAGE=python:3.11.11-slim-bookworm

Examples:
  chmod +x scripts/vps-build.sh
  bash scripts/vps-build.sh --pull
  bash scripts/vps-build.sh --pull --up
  bash scripts/vps-build.sh --install-docker --pull --up
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull)
      PULL=1
      ;;
    --no-cache)
      NO_CACHE=1
      ;;
    --up)
      UP=1
      ;;
    --prune)
      PRUNE=1
      ;;
    --install-docker)
      INSTALL_DOCKER=1
      ;;
    --recreate-env)
      RECREATE_ENV=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
  shift
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

sudo_prefix() {
  if [[ "$(id -u)" -eq 0 ]]; then
    return 0
  fi
  command -v sudo >/dev/null 2>&1 || die "sudo is required for this action"
}

install_docker() {
  [[ -r /etc/os-release ]] || die "Cannot detect OS; /etc/os-release is missing"
  # shellcheck disable=SC1091
  . /etc/os-release

  case "${ID:-}" in
    ubuntu|debian)
      ;;
    *)
      die "--install-docker currently supports Ubuntu/Debian only; detected ID=${ID:-unknown}"
      ;;
  esac

  sudo_prefix
  local SUDO=""
  if [[ "$(id -u)" -ne 0 ]]; then
    SUDO="sudo"
  fi

  local codename="${VERSION_CODENAME:-}"
  if [[ -z "${codename}" ]] && command -v lsb_release >/dev/null 2>&1; then
    codename="$(lsb_release -cs)"
  fi
  [[ -n "${codename}" ]] || die "Cannot determine Ubuntu/Debian codename"

  log "Installing Docker Engine and Compose plugin for ${ID} ${codename}"
  ${SUDO} apt-get update
  ${SUDO} apt-get install -y ca-certificates curl gnupg
  ${SUDO} install -m 0755 -d /etc/apt/keyrings

  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL "https://download.docker.com/linux/${ID}/gpg" \
      | ${SUDO} gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    ${SUDO} chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} ${codename} stable" \
    | ${SUDO} tee /etc/apt/sources.list.d/docker.list >/dev/null

  ${SUDO} apt-get update
  ${SUDO} apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  if [[ "$(id -u)" -ne 0 ]]; then
    ${SUDO} usermod -aG docker "$USER" || true
    log "Current user was added to docker group. If docker still needs sudo, re-login once."
  fi
}

docker_cmd() {
  if [[ "${USE_SUDO_DOCKER}" -eq 1 ]]; then
    sudo docker "$@"
  else
    docker "$@"
  fi
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    if [[ "${INSTALL_DOCKER}" -eq 1 ]]; then
      install_docker
    else
      die "Docker is not installed. Re-run with --install-docker or install Docker manually."
    fi
  fi

  if docker info >/dev/null 2>&1; then
    USE_SUDO_DOCKER=0
  elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    USE_SUDO_DOCKER=1
    log "Docker requires sudo for current user; using sudo docker."
  else
    die "Cannot access Docker daemon. Start Docker or re-login after joining docker group."
  fi

  docker_cmd compose version >/dev/null 2>&1 \
    || die "Docker Compose v2 plugin is not available. Install docker-compose-plugin."
}

random_hex() {
  local bytes="$1"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "${bytes}"
  else
    head -c "${bytes}" /dev/urandom | od -An -tx1 -v | tr -d ' \n'
  fi
}

backup_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    local backup="${file}.bak.$(date +%Y%m%d%H%M%S)"
    cp "${file}" "${backup}"
    chmod 600 "${backup}" || true
    log "Backed up existing env file: ${backup}"
  fi
}

env_get() {
  local key="$1"
  awk -v key="${key}" '
    BEGIN { FS="=" }
    /^[[:space:]]*#/ { next }
    $1 == key {
      sub(/^[^=]*=/, "")
      sub(/\r$/, "")
      print
      exit
    }
  ' "${ENV_FILE}" 2>/dev/null || true
}

validate_and_load_env() {
  local secret_key
  local value

  secret_key="$(env_get SECRET_KEY)"
  if [[ -z "${secret_key}" || "${secret_key}" == "your-secret-key-here" ]]; then
    die "SECRET_KEY is missing or still uses the placeholder in ${ENV_FILE}. Edit it or run with --recreate-env."
  fi

  value="$(env_get DOCDIST_IMAGE)"
  [[ -z "${CALLER_DOCDIST_IMAGE_SET}" && -n "${value}" ]] && DOCDIST_IMAGE="${value}"

  value="$(env_get DOCDIST_PORT)"
  [[ -z "${CALLER_DOCDIST_PORT_SET}" && -n "${value}" ]] && DOCDIST_PORT="${value}"

  value="$(env_get NODE_IMAGE)"
  [[ -z "${CALLER_NODE_IMAGE_SET}" && -n "${value}" ]] && NODE_IMAGE="${value}"

  value="$(env_get PYTHON_IMAGE)"
  [[ -z "${CALLER_PYTHON_IMAGE_SET}" && -n "${value}" ]] && PYTHON_IMAGE="${value}"
}

write_env_file() {
  local target="$1"
  local secret_key
  local admin_password

  secret_key="$(random_hex 32)"
  admin_password="$(random_hex 12)"

  umask 077
  cat > "${target}" <<EOF
# DocDist production environment
# Generated by scripts/vps-build.sh on $(date -Iseconds)

ENVIRONMENT=production
DEBUG=false

SECRET_KEY=${secret_key}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${admin_password}

DATABASE_URL=sqlite:////app/data/docdist.db
UPLOAD_DIR=/app/data/uploads

DOCDIST_IMAGE=${DOCDIST_IMAGE}
DOCDIST_PORT=${DOCDIST_PORT}
NODE_IMAGE=${NODE_IMAGE}
PYTHON_IMAGE=${PYTHON_IMAGE}

ACCESS_TOKEN_EXPIRE_MINUTES=1440
MAX_FILE_SIZE=52428800
MAX_REQUEST_BODY_SIZE=104857600
ALLOWED_FILE_TYPES=.pdf,.docx,.xlsx,.xls,.png,.jpg,.jpeg

MAX_WORKERS=4
DIFF_ENGINE_TIMEOUT=300
CACHE_TYPE=memory
LOG_LEVEL=INFO

CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
API_PREFIX=/api/v1
TIMEZONE=Asia/Shanghai
DEFAULT_LANGUAGE=zh-CN
EOF

  chmod 600 "${target}" || true
  log "Generated env file: ${target}"
  log "Initial admin account:"
  log "  username: admin"
  log "  password: ${admin_password}"
  log "Save this password now. It is only printed when .env is generated."
}

ensure_env() {
  mkdir -p "$(dirname "${ENV_FILE}")"

  if [[ -f "${ENV_FILE}" && "${RECREATE_ENV}" -eq 0 ]]; then
    log "Using existing env file: ${ENV_FILE}"
  else
    backup_file "${ENV_FILE}"
    write_env_file "${ENV_FILE}"
  fi

  local compose_env="${APP_DIR}/.env"
  if [[ "${ENV_FILE}" != "${compose_env}" ]]; then
    backup_file "${compose_env}"
    cp "${ENV_FILE}" "${compose_env}"
    chmod 600 "${compose_env}" || true
    log "Synced ${ENV_FILE} to docker-compose env file: ${compose_env}"
  fi
}

ensure_project() {
  [[ -f "${APP_DIR}/Dockerfile" ]] || die "Dockerfile not found in APP_DIR=${APP_DIR}"
  [[ -f "${APP_DIR}/docker-compose.yml" ]] || die "docker-compose.yml not found in APP_DIR=${APP_DIR}"
  mkdir -p "${APP_DIR}/data/uploads"
}

build_image() {
  local build_args=()
  [[ "${PULL}" -eq 1 ]] && build_args+=(--pull)
  [[ "${NO_CACHE}" -eq 1 ]] && build_args+=(--no-cache)

  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1
  export DOCDIST_IMAGE DOCDIST_PORT NODE_IMAGE PYTHON_IMAGE

  log "Building service=${SERVICE}, image=${DOCDIST_IMAGE}, app=${APP_DIR}"
  cd "${APP_DIR}"
  docker_cmd compose --env-file "${ENV_FILE}" build "${build_args[@]}" "${SERVICE}"
}

start_service() {
  log "Starting service=${SERVICE} on port=${DOCDIST_PORT}"
  cd "${APP_DIR}"
  docker_cmd compose --env-file "${ENV_FILE}" up -d "${SERVICE}"
  docker_cmd compose --env-file "${ENV_FILE}" ps "${SERVICE}"
  log "Open: http://<your-vps-ip>:${DOCDIST_PORT}"
}

prune_cache() {
  log "Pruning Docker builder cache older than 72h"
  docker_cmd builder prune -af --filter until=72h
}

main() {
  ensure_project
  ensure_env
  validate_and_load_env
  ensure_docker
  build_image

  if [[ "${UP}" -eq 1 ]]; then
    start_service
  else
    log "Build finished. Service not started because --up was not provided."
  fi

  if [[ "${PRUNE}" -eq 1 ]]; then
    prune_cache
  fi
}

main "$@"
