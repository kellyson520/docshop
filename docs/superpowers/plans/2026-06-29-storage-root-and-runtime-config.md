# Storage Root And Runtime Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一 DocShop 的唯一存储根到仓库根 `data/`，并让设置页中的运行期配置在进程内立即生效，而不是依赖 uvicorn reload。

**Architecture:** 在 `backend/app/config.py` 中引入统一路径解析与显式存储目录派生；新增运行期配置刷新服务专门处理热生效和副作用同步；设置路由只允许更新运行期配置并统一返回错误。当前仓库已有大量未提交改动，执行时不做 git commit，避免混入用户现有工作。

**Tech Stack:** FastAPI, Pydantic Settings, SQLAlchemy, Python logging, Pytest

---

### Task 1: 统一配置层的存储根与相对路径解析

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 写失败测试，覆盖仓库根存储路径与 SQLite 路径规范化**

```python
def test_relative_storage_dirs_resolve_from_project_root(tmp_path, monkeypatch):
    from app.config import Settings

    project_root = tmp_path / "docshop"
    backend_root = project_root / "backend"
    backend_root.mkdir(parents=True)
    fake_config = backend_root / "app" / "config.py"
    fake_config.parent.mkdir(parents=True, exist_ok=True)
    fake_config.write_text("# stub", encoding="utf-8")

    monkeypatch.setattr("app.config.__file__", str(fake_config))

    settings = Settings(
        _env_file=None,
        STORAGE_ROOT="./data",
        UPLOAD_DIR="./data/uploads",
        LOG_DIR="./data/logs",
        TEMP_DIR="./data/temp",
        MOBILE_MODEL_CACHE_DIR="./data/cache",
    )

    assert settings.STORAGE_ROOT == str((project_root / "data").resolve())
    assert settings.UPLOAD_DIR == str((project_root / "data" / "uploads").resolve())
    assert settings.LOG_DIR == str((project_root / "data" / "logs").resolve())
    assert settings.TEMP_DIR == str((project_root / "data" / "temp").resolve())
    assert settings.MOBILE_MODEL_CACHE_DIR == str((project_root / "data" / "cache").resolve())


def test_relative_sqlite_database_url_resolves_from_project_root(tmp_path, monkeypatch):
    from app.config import Settings

    project_root = tmp_path / "docshop"
    backend_root = project_root / "backend"
    backend_root.mkdir(parents=True)
    fake_config = backend_root / "app" / "config.py"
    fake_config.parent.mkdir(parents=True, exist_ok=True)
    fake_config.write_text("# stub", encoding="utf-8")

    monkeypatch.setattr("app.config.__file__", str(fake_config))

    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite:///./data/docshop.db",
    )

    assert settings.DATABASE_URL == f"sqlite:///{(project_root / 'data' / 'docshop.db').resolve().as_posix()}"
```

- [ ] **Step 2: 运行测试，确认先失败**

Run: `python -m pytest backend/tests/test_config.py -q`

Expected: 新增两个测试失败，原因是当前配置仍按 cwd 解析相对路径，且未统一 `STORAGE_ROOT`。

- [ ] **Step 3: 在配置层实现统一存储根与相对 SQLite 解析**

```python
class Settings(BaseSettings):
    STORAGE_ROOT: str = "./data"

    @classmethod
    def _project_root(cls) -> Path:
        return Path(__file__).resolve().parents[2]

    @classmethod
    def _resolve_project_path(cls, value: str | Path) -> str:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = cls._project_root() / candidate
        return str(candidate.resolve(strict=False))

    @field_validator("STORAGE_ROOT", "UPLOAD_DIR", "LOG_DIR", "TEMP_DIR", "MOBILE_MODEL_CACHE_DIR")
    @classmethod
    def validate_directory_paths(cls, v: str) -> str:
        return cls._resolve_project_path(str(v).strip())

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        raw = str(v).strip()
        if raw.startswith("sqlite:///./") or raw.startswith("sqlite:///data/"):
            relative = raw.removeprefix("sqlite:///")
            path = cls._resolve_project_path(relative)
            return f"sqlite:///{Path(path).as_posix()}"
        return raw
```

- [ ] **Step 4: 增加显式派生目录属性，供后续代码替换隐式 parent 推导**

```python
    @property
    def covers_dir(self) -> Path:
        return self._safe_child_path(self.STORAGE_ROOT, "covers")

    @property
    def avatars_dir(self) -> Path:
        return self._safe_child_path(self.STORAGE_ROOT, "avatars")

    @property
    def documents_dir(self) -> Path:
        return self._safe_child_path(self.STORAGE_ROOT, "documents")

    @property
    def objects_dir(self) -> Path:
        return self._safe_child_path(self.STORAGE_ROOT, "objects")

    @property
    def trash_dir(self) -> Path:
        return self._safe_child_path(self.STORAGE_ROOT, "trash")
```

