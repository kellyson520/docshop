
import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, List, Optional, Set

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **values: Any):
        if "pytest" in sys.modules and "_env_file" not in values:
            values["_env_file"] = None
        super().__init__(**values)

    ENVIRONMENT: str = Field(default="development", pattern="^(development|production|test)$")
    DEBUG: bool = False
    SECRET_KEY: str = Field(default="docshop-secret-key-change-me-32chars", min_length=16)

    STORAGE_ROOT: str = "./data"
    DATABASE_URL: str = "sqlite:///./data/docshop.db"
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DATABASE_POOL_RECYCLE: int = Field(default=3600, ge=300)

    UPLOAD_DIR: str = "./data/uploads"
    LOG_DIR: str = "./data/logs"
    TEMP_DIR: str = "./data/temp"

    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, ge=1024, le=500 * 1024 * 1024)
    ALLOWED_FILE_TYPES: Annotated[Set[str], NoDecode] = Field(
        default={".pdf", ".docx", ".xlsx", ".doc", ".xls"}
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, ge=5, le=10080)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)

    CORS_ORIGINS: Any = "*"
    FORCE_HTTPS: bool = False

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    RATE_LIMIT_WINDOW: int = Field(default=60, ge=1)
    AUTH_RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    AUTH_RATE_LIMIT_WINDOW: int = Field(default=60, ge=1)
    SHARE_UNLOCK_RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    SHARE_UNLOCK_RATE_LIMIT_WINDOW: int = Field(default=60, ge=1)
    PREVIEW_RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    PREVIEW_RATE_LIMIT_WINDOW: int = Field(default=60, ge=1)
    DOWNLOAD_RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1)
    DOWNLOAD_RATE_LIMIT_WINDOW: int = Field(default=60, ge=1)
    RATE_LIMIT_MAX_KEYS: int = Field(default=10000, ge=1)
    TRUSTED_PROXY_IPS: Any = "127.0.0.1,::1"

    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = Field(default="json", pattern="^(json|text)$")

    CACHE_ENABLED: bool = False
    CACHE_TTL: int = Field(default=300, ge=60)
    CACHE_MAX_SIZE: int = Field(default=1000, ge=1)

    MOBILE_MODEL_SYNC_ENABLED: bool = True
    MOBILE_MODEL_SYNC_INTERVAL_HOURS: int = Field(default=168, ge=1)
    MOBILE_MODEL_SOURCE_URL: str = "https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv"
    MOBILE_MODEL_CACHE_DIR: str = "./data/cache"
    MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS: int = Field(default=15, ge=1)
    MOBILE_MODEL_MAX_DOWNLOAD_BYTES: int = Field(default=20 * 1024 * 1024, ge=1024)

    FEATURE_FILE_PREVIEW: bool = True
    FEATURE_DIFF_EXPORT: bool = True
    FEATURE_SHARE_LINK: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def set_debug_by_environment(cls, v: bool, info: ValidationInfo) -> bool:
        if v is not None:
            return v
        return info.data.get("ENVIRONMENT", "production") == "development"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        env = info.data.get("ENVIRONMENT", "production")
        if env == "production" and len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        if v and "change-me" in v.lower():
            raise ValueError("SECRET_KEY must not contain 'change-me' placeholder")
        return v

    @classmethod
    def _project_root(cls) -> Path:
        return Path(__file__).resolve().parents[2]

    @classmethod
    def _resolve_project_path(cls, value: str | Path) -> str:
        raw = str(value).strip()
        if not raw:
            return raw
        if raw.startswith(("/", "\\")):
            return raw

        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = cls._project_root() / candidate
        return str(candidate.resolve(strict=False))

    @field_validator("STORAGE_ROOT", "UPLOAD_DIR", "LOG_DIR", "TEMP_DIR", "MOBILE_MODEL_CACHE_DIR")
    @classmethod
    def validate_directory_paths(cls, v: str) -> str:
        return cls._resolve_project_path(v)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        raw = str(v).strip()
        prefix = "sqlite:///"

        if not raw.lower().startswith(prefix):
            return raw

        location = raw[len(prefix):]
        if not location or location == ":memory:":
            return raw
        if raw.startswith("sqlite:////"):
            return raw
        if location.startswith(("/", "\\")):
            return raw
        if len(location) >= 2 and location[1] == ":":
            return raw

        path = cls._resolve_project_path(location)
        return f"sqlite:///{Path(path).as_posix()}"

    @model_validator(mode="after")
    def normalize_storage_layout(self):
        derived_dirs = {
            "UPLOAD_DIR": "uploads",
            "LOG_DIR": "logs",
            "TEMP_DIR": "temp",
            "MOBILE_MODEL_CACHE_DIR": "cache",
        }
        storage_root = Path(self.STORAGE_ROOT).resolve(strict=False)

        for field_name, child_name in derived_dirs.items():
            legacy_default = type(self)._resolve_project_path(f"./data/{child_name}")
            current_value = getattr(self, field_name)
            if current_value == legacy_default:
                setattr(self, field_name, str((storage_root / child_name).resolve(strict=False)))
        return self

    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def validate_allowed_file_types(cls, v) -> Set[str]:
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw)
                    v = parsed if isinstance(parsed, list) else [raw]
                except (json.JSONDecodeError, TypeError):
                    v = [raw]
            else:
                v = [ext.strip() for ext in raw.split(",") if ext.strip()]
        if isinstance(v, (list, tuple, set)):
            return {str(ext).lower() if str(ext).startswith(".") else f".{str(ext).lower()}" for ext in v}
        return set(v or [])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def validate_cors_origins(cls, v) -> List[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return ["*"]
        if isinstance(v, list):
            items = [str(x) for x in v if x]
            return items or ["*"]
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        items = [str(x) for x in parsed if x]
                        return items or ["*"]
                except (json.JSONDecodeError, TypeError):
                    pass
            origins = [item.strip().strip('"').strip("'") for item in raw.split(",") if item.strip()]
            return origins or ["*"]
        return ["*"]

    @field_validator("TRUSTED_PROXY_IPS", mode="before")
    @classmethod
    def validate_trusted_proxy_ips(cls, v) -> List[str]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return []
        if isinstance(v, list):
            candidates = v
        elif isinstance(v, str):
            raw = v.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw)
                    candidates = parsed if isinstance(parsed, list) else []
                except (json.JSONDecodeError, TypeError):
                    candidates = []
            else:
                candidates = [item.strip() for item in raw.split(",") if item.strip()]
        else:
            candidates = []

        import ipaddress
        normalized = []
        for item in candidates:
            try:
                normalized.append(str(ipaddress.ip_address(str(item).strip())))
            except ValueError:
                raise ValueError(f"Invalid trusted proxy IP: {item}")
        return normalized

    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    def is_test(self) -> bool:
        return self.ENVIRONMENT == "test"

    def _safe_child_path(self, base_dir: str, *paths: str) -> Path:
        base = Path(base_dir).resolve(strict=False)
        candidate = base.joinpath(*paths).resolve(strict=False)
        try:
            if not candidate.is_relative_to(base):
                raise ValueError(f"Path escapes base directory: {candidate}")
        except AttributeError:
            if os.path.commonpath([str(base), str(candidate)]) != str(base):
                raise ValueError(f"Path escapes base directory: {candidate}")
        return candidate

    def get_upload_path(self, *paths: str) -> Path:
        return self._safe_child_path(self.UPLOAD_DIR, *paths)

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

    def get_log_path(self, filename: str) -> Path:
        return Path(self.LOG_DIR) / filename

    def get_temp_path(self, filename: Optional[str] = None) -> Path:
        if filename:
            return self._safe_child_path(self.TEMP_DIR, filename)
        return self._safe_child_path(self.TEMP_DIR)

    def ensure_directories(self) -> None:
        for directory in [self.UPLOAD_DIR, self.LOG_DIR, self.TEMP_DIR, self.MOBILE_MODEL_CACHE_DIR]:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                import warnings
                warnings.warn(f"Unable to create directory {directory}: {exc}")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def reload_settings(env_file: Optional[str | Path] = None) -> Settings:
    global settings

    get_settings.cache_clear()
    new_settings = Settings(_env_file=str(env_file)) if env_file else Settings()

    current_settings = globals().get("settings")
    if current_settings is None:
        settings = new_settings
    else:
        for field_name in type(new_settings).model_fields:
            setattr(current_settings, field_name, getattr(new_settings, field_name))
        settings = current_settings

    settings.ensure_directories()
    return settings


