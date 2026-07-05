# DocShop Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将项目对外品牌、默认部署名、默认数据库名从 DocShop/docshop 改为 DocShop/docshop，同时保留旧 Docker SQLite 数据库兼容迁移。

**Architecture:** 以测试约束改名契约：部署配置、后端配置、前端品牌文本各自有可验证断言。数据库兼容由容器 entrypoint 在默认 `docshop.db` 不存在且旧 `docshop.db` 存在时复制旧库。

**Tech Stack:** FastAPI/Python/pytest, Vue/Vite/npm, Docker Compose, Bash entrypoint。

---

### Task 1: 改名契约测试

**Files:**
- Modify: `backend/tests/test_docker_deployment_contract.py`
- Modify: `backend/tests/test_config.py`
- Create: `backend/tests/test_docshop_branding_contract.py`

- [x] **Step 1: Write failing tests**
  - 部署契约断言 `docshop:latest`、`docshop.db`。
  - `backend/start.sh` 断言包含 `docshop.db` 到 `docshop.db` 的兼容迁移。
  - 品牌扫描排除 `.git/node_modules/dist/data/artifacts/logs/cache`，断言源码与配置不再保留 `DocShop/docshop/DOCSHOP`。

- [x] **Step 2: Run tests to verify they fail**
  Run: `python -m pytest backend\tests\test_docker_deployment_contract.py backend\tests\test_config.py backend\tests\test_docshop_branding_contract.py -q`
  Expected: FAIL because production files still contain DocShop/docshop defaults.

### Task 2: 后端与部署配置改名

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `.env`
- Modify: `backend/.env`
- Modify: `backend/start.sh`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/utils/logger.py`

- [x] **Step 1: Implement minimal changes**
  - `docshop:latest` -> `docshop:latest`
  - `docshop.db` -> `docshop.db`
  - FastAPI title/log/secret placeholder/logger namespace -> DocShop/docshop
  - `backend/start.sh` adds legacy DB copy before DB init.

- [x] **Step 2: Run backend contract tests**
  Run: `python -m pytest backend\tests\test_docker_deployment_contract.py backend\tests\test_config.py backend\tests\test_docshop_branding_contract.py -q`

### Task 3: 前端、文档、脚本展示改名

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/index.html`
- Modify: `frontend/src/**`
- Modify: `README.md`, `docs/**`, `scripts/**`, `start-lan.bat` where brand/default image/db appears.

- [x] **Step 1: Replace user-visible and config references**
  Use text replacement for `DocShop` -> `DocShop`, `docshop` -> `docshop`, `DOCSHOP` -> `DOCSHOP` on source/config/doc files, excluding generated/user data paths.

- [x] **Step 2: Build and regression tests**
  Run:
  - `python -m pytest backend\tests\test_settings_password.py backend\tests\test_public_project_uploader.py backend\tests\test_share.py -q`
  - `Push-Location frontend; npm run build; Pop-Location`
  - `docker compose config`

### Task 4: Verification checklist

- [x] Brand scan shows no unintended `DocShop/docshop/DOCSHOP` in source/config/docs, except explicitly allowed legacy migration strings.
- [x] Docker defaults use `docshop:latest` and `/app/data/docshop.db`.
- [x] Legacy migration string remains in `backend/start.sh`.
- [x] Backend focused tests pass.
- [x] Frontend build exits 0.
- [x] Docker Compose config exits 0.
