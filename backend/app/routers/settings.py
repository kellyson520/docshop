"""
用户设置路由模块 — 安全配置统一读写 .env
"""
from datetime import datetime
from pathlib import Path
import asyncio
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session
import os

from app.utils.time import utc_now, utc_now_iso
from app.database import get_db
from app.models.user import User
from app.deps.auth import get_current_user, get_current_admin, verify_password, get_password_hash
from app.utils.response import success_response
from app.utils.logger import get_logger
from app.exceptions import ValidationError, AuthenticationError
from app.config import reload_settings, settings as app_settings
from app.services.runtime_config import apply_runtime_settings
from app.services.event_bus import publish_config_updated
from app.utils.password_policy import validate_password_strength

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
settings_logger = get_logger("routers.settings")
_AVATAR_MAX_BYTES = 2 * 1024 * 1024
_AVATAR_ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}
_AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png"}

RUNTIME_SETTING_KEYS = {
    "force_https", "token_expire", "max_file_mb", "rate_upload", "log_level",
    "log_retention_days", "cors_origins_str", "cors_origins", "file_types",
}

RESTART_REQUIRED_KEYS = {
    "storage_root",
    "upload_dir",
    "log_dir",
    "temp_dir",
    "mobile_model_cache_dir",
    "database_url",
}

# .env 文件绝对路径（与 backend/.env 对应）
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "backend", ".env")


def _env_abs_path() -> str:
    """Return the mutable env file used by the running backend.

    In local development ``UPLOAD_DIR`` is commonly relative
    (``./data/uploads``).  The previous implementation derived ``.env`` from
    that path and then required the result to live inside ``./data``; this made
    the normal ``backend/.env`` path fail with ``ValueError`` and turned
    security-setting saves (for example LOG_LEVEL) into HTTP 500 responses.
    Resolve the env file from the backend application root instead, matching
    pydantic-settings' default ``env_file=".env"`` behavior while remaining
    independent of the current working directory.
    """
    backend_root = Path(__file__).resolve().parents[2]
    configured = os.environ.get("DOCSHOP_ENV_FILE")

    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = backend_root / candidate
    else:
        candidate = backend_root / ".env"

    return str(candidate.resolve(strict=False))


def _read_env() -> dict:
    """读取 .env 中当前生效值 —— 直接从 pydantic-settings 读取。"""
    env_path = _env_abs_path()
    snapshot = reload_settings(env_path) if Path(env_path).exists() else app_settings
    return {
        "force_https": bool(getattr(snapshot, "FORCE_HTTPS", False)),
        "cors_origins": snapshot.CORS_ORIGINS,
        "rate_upload": snapshot.RATE_LIMIT_REQUESTS,
        "token_expire": snapshot.ACCESS_TOKEN_EXPIRE_MINUTES,
        "max_file_size": snapshot.MAX_FILE_SIZE,
        "max_file_mb": snapshot.MAX_FILE_SIZE // (1024 * 1024),
        "log_level": snapshot.LOG_LEVEL,
        "file_types": sorted(snapshot.ALLOWED_FILE_TYPES),
    }


