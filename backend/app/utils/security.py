"""
安全工具模块
- file_integrity_ok(): 验证文件 SHA-256 与预期值匹配
- log_security_event(): 安全事件审计日志
"""

import hashlib
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from jose import jwt

from app.config import settings


def file_sha256(path: str) -> str:
    """计算文件 SHA-256 哈希。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def file_integrity_ok(path: str, expected_hash: str) -> bool:
    """
    验证文件完整性：读取磁盘文件，与数据库记录的文件哈希比对。

    Returns:
        True 若哈希匹配，False 若文件不存在或哈希不一致。
    """
    if not os.path.exists(path):
        return False
    try:
        actual = file_sha256(path)
        return actual == expected_hash
    except OSError:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Kept here as a compatibility facade for tests and older modules; the auth
    dependency layer uses the same algorithm.
    """
    default_rounds = 4 if "pytest" in sys.modules else 12
    rounds = int(os.getenv("BCRYPT_ROUNDS", str(default_rounds)))
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=rounds),
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token with a revocation identifier."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def log_security_event(logger, event_type: str, resource: str, user_id: str = "unknown", **ctx):
    """
    记录安全相关事件到审计日志。

    Args:
        logger: 日志器实例
        event_type: "FILE_INTEGRITY_FAIL" | "UPLOAD_SIZE_EXCEED" | "RATE_LIMIT_HIT" | ...
        resource: 资源标识（file_id / project_id）
        user_id: 触发用户
        **ctx: 额外上下文
    """
    logger.warning(
        f"SECURITY | {event_type} | user={user_id} | resource={resource} | "
        + " ".join(f"{k}={v}" for k, v in ctx.items())
    )
