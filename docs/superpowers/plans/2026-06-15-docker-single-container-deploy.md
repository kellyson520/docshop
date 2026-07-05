# Docker 单容器部署完善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 DocShop 的 Docker 部署打磨成低占用、单容器、局域网/VPS 可直接运行的流程，并修复现有部署文件中的乱码、旧命名和潜在预览依赖问题。

**Architecture:** 保持一个生产容器，镜像内包含前端静态构建、FastAPI 后端、Nginx 反向代理。运行时只挂载 `/app/data` 和 `.env`，后台预览继续使用现有轻量内存队列和本地 meta/cache。

**Tech Stack:** Docker Compose、Python 3.11 slim、Node 18 build stage、Nginx、FastAPI/Uvicorn、SQLite、本地文件存储、LibreOffice/headless 字体依赖。

---

### Task 1: 修复 Docker runtime 与启动脚本

**Files:**
- Modify: `Dockerfile`
- Modify: `backend/start.sh`
- Test: `docker compose config`

- [ ] 将镜像 label、用户、目录命名从 docshop 统一成 docshop，同时保留 compose 变量兼容。
- [ ] 安装 headless 预览依赖：`libreoffice-writer`, `libreoffice-calc`, `fonts-noto-cjk`, `fontconfig`，用于 Docker 内 doc/docx/xls/xlsx 转 PDF。
- [ ] 重写 `backend/start.sh` 为 UTF-8 中文日志，创建 `/app/data/uploads|logs|temp|cache`，初始化 DB，按环境变量创建管理员，启动 uvicorn 和 nginx。
- [ ] 使用 `app.utils.security.get_password_hash` 生成管理员密码，避免启动脚本和应用哈希逻辑分叉。
- [ ] 运行 `docker compose config`，预期配置能正常展开。

### Task 2: 修复 Compose/env/nginx 生产默认值

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/nginx.conf`
- Replace: `.env.example`
- Test: `docker compose config`

- [ ] compose service 改为 `docshop`，image 改为 `docshop:latest`，保留 `DOCSHOP_*` 兼容变量或提供清晰迁移。
- [ ] 设置生产默认环境变量：`DATABASE_URL=sqlite:////app/data/docshop.db`、`UPLOAD_DIR=/app/data/uploads`、`LOG_DIR=/app/data/logs`、`TEMP_DIR=/app/data/temp`、`DOCX2PDF_TIMEOUT_SECONDS=300`。
- [ ] nginx 移除默认 HSTS，避免 HTTP 局域网部署误导浏览器；保留其它安全头。
- [ ] nginx `client_max_body_size` 设置为 100m，与 env 示例的 `MAX_FILE_SIZE` 保持一致或在文档中解释。
- [ ] `.env.example` 重写为 UTF-8 中文，包含必填 `SECRET_KEY`、可选 `ADMIN_USERNAME/ADMIN_PASSWORD`、端口、上传限制、CORS、预览超时。

### Task 3: 增加 Windows/Linux 运维脚本

**Files:**
- Create: `scripts/docker-up.ps1`
- Create: `scripts/docker-down.ps1`
- Create: `scripts/docker-logs.ps1`
- Modify: `scripts/docker-build.ps1`
- Modify: `scripts/health_check.sh`
- Modify: `scripts/backup.sh`
- Test: PowerShell 脚本静态解析；`bash -n` 检查 shell 脚本。

- [ ] `docker-up.ps1` 检查 `.env` 是否存在，不存在则从 `.env.example` 复制并提示填写 `SECRET_KEY`；执行 `docker compose up -d --build`。
- [ ] `docker-down.ps1` 执行 `docker compose down`，可选 `-RemoveVolumes` 但默认不删数据。
- [ ] `docker-logs.ps1` 默认跟踪 `docshop` 服务日志。
- [ ] `health_check.sh` 默认使用 DocShop 路径和日志目录 `/var/log/docshop`。
- [ ] `backup.sh` 默认备份 `/app/data/docshop.db` 和 uploads 到 `/backup/docshop`，同时兼容旧 `docshop.db`。

### Task 4: 文档和验证

**Files:**
- Create: `docs/docker-deploy.md`
- Modify: `README.md`
- Test: `npm run build`, backend focused tests, `docker compose config`

- [ ] 写 Docker 部署文档：Windows 一键部署、Linux/VPS 部署、局域网访问、初始化管理员、备份恢复、查看日志、常见问题。
- [ ] README 增加 Docker 快速入口并链接到 `docs/docker-deploy.md`。
- [ ] 运行 `npm run build`，预期 exit 0。
- [ ] 运行 `pytest backend/tests/test_preview_queue.py backend/tests/test_tracking_middleware.py backend/tests/test_share_tokens_api.py -q`，预期全部通过。
- [ ] 运行 `docker compose config`，预期 exit 0。
- [ ] 如果 Docker 可用，运行 `docker compose build docshop`，预期构建成功。