def _write_env(body: dict) -> None:
    """将 body 中的 key=value 写入 .env 文件，保留现有注释和未提及的行。"""
    env_path = Path(_env_abs_path())
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []

    updates = {}
    if "force_https" in body:
        updates["FORCE_HTTPS"] = str(bool(body["force_https"])).lower()
    if "token_expire" in body:
        updates["ACCESS_TOKEN_EXPIRE_MINUTES"] = str(int(body["token_expire"]))
    if "max_file_mb" in body:
        updates["MAX_FILE_SIZE"] = str(int(float(body["max_file_mb"]) * 1024 * 1024))
    if "rate_upload" in body:
        updates["RATE_LIMIT_REQUESTS"] = str(int(body["rate_upload"]))
    if "log_level" in body:
        updates["LOG_LEVEL"] = body["log_level"].upper()
    if "log_retention_days" in body:
        updates["LOG_RETENTION_DAYS"] = str(int(body["log_retention_days"]))
    if "cors_origins_str" in body or "cors_origins" in body:
        origins_value = body.get("cors_origins_str", body.get("cors_origins", ""))
        if isinstance(origins_value, list):
            origins = ",".join(str(p).strip() for p in origins_value if str(p).strip())
        else:
            origins = str(origins_value).strip()
        if origins == "*":
            updates["CORS_ORIGINS"] = origins
        else:
            parts = [p.strip() for p in origins.split(",") if p.strip()]
            updates["CORS_ORIGINS"] = json_dumps(parts)
    if "file_types" in body:
        types = body["file_types"]
        if isinstance(types, str):
            types = [t.strip() for t in types.split(",") if t.strip()]
        updates["ALLOWED_FILE_TYPES"] = ",".join(t if t.startswith(".") else f".{t}" for t in types)

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                val = updates.pop(key)
                new_lines.append(f"{key}={val}\n")
                continue
        new_lines.append(line)
    # 追加未匹配的新 key
    for key, val in updates.items():
        new_lines.append(f"{key}={val}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def _delayed_touch_reload(delay_seconds: float = 0.2) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    _touch_reload()


def _notify_config_updated(changed_keys: list[str], source: str = "settings-api") -> None:
    async def _publish() -> None:
        await publish_config_updated(changed_keys, source=source)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.run(_publish())
        except Exception as exc:
            settings_logger.warning(f"Failed to publish config update event: {exc}", exc_info=True)
    else:
        loop.create_task(_publish())


# ── 端点 ──

@router.get("")
def get_user_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sec = _read_env()
    return success_response(data={
        "profile": {"username": current_user.username, "avatar": getattr(current_user, "avatar_url", None) or ""},
        "notifications": {"email": True, "push": True},
        "appearance": {"theme": "light", "default_page_size": 20},
        "tracking": {"enabled": True, "ip_tracking": True, "device_tracking": True, "location_tracking": False},
        **sec,
    })


@router.put("")
def update_user_settings(
    body: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    settings_logger.info(f"用户 {current_user.username} 更新设置: {list(body.keys())}")
    forbidden = sorted(key for key in body.keys() if key in RESTART_REQUIRED_KEYS)
    if forbidden:
        raise ValidationError(
            message=f"以下配置需要重启后生效，不支持在线修改: {', '.join(forbidden)}"
        )

    profile = body.get("profile")
    if isinstance(profile, dict) and "avatar" in profile:
        current_user.avatar_url = profile.get("avatar") or None
        current_user.updated_at = utc_now_iso()
        db.commit()
    try:
        env_body = {key: value for key, value in body.items() if key in RUNTIME_SETTING_KEYS}
        if env_body:
            _write_env(env_body)
            apply_runtime_settings(_env_abs_path())
            _notify_config_updated(sorted(env_body.keys()), source="settings-api")
    except FileNotFoundError as e:
        raise ValidationError(message=str(e))
    message = "设置已保存"
    if env_body:
        message = "运行期配置已写入 .env 并立即生效"
    return success_response(data=body, message=message)


def _touch_reload() -> None:
    """修改 env 文件后 uvicorn --reload 自动检测重启。"""
    try:
        env_file = _env_abs_path()
        os.utime(env_file, None)
    except OSError:
        pass


@router.post("/change-password")
def change_password(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    if not old_password or not new_password:
        raise ValidationError(message="旧密码和新密码不能为空", field="password")
    if not verify_password(old_password, current_user.password_hash):
        raise AuthenticationError(message="旧密码不正确")
    validate_password_strength(new_password, field="new_password")
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    return success_response(data={"message": "密码修改成功"})


@router.get("/devices")
def get_login_devices(current_user: User = Depends(get_current_user)):
    return success_response(data={"devices": []})


@router.post("/devices/logout-all")
def logout_all_devices(current_user: User = Depends(get_current_user)):
    return success_response(data={"message": "所有设备已登出"})


_AVATAR_MAGIC_BYTES = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG",
}


def _validate_avatar_magic(content: bytes, suffix: str) -> bool:
    expected = _AVATAR_MAGIC_BYTES.get(suffix)
    if expected is None:
        return False
    return content[:len(expected)] == expected


@router.post("/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = avatar.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in _AVATAR_ALLOWED_EXTS:
        raise ValidationError(message="Only JPG and PNG avatars are supported", field="avatar")
    if avatar.content_type not in _AVATAR_ALLOWED_TYPES:
        raise ValidationError(message="Only JPG and PNG avatars are supported", field="avatar")

    content = await avatar.read()
    if not content:
        raise ValidationError(message="Avatar file is empty", field="avatar")
    if len(content) > _AVATAR_MAX_BYTES:
        raise ValidationError(message="Avatar must be smaller than 2MB", field="avatar")

    if not _validate_avatar_magic(content, suffix):
        raise ValidationError(message="File content does not match declared type", field="avatar")

    user_dir = app_settings.avatars_dir / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    avatar_name = f"{uuid.uuid4().hex}{suffix}"
    avatar_path = user_dir / avatar_name
    avatar_path.write_bytes(content)

    old_avatar = getattr(current_user, "avatar_url", None)
    current_user.avatar_url = f"/api/v1/avatars/{current_user.id}/{avatar_name}"
    current_user.updated_at = utc_now_iso()
    db.commit()

    if old_avatar and old_avatar.startswith(f"/api/v1/avatars/{current_user.id}/"):
        old_name = old_avatar.rsplit("/", 1)[-1]
        old_path = user_dir / old_name
        if old_path.exists() and old_path != avatar_path:
            try:
                resolved_old_path = old_path.resolve()
                resolved_user_dir = user_dir.resolve()
                if resolved_old_path == avatar_path.resolve() or resolved_old_path.is_relative_to(resolved_user_dir):
                    old_path.unlink()
                else:
                    settings_logger.warning(f"Skipping avatar cleanup outside allowed roots: {old_path}")
            except OSError:
                settings_logger.warning(f"Failed to remove old avatar: {old_path}")

    return success_response(data={"avatar_url": current_user.avatar_url})
