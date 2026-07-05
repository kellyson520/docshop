import os
import sys
import threading
from pathlib import Path

from app.config import Settings, settings


REGISTRATION_ENABLED_KEY = "REGISTRATION_ENABLED"
_env_write_lock = threading.Lock()


def _env_path() -> Path:
    override = os.environ.get("DOCSHOP_ENV_FILE")
    if override:
        return Path(override)
    return (Settings._project_root() / "backend" / ".env").resolve()


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def is_registration_enabled() -> bool:
    if "pytest" in sys.modules and os.environ.get(REGISTRATION_ENABLED_KEY) is not None:
        return _parse_bool(os.environ.get(REGISTRATION_ENABLED_KEY), default=True)

    env_file = _env_path()
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == REGISTRATION_ENABLED_KEY:
                return _parse_bool(value, default=False)
    return _parse_bool(os.environ.get(REGISTRATION_ENABLED_KEY), default=False)


def set_registration_enabled(enabled: bool) -> None:
    with _env_write_lock:
        env_file = _env_path()
        lines = env_file.read_text(encoding="utf-8").splitlines(keepends=True) if env_file.exists() else []
        updated = False
        new_lines: list[str] = []
        value = "true" if enabled else "false"

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key == REGISTRATION_ENABLED_KEY:
                    new_lines.append(f"{REGISTRATION_ENABLED_KEY}={value}\n")
                    updated = True
                    continue
            new_lines.append(line)

        if not updated:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            new_lines.append(f"{REGISTRATION_ENABLED_KEY}={value}\n")

        env_file.write_text("".join(new_lines), encoding="utf-8")
