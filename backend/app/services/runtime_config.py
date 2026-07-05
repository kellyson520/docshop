from pathlib import Path

from app.config import reload_settings
from app.utils.logger import reconfigure_logging


HOT_RELOADABLE_ENV_KEYS = {
    "FORCE_HTTPS",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "MAX_FILE_SIZE",
    "RATE_LIMIT_REQUESTS",
    "LOG_LEVEL",
    "LOG_RETENTION_DAYS",
    "CORS_ORIGINS",
    "ALLOWED_FILE_TYPES",
}

RESTART_REQUIRED_ENV_KEYS = {
    "STORAGE_ROOT",
    "UPLOAD_DIR",
    "LOG_DIR",
    "TEMP_DIR",
    "MOBILE_MODEL_CACHE_DIR",
    "DATABASE_URL",
}


def apply_runtime_settings(env_file: str | Path | None = None):
    updated_settings = reload_settings(env_file=env_file)
    reconfigure_logging()
    return updated_settings