- [ ] **Step 5: 跑回测试确认通过**

Run: `python -m pytest backend/tests/test_config.py -q`

Expected: `backend/tests/test_config.py` 通过，新增路径规范化断言为绿。

---

### Task 2: 增加运行期配置刷新服务与日志热生效

**Files:**
- Create: `backend/app/services/runtime_config.py`
- Modify: `backend/app/utils/logger.py`
- Test: `backend/tests/test_runtime_config.py`

- [ ] **Step 1: 写失败测试，覆盖运行期配置刷新与日志级别重配置**

```python
def test_apply_runtime_settings_updates_global_settings(monkeypatch, tmp_path):
    from app.config import settings
    from app.services.runtime_config import apply_runtime_settings

    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=ERROR\nMAX_FILE_SIZE=1048576\n", encoding="utf-8")

    apply_runtime_settings(env_file=env_file)

    assert settings.LOG_LEVEL == "ERROR"
    assert settings.MAX_FILE_SIZE == 1048576


def test_reconfigure_logging_uses_new_log_level(monkeypatch):
    import logging
    from app.config import settings
    from app.utils import logger as logger_module

    monkeypatch.setattr(settings, "LOG_LEVEL", "ERROR")
    logger_module.reconfigure_logging()

    assert logger_module._global_log_level == logging.ERROR
    assert logger_module.logger.handlers[0].level == logging.ERROR
```

- [ ] **Step 2: 运行测试，确认先失败**

Run: `python -m pytest backend/tests/test_runtime_config.py -q`

Expected: 失败，原因是 `runtime_config.py` / `reconfigure_logging()` 还不存在。

- [ ] **Step 3: 实现运行期配置刷新服务**

```python
from pathlib import Path

from app.config import reload_settings, settings
from app.utils.logger import reconfigure_logging

HOT_RELOADABLE_ENV_KEYS = {
    "FORCE_HTTPS",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "MAX_FILE_SIZE",
    "RATE_LIMIT_REQUESTS",
    "LOG_LEVEL",
    "ALLOWED_FILE_TYPES",
    "CORS_ORIGINS",
}


def apply_runtime_settings(env_file: str | Path | None = None):
    updated = reload_settings(env_file=env_file)
    reconfigure_logging()
    return updated
```

- [ ] **Step 4: 在 logger 模块增加可重复调用的重配置入口**

```python
def reconfigure_logging() -> None:
    global _global_log_level, _log_dir
    _log_dir = _create_log_directory()
    _global_log_level = _get_log_level()

    for target in (logger, access_logger, error_logger, audit_logger):
        for handler in target.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(_get_formatter())

    for handler in logger.handlers:
        handler.setLevel(_global_log_level)
    for handler in access_logger.handlers:
        handler.setLevel(logging.INFO)
    for handler in error_logger.handlers:
        handler.setLevel(logging.ERROR)
    for handler in audit_logger.handlers:
        handler.setLevel(logging.INFO)
```

- [ ] **Step 5: 跑回测试确认通过**

Run: `python -m pytest backend/tests/test_runtime_config.py -q`

Expected: 新增 `runtime_config` 测试通过。

---

### Task 3: 设置接口只允许运行期配置，并在保存后立即生效

**Files:**
- Modify: `backend/app/routers/settings.py`
- Test: `backend/tests/test_settings_router.py`

- [ ] **Step 1: 写失败测试，覆盖禁止在线修改基础设施配置与即时热生效**

```python
def test_update_user_settings_rejects_storage_root_changes(client, auth_headers):
    response = client.put(
        "/api/v1/settings",
        headers=auth_headers,
        json={"storage_root": "./backend/data"},
    )

    assert response.status_code == 400
    assert "需要重启" in response.json()["message"]


def test_update_user_settings_applies_runtime_settings_immediately(client, auth_headers, monkeypatch):
    from app.config import settings

    response = client.put(
        "/api/v1/settings",
        headers=auth_headers,
        json={"log_level": "error"},
    )

    assert response.status_code == 200
    assert settings.LOG_LEVEL == "ERROR"
```

- [ ] **Step 2: 运行测试，确认先失败**

Run: `python -m pytest backend/tests/test_settings_router.py -q`

Expected: 失败，原因是当前接口不会拒绝基础设施配置，也没有显式运行期配置分类。

- [ ] **Step 3: 在设置路由中引入运行期配置白名单与基础设施黑名单**

