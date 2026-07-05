# Dependency inventory

本文档列出 DocShop/DocShop 运行、构建和文档转换所需的必要依赖。实际安装入口仍以 `backend/requirements.txt`、`frontend/package-lock.json` 和 `Dockerfile` 为准；本清单用于部署前核对环境。

## Python runtime

安装入口：`backend/requirements.txt`

| Dependency | Purpose |
| --- | --- |
| `fastapi` | API framework |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy` | ORM and SQLite access |
| `pydantic`, `pydantic-settings` | schemas and environment config |
| `python-jose[cryptography]` | JWT signing/verification |
| `passlib[bcrypt]`, `bcrypt` | password hashing |
| `python-multipart`, `aiofiles` | upload handling |
| `python-docx` | DOCX parsing and HTML fallback preview |
| `openpyxl` | XLSX parsing and preview |
| `pandas`, `numpy` | spreadsheet diff/normalization |
| `Pillow` | DOCX embedded image thumbnail handling |
| `PyMuPDF` | PDF page counting and image rendering |
| `pdfplumber` | PDF text extraction for diff |
| `diff-match-patch` | text diff engine |
| `requests` | fetching external DOCX relationship images before sanitizing/fallback |
| `user-agents`, `geoip2` | optional access tracking enrichment |
| `cachetools` | in-memory TTL cache helpers |
| `pywin32` | Optional Windows Word COM conversion path; installed only when `platform_system=="Windows"` |

## Dev / test dependencies

安装入口：`backend/requirements-dev.txt`

| Dependency | Purpose |
| --- | --- |
| `pytest`, `pytest-asyncio`, `pytest-cov` | test runner / async + coverage |
| `httpx` | async HTTP test client |
| `factory-boy`, `faker` | test data factories |
| `psutil` | memory profiling in performance tests (`tests/performance/test_memory.py`) |

## Load testing dependencies

安装入口：手动安装（`pip install locust`），不入 `requirements-dev.txt` 以免拉入较大依赖树。

| Dependency | Purpose |
| --- | --- |
| `locust` | HTTP load testing (`backend/load_tests/locustfile.py`) |

## Optional Windows Word COM

Windows 本地部署如果安装了 Microsoft Word，后端会尝试通过 `pywin32` / `win32com.client` 调用 Word COM，把 DOC/DOCX 转成高保真 PDF。该能力只在 Windows 可用；Linux Docker 不安装 `pywin32`，而是使用 LibreOffice。

## Node build

安装入口：`frontend/package-lock.json`，通过 `npm ci` 安装。

| Dependency | Purpose |
| --- | --- |
| `vue`, `vue-router`, `pinia` | frontend framework, routing and state |
| `axios` | API client |
| `element-plus`, `@element-plus/icons-vue` | UI components/icons |
| `diff-match-patch` | browser-side diff display helpers |
| `vite`, `@vitejs/plugin-vue` | production frontend build |
| `vitest`, `@vue/test-utils`, `@testing-library/vue`, `jsdom`, `msw` | frontend tests |
| `@playwright/test` | e2e tests |

## Docker runtime system packages

安装入口：`Dockerfile` runtime stage 的 `apt-get install`。

| Package | Purpose |
| --- | --- |
| `nginx` | serve frontend and reverse proxy API |
| `curl` | container healthcheck |
| `sqlite3` | SQLite inspection/debugging |
| `ca-certificates` | HTTPS certificate store for Python/LibreOffice/curl |
| `LibreOffice` (`libreoffice-writer`, `libreoffice-calc`, `libreoffice-math`) | Linux DOC/DOCX/XLS/XLSX to PDF conversion, including Word formula rendering |
| `fonts-noto-cjk`, `fonts-wqy-microhei`, `fonts-wqy-zenhei`, `fonts-opensymbol`, `fonts-stix`, `fonts-dejavu-core`, `fontconfig` | Chinese/CJK and formula/symbol font rendering plus font cache |
| `poppler-utils` | PDF diagnostics/conversion utilities |
| `tini` | signal forwarding/reaping for container PID 1 |
| `procps` | process inspection while diagnosing container issues |

## External host requirements

| Tool | Required for |
| --- | --- |
| Docker Engine | building/running production image |
| Docker Compose v2 | `docker compose build/up/config` |
| Node.js 18+ | local frontend development outside Docker |
| Python 3.11+ | local backend development outside Docker |
| Microsoft Word | optional high-fidelity DOC/DOCX conversion on Windows local deployment |

## Notes

- Docker 镜像内的文档转换路径是 LibreOffice，不依赖 Microsoft Word。
- `PREVIEW_IMAGE_MAX_WORKERS=1` 是低内存环境的安全默认值；资源充足时可调到 `2` 或 `4`。
- 新增直接 import 的第三方 Python 包时，应同步更新 `backend/requirements.txt` 和本文件。


## Mobile model cache data source

| Dependency | Purpose |
| --- | --- |
| `MobileModels-csv` | Local Android model-code mapping source for access-log display enrichment |

- Upstream: `https://github.com/KHwang9883/MobileModels-csv`
- License / attribution: `CC BY-NC-SA 4.0`
- Runtime behavior: the backend downloads the CSV into a local cache and continues using the previous cache when refresh fails.
- Cache artifacts: `data/cache/mobile_models.csv`, `data/cache/mobile_models.json`, `data/cache/mobile_models.meta.json`
