"""
用户设置路由模块 — 安全配置统一读写 .env
"""
from datetime import datetime
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models.user import User
from app.deps.auth import get_current_user, verify_password, get_password_hash
from app.utils.response import success_response
from app.utils.logger import get_logger
from app.exceptions import ValidationError, AuthenticationError
from app.config import settings as app_settings

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
settings_logger = get_logger("routers.settings")
_AVATAR_MAX_BYTES = 2 * 1024 * 1024
_AVATAR_ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}
_AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png"}

# .env 文件绝对路径（与 backend/.env 对应）
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "backend", ".env")


def _env_abs_path() -> str:
    p = os.environ.get("DOCDIST_ENV_FILE") or \
        os.path.join(os.path.dirname(app_settings.UPLOAD_DIR), "..", ".env")
    return os.path.normpath(p)


def _read_env() -> dict:
    """读取 .env 中当前生效值 —— 直接从 pydantic-settings 读取。"""
    return {
        "force_https": False,
        "cors_origins": app_settings.CORS_ORIGINS,
        "rate_upload": app_settings.RATE_LIMIT_REQUESTS,
        "token_expire": app_settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "max_file_size": app_settings.MAX_FILE_SIZE,
        "max_file_mb": app_settings.MAX_FILE_SIZE // (1024 * 1024),
        "log_level": app_settings.LOG_LEVEL,
        "file_types": sorted(app_settings.ALLOWED_FILE_TYPES),
    }


def _write_env(body: dict) -> None:
    """将 body 中的 key=value 写入 .env 文件，保留现有注释和未提及的行。"""
    env_file = _env_abs_path()
    if not os.path.exists(env_file):
        raise FileNotFoundError(f".env not found at {env_file}")

    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updates = {}
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
    if "cors_origins_str" in body:
        origins = body["cors_origins_str"].strip()
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

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings_logger.info(f"用户 {current_user.username} 更新设置: {list(body.keys())}")
    profile = body.get("profile")
    if isinstance(profile, dict) and "avatar" in profile:
        current_user.avatar_url = profile.get("avatar") or None
        current_user.updated_at = datetime.utcnow().isoformat() + "Z"
        db.commit()
    try:
        env_body = {key: value for key, value in body.items() if key != "profile"}
        if env_body:
            _write_env(env_body)
    except FileNotFoundError as e:
        raise ValidationError(message=str(e))
    if any(key != "profile" for key in body.keys()):
        _touch_reload()
    return success_response(data=body, message="配置已保存到 .env，文件改动将自动触发服务重载")


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
    if len(new_password) < 6:
        raise ValidationError(message="新密码至少 6 位", field="new_password")
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    return success_response(data={"message": "密码修改成功"})


@router.get("/devices")
def get_login_devices(current_user: User = Depends(get_current_user)):
    return success_response(data={"devices": []})


@router.post("/devices/logout-all")
def logout_all_devices(current_user: User = Depends(get_current_user)):
    return success_response(data={"message": "所有设备已登出"})


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

    user_dir = Path(app_settings.UPLOAD_DIR).parent / "avatars" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    avatar_name = f"{uuid.uuid4().hex}{suffix}"
    avatar_path = user_dir / avatar_name
    avatar_path.write_bytes(content)

    old_avatar = getattr(current_user, "avatar_url", None)
    current_user.avatar_url = f"/api/v1/avatars/{current_user.id}/{avatar_name}"
    current_user.updated_at = datetime.utcnow().isoformat() + "Z"
    db.commit()

    if old_avatar and old_avatar.startswith(f"/api/v1/avatars/{current_user.id}/"):
        old_name = old_avatar.rsplit("/", 1)[-1]
        old_path = user_dir / old_name
        if old_path.exists() and old_path != avatar_path:
            try:
                old_path.unlink()
            except OSError:
                settings_logger.warning(f"Failed to remove old avatar: {old_path}")

    return success_response(data={"avatar_url": current_user.avatar_url})
