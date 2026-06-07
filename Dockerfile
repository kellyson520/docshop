# syntax=docker/dockerfile:1.7

ARG NODE_IMAGE=node:18.20.8-alpine3.20
ARG PYTHON_IMAGE=python:3.11.11-slim-bookworm

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

LABEL maintainer="docdist"
LABEL description="DocDist production image"
LABEL version="1.0.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    ENVIRONMENT=production

WORKDIR /app

# Keep apt package downloads cached by BuildKit while leaving the final layer clean.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends nginx curl sqlite3 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies are isolated from application code for faster rebuilds.
COPY backend/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Runtime files.
COPY backend/app ./app
COPY backend/start.sh /start.sh
COPY backend/nginx.conf /etc/nginx/nginx.conf
COPY --from=frontend-builder /frontend/dist ./dist

# Non-root runtime user and writable directories for nginx/app data.
RUN groupadd -r docdist && \
    useradd -r -g docdist -d /app -s /sbin/nologin docdist && \
    mkdir -p \
      /app/data/uploads \
      /var/log/nginx \
      /var/lib/nginx \
      /run/nginx \
      /tmp/nginx/client_body \
      /tmp/nginx/proxy \
      /tmp/nginx/fastcgi \
      /tmp/nginx/uwsgi \
      /tmp/nginx/scgi && \
    chmod +x /start.sh && \
    chown -R docdist:docdist \
      /app \
      /var/log/nginx \
      /var/lib/nginx \
      /run/nginx \
      /tmp/nginx \
      /start.sh

VOLUME ["/app/data"]

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fs http://localhost:80/api/v1/health || exit 1

USER docdist

CMD ["/start.sh"]