```python
RUNTIME_SETTING_KEYS = {
    "force_https", "token_expire", "max_file_mb",
    "rate_upload", "log_level", "cors_origins",
    "cors_origins_str", "file_types",
}

RESTART_REQUIRED_KEYS = {
    "storage_root", "upload_dir", "log_dir", "temp_dir",
    "mobile_model_cache_dir", "database_url",
}
```

- [ ] **Step 4: 写入 `.env` 后改为调用运行期刷新服务**

```python
    forbidden = sorted(key for key in body.keys() if key in RESTART_REQUIRED_KEYS)
    if forbidden:
        raise ValidationError(
            message=f\"以下配置需要重启后生效，不支持在线修改: {', '.join(forbidden)}\"
        )

    env_body = {key: value for key, value in body.items() if key in RUNTIME_SETTING_KEYS}
    if env_body:
        _write_env(env_body)
        apply_runtime_settings(_env_abs_path())
```

- [ ] **Step 5: 更新成功消息，去掉“已保存到 .env 就等于热生效”的歧义**

```python
return success_response(
    data=body,
    message="运行期配置已写入 .env 并立即生效"
)
```

- [ ] **Step 6: 跑回测试确认通过**

Run: `python -m pytest backend/tests/test_settings_router.py -q`

Expected: 设置接口相关测试通过，包括拒绝基础设施配置和即时生效断言。

---

### Task 4: 将启动路径与关键目录使用切换到显式存储目录

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: 写失败测试，覆盖 `main.py` 不再依赖 `UPLOAD_DIR.parent`**

```python
def test_create_required_directories_uses_explicit_storage_dirs():
    from app.main import _create_required_directories
    from app.config import settings

    settings.UPLOAD_DIR = "/tmp/data/uploads"
    settings.LOG_DIR = "/tmp/data/logs"
    settings.TEMP_DIR = "/tmp/data/temp"
    settings.MOBILE_MODEL_CACHE_DIR = "/tmp/data/cache"

    _create_required_directories()
```

在现有 `test_main.py` 中补断言，要求创建目录列表直接包含 `settings.TEMP_DIR` / `settings.MOBILE_MODEL_CACHE_DIR`，而不是 `Path(settings.UPLOAD_DIR).parent / ...`。

- [ ] **Step 2: 运行测试，确认先失败**

Run: `python -m pytest backend/tests/test_main.py -q`

Expected: 失败，原因是 `main.py` 仍在用 `UPLOAD_DIR.parent / "temp"` 与 `UPLOAD_DIR.parent / "cache"`。

- [ ] **Step 3: 替换 main 中散落的隐式派生路径**

```python
directories = [
    settings.UPLOAD_DIR,
    settings.LOG_DIR,
    settings.TEMP_DIR,
    settings.MOBILE_MODEL_CACHE_DIR,
]

temp_dir = Path(settings.TEMP_DIR)
covers_dir = settings.covers_dir
avatars_dir = settings.avatars_dir
```

- [ ] **Step 4: 跑回主模块测试确认通过**

Run: `python -m pytest backend/tests/test_main.py -q`

Expected: `backend/tests/test_main.py` 通过，显式目录路径断言为绿。

---

### Task 5: 全量回归本次重构涉及区域

**Files:**
- Verify: `backend/tests/test_config.py`
- Verify: `backend/tests/test_runtime_config.py`
- Verify: `backend/tests/test_settings_router.py`
- Verify: `backend/tests/test_main.py`
- Verify: `backend/tests/test_tracking.py`
- Verify: `backend/tests/test_tracking_middleware.py`
- Verify: `test/test_tracking_ping.py`

- [ ] **Step 1: 运行后端聚合回归**

Run: `python -m pytest backend/tests/test_config.py backend/tests/test_runtime_config.py backend/tests/test_settings_router.py backend/tests/test_main.py backend/tests/test_tracking.py backend/tests/test_tracking_middleware.py test/test_tracking_ping.py -q`

Expected: 全部通过。

- [ ] **Step 2: 检查工作区变更，确认只包含本次预期文件**

Run: `git -C "C:\\Users\\lihuo\\Desktop\\docshop" diff -- backend/app/config.py backend/app/main.py backend/app/routers/settings.py backend/app/services/runtime_config.py backend/app/utils/logger.py backend/tests/test_config.py backend/tests/test_runtime_config.py backend/tests/test_settings_router.py backend/tests/test_main.py docs/superpowers/specs/2026-06-29-storage-root-and-runtime-config-design.md docs/superpowers/plans/2026-06-29-storage-root-and-runtime-config.md`

Expected: diff 仅展示本次实现与文档。