settings = get_settings()


class DevelopmentSettings(Settings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440


class TestSettings(Settings):
    ENVIRONMENT: str = "test"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./data/test.db"
    UPLOAD_DIR: str = "./data/test_uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024


class ProductionSettings(Settings):
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RATE_LIMIT_ENABLED: bool = True
    CACHE_ENABLED: bool = True


def get_settings_by_environment(environment: Optional[str] = None) -> Settings:
    env = environment or os.getenv("ENVIRONMENT", "development")
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
        "test": TestSettings,
    }
    settings_class = settings_map.get(env, Settings)
    if env in settings_map:
        return settings_class(_env_file=None, ENVIRONMENT=env)
    return settings_class(_env_file=None)


def validate_settings() -> List[str]:
    warnings: List[str] = []

    if settings.is_production():
        if settings.DEBUG:
            warnings.append("Production should not enable DEBUG")
        if settings.SECRET_KEY.startswith("docshop-secret-key-change-me"):
            warnings.append("Production must use a custom SECRET_KEY")
        if "*" in settings.CORS_ORIGINS:
            warnings.append("Production should not allow all CORS origins")
        if settings.CORS_ORIGINS != ["*"] and "*" not in settings.CORS_ORIGINS:
            warnings.append("Production CORS should use explicit origins")
        if "sqlite" in settings.DATABASE_URL.lower():
            warnings.append("Production should use PostgreSQL or MySQL")

    for directory in [settings.UPLOAD_DIR, settings.LOG_DIR, settings.TEMP_DIR]:
        path = Path(directory)
        if path.exists() and not os.access(path, os.W_OK):
            warnings.append(f"Directory is not writable: {directory}")

    return warnings


if __name__ != "__main__":
    settings.ensure_directories()
    config_warnings = validate_settings()
    if config_warnings:
        import warnings as _warnings
        for warning in config_warnings:
            _warnings.warn(f"[Config Warning] {warning}")
