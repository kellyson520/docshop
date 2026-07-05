# syntax=docker/dockerfile:1.7

ARG NODE_IMAGE=node:18.20.8-alpine3.20
ARG PYTHON_IMAGE=python:3.11.11-slim-bookworm
ARG APT_MIRROR=
ARG APT_SECURITY_MIRROR=
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# ============================================================
# Stage 1: frontend dependencies
# ============================================================
FROM ${NODE_IMAGE} AS frontend-deps

WORKDIR /frontend

# Copy lock files first to maximize dependency-layer cache hits.
COPY frontend/package.json frontend/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm \
    npm ci \
      --registry=https://registry.npmmirror.com \
      --prefer-offline \
      --no-audit \
      --no-fund

# ============================================================
# Stage 2: frontend build
# ============================================================
FROM frontend-deps AS frontend-builder

WORKDIR /frontend
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
RUN npm run build

# ============================================================
# Stage 3: production runtime
# ============================================================
FROM ${PYTHON_IMAGE} AS runtime

ARG APT_MIRROR
ARG APT_SECURITY_MIRROR
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

LABEL maintainer="docshop"
LABEL description="DocShop production image"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    ENVIRONMENT=production \
    STORAGE_ROOT=/app/data \
    DATABASE_URL=sqlite:////app/data/docshop.db \
    UPLOAD_DIR=/app/data/uploads \
    LOG_DIR=/app/data/logs \
    TEMP_DIR=/app/data/temp \
    MOBILE_MODEL_CACHE_DIR=/app/data/cache \
    DOCX2PDF_TIMEOUT_SECONDS=300 \
    PREVIEW_PDF_TIMEOUT_SECONDS=300 \
    PREVIEW_IMAGE_MAX_WORKERS=1 \
    UVICORN_WORKERS=1 \
    SAL_USE_VCLPLUGIN=svp \
    HOME=/app

WORKDIR /app

# Runtime dependencies:
# - nginx/curl/sqlite3: serving, healthcheck and SQLite inspection
# - libreoffice*: Linux DOC/DOCX/XLS/XLSX -> PDF conversion inside Docker
# - CJK fonts/fontconfig: readable Chinese document rendering
# - poppler-utils: common PDF diagnostic/conversion utilities
# - tini/procps: signal handling and process inspection
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    set -eux; \
    if [ -n "${APT_MIRROR}" ] || [ -n "${APT_SECURITY_MIRROR}" ]; then \
      APT_MIRROR="${APT_MIRROR:-http://deb.debian.org/debian}"; \
      APT_SECURITY_MIRROR="${APT_SECURITY_MIRROR:-http://deb.debian.org/debian-security}"; \
      printf '%s\n' \
        'Types: deb' \
        "URIs: ${APT_MIRROR}" \
        'Suites: bookworm bookworm-updates' \
        'Components: main' \
        'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
        '' \
        'Types: deb' \
        "URIs: ${APT_SECURITY_MIRROR}" \
        'Suites: bookworm-security' \
        'Components: main' \
        'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
        > /etc/apt/sources.list.d/debian.sources; \
      rm -f /etc/apt/sources.list; \
      cat /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update -o Acquire::Retries=5 && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      fontconfig \
      fonts-noto-cjk \
      fonts-wqy-microhei \
      fonts-wqy-zenhei \
      gosu \
      libreoffice-calc \
      libreoffice-math \
      libreoffice-writer \
      nginx \
      poppler-utils \
      procps \
      sqlite3 \
      tini \
      fonts-dejavu-core \
      fonts-dejavu-extra \
      fonts-opensymbol \
      fonts-stix && \
    fc-cache -f && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Python dependencies are isolated from application code for faster rebuilds.
COPY backend/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip_args="--retries 20 --default-timeout 300 --prefer-binary --progress-bar off"; \
    if [ -n "${PIP_INDEX_URL}" ]; then \
      pip_args="${pip_args} --index-url ${PIP_INDEX_URL}"; \
    fi; \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then \
      pip_args="${pip_args} --trusted-host ${PIP_TRUSTED_HOST}"; \
    fi; \
    python -m pip wheel ${pip_args} --wheel-dir /tmp/wheels -r requirements.txt; \
    python -m pip install --no-index --find-links=/tmp/wheels -r requirements.txt; \
    rm -rf /tmp/wheels

# Runtime files.
COPY backend/app ./app
COPY backend/start.sh /start.sh
COPY backend/nginx.conf /etc/nginx/nginx.conf
COPY scripts/backup.sh scripts/restore.sh scripts/health_check.sh scripts/migrate_sqlite_layout.py /app/scripts/
COPY --from=frontend-builder /frontend/dist ./dist

# Non-root runtime user and writable directories for nginx/app data.
RUN groupadd -r docshop && \
    useradd -r -g docshop -d /app -s /usr/sbin/nologin docshop && \
    mkdir -p \
      /app/data/uploads \
      /app/data/logs \
      /app/data/temp \
      /app/data/cache \
      /app/data/covers \
      /app/data/avatars \
      /app/data/documents \
      /app/data/objects \
      /app/data/trash \
      /app/scripts \
      /app/.cache \
      /app/.config \
      /var/log/nginx \
      /var/lib/nginx \
      /run/nginx \
      /tmp/nginx/client_body \
      /tmp/nginx/proxy \
      /tmp/nginx/fastcgi \
      /tmp/nginx/uwsgi \
      /tmp/nginx/scgi && \
    chmod +x /start.sh /app/scripts/*.sh && \
    chown -R docshop:docshop \
      /app \
      /var/log/nginx \
      /var/lib/nginx \
      /run/nginx \
      /tmp/nginx \
      /start.sh

VOLUME ["/app/data"]

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=5 \
    CMD curl -fs http://localhost:80/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/start.sh"]


# ============================================================
# Stage 4: backend development runtime
# ============================================================
# Used by docker-compose.dev.yml. Python dependencies and system
# preview tools stay inside the image, while ./backend/app is bind
# mounted for hot reload.
FROM runtime AS backend-dev

ENV ENVIRONMENT=development \
    DEBUG=true \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    STORAGE_ROOT=/app/data \
    DATABASE_URL=sqlite:////app/data/docshop.db \
    UPLOAD_DIR=/app/data/uploads \
    LOG_DIR=/app/data/logs \
    TEMP_DIR=/app/data/temp \
    MOBILE_MODEL_CACHE_DIR=/app/data/cache

EXPOSE 8000

CMD ["sh", "-lc", "mkdir -p /app/data/uploads /app/data/logs /app/data/temp /app/data/cache /app/data/covers /app/data/avatars /app/data/documents /app/data/objects /app/data/trash && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app"]

# ============================================================
# Stage 5: frontend development runtime
# ============================================================
# Used by docker-compose.dev.yml. node_modules are kept in an
# anonymous volume so bind mounting ./frontend does not overwrite
# dependencies installed at image build time.
FROM frontend-deps AS frontend-dev

WORKDIR /frontend
ENV NODE_ENV=development
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
