import re
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.deps.auth import (
    get_current_user,
    get_current_admin,
    create_access_token,
    verify_password,
    get_password_hash,
)
from app.config import settings
from app.exceptions import AuthenticationError, ConflictError, ValidationError
from app.utils.response import success_response, error_response
from app.utils.logger import get_logger, log_audit
from app.services.security_settings import is_registration_enabled

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# 获取模块日志器
auth_logger = get_logger("routers.auth")

# 密码强度正则：至少8字符，包含字母和数字
_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")

# 登录暴力破解防护：内存失败计数器
_MAX_LOGIN_ATTEMPTS = 5       # 最大连续失败次数
_LOCKOUT_DURATION = 900        # 锁定时间（秒），默认 15 分钟
_login_failures: dict = defaultdict(lambda: {"count": 0, "locked_until": 0})


def _check_login_rate_limit(username: str) -> None:
    """
    检查登录失败频率限制

    同一用户名连续失败达到上限后，临时锁定。

    Args:
        username: 用户名

    Raises:
        AuthenticationError: 账户被临时锁定时抛出
    """
    now = time.time()
    entry = _login_failures[username]

    # 清理过期记录
    if entry["locked_until"] > 0 and now > entry["locked_until"]:
        entry["count"] = 0
        entry["locked_until"] = 0

    if entry["locked_until"] > 0 and now <= entry["locked_until"]:
        remaining = int(entry["locked_until"] - now)
        raise AuthenticationError(
            message=f"登录尝试过于频繁，请 {remaining} 秒后再试",
            auth_type="rate_limit",
        )


def _record_login_failure(username: str) -> None:
    """记录登录失败"""
    entry = _login_failures[username]
    entry["count"] += 1
    if entry["count"] >= _MAX_LOGIN_ATTEMPTS:
        entry["locked_until"] = time.time() + _LOCKOUT_DURATION
        auth_logger.warning(f"账户 {username} 已被临时锁定 {_LOCKOUT_DURATION}s（{_MAX_LOGIN_ATTEMPTS} 次失败）")


def _clear_login_failures(username: str) -> None:
    """登录成功后清除失败记录"""
    _login_failures.pop(username, None)


def _validate_password_strength(password: str) -> None:
    """
    验证密码强度

    要求：最少8字符，必须包含字母和数字。

    Args:
        password: 待验证的密码

    Raises:
        ValidationError: 密码不符合强度要求时抛出
    """
    if not _PASSWORD_PATTERN.match(password):
        raise ValidationError(
            message="密码强度不足：至少8个字符，且必须包含字母和数字",
            field="password",
        )


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 暴力破解防护：检查是否被锁定
    _check_login_rate_limit(request.username)

    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        _record_login_failure(request.username)
        raise AuthenticationError(
            message="用户名或密码错误",
            auth_type="password",
        )

    # 登录成功，清除失败记录
    _clear_login_failures(request.username)

    access_token = create_access_token(data={"sub": user.username, "role": user.role})

    # 审计日志
    log_audit(
        user_id=user.id,
        action="login",
        resource=f"user:{user.id}",
        result="success",
    )

    return success_response(
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        ).model_dump()
    )


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    if user_count > 0 and not is_registration_enabled():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is disabled")

    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise ConflictError(
            message="用户名已存在",
            conflict_type="username",
        )

    # 密码强度验证
    _validate_password_strength(request.password)

    # 判断角色：第一个注册用户为 admin，后续为 user
    # 使用排他行锁防止并发注册竞态（FOR UPDATE 在 PostgreSQL 有效；SQLite 降级）
    try:
        db.query(User).with_for_update().count()
    except Exception:
        pass  # SQLite 不支持 FOR UPDATE，接受极低概率的竞态
    user_count = db.query(User).count()
    role = "admin" if user_count == 0 else "user"

    user = User(
        username=request.username,
        password_hash=get_password_hash(request.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 审计日志
    log_audit(
        user_id=user.id,
        action="register",
        resource=f"user:{user.id}",
        result="success",
        details=f"role={role}",
    )

    return success_response(
        data=UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            created_at=user.created_at,
        ).model_dump()
    )


@router.get("/registration-policy")
def registration_policy(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    enabled = is_registration_enabled()
    return success_response(data={
        "enabled": enabled,
        "first_user": user_count == 0,
        "can_register": user_count == 0 or enabled,
    })


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse(
            id=current_user.id,
            username=current_user.username,
            role=current_user.role,
            avatar=getattr(current_user, "avatar_url", None) or "",
            created_at=current_user.created_at,
        ).model_dump()
    )
