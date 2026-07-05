"""
访问令牌管理路由

管理员管理主页门禁令牌，主页验证令牌。
"""

import hashlib
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.access_token import AccessToken
from app.deps.auth import get_current_admin
from app.utils.response import success_response
from app.utils.logger import get_logger, log_audit

router = APIRouter(prefix="/api/v1/access-tokens", tags=["access-tokens"])
logger = get_logger("routers.access_tokens")

_LEGACY_VALIDATE_MAX_ATTEMPTS = 10
_LEGACY_VALIDATE_WINDOW_SECONDS = 60
_LEGACY_VALIDATE_CLEANUP_INTERVAL = 300
_legacy_validate_attempts: dict[str, list[float]] = {}
_last_validate_cleanup: float = 0.0


class ValidateTokenRequest(BaseModel):
    token: str


def _cleanup_validate_attempts() -> None:
    now = time.monotonic()
    cutoff = now - _LEGACY_VALIDATE_WINDOW_SECONDS * 2
    expired = [k for k, v in _legacy_validate_attempts.items() if not v or v[-1] < cutoff]
    for k in expired:
        del _legacy_validate_attempts[k]


def _validate_access_token(token: str, db: Session) -> dict:
    t = db.query(AccessToken).filter(AccessToken.token == token, AccessToken.is_active == 1).first()
    return success_response(data={"valid": t is not None})


def _legacy_validate_key(request: Request, token: str) -> str:
    client = request.client.host if request.client else "unknown"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"{client}:{token_hash}"


def _enforce_legacy_validate_rate_limit(request: Request, token: str) -> None:
    global _last_validate_cleanup
    now = time.monotonic()
    if now - _last_validate_cleanup > _LEGACY_VALIDATE_CLEANUP_INTERVAL:
        _last_validate_cleanup = now
        _cleanup_validate_attempts()
    window_start = now - _LEGACY_VALIDATE_WINDOW_SECONDS
    key = _legacy_validate_key(request, token)
    attempts = [
        ts for ts in _legacy_validate_attempts.get(key, [])
        if ts >= window_start
    ]

    if len(attempts) >= _LEGACY_VALIDATE_MAX_ATTEMPTS:
        _legacy_validate_attempts[key] = attempts
        raise HTTPException(status_code=429, detail="legacy token validation rate limit exceeded")

    attempts.append(now)
    _legacy_validate_attempts[key] = attempts


@router.get("/validate")
def validate_token_legacy(
    request: Request,
    response: Response,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """公开接口：验证访问令牌是否有效"""
    _enforce_legacy_validate_rate_limit(request, token)
    response.headers["Deprecation"] = "true"
    response.headers["Warning"] = '299 - "GET query token validation is deprecated; use POST body instead"'
    return _validate_access_token(token, db)


@router.post("/validate")
def validate_token(body: ValidateTokenRequest, db: Session = Depends(get_db)):
    """Public endpoint: validate an access token from the POST body."""
    return _validate_access_token(body.token, db)


@router.get("")
def list_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """管理员列表"""
    tokens = db.query(AccessToken).order_by(AccessToken.created_at.desc()).all()
    return success_response(data={"items": [t.to_dict(include_token=True) for t in tokens]})


@router.get("/{token_id}")
def get_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """管理员按 id 获取完整令牌，用于复制访问链接。"""
    t = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    return success_response(data=t.to_dict(include_token=True))


@router.post("")
def create_token(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """创建新令牌"""
    t = AccessToken(
        token=AccessToken.generate(),
        name=body.get("name", "未命名"),
        created_by=current_user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    log_audit(user_id=current_user.id, action="create_access_token", resource=f"token:{t.id}", result="success")
    return success_response(data=t.to_dict(include_token=True))


@router.put("/{token_id}")
def update_token(
    token_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """更新令牌（重命名/启禁用/重新生成）"""
    t = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    if "name" in body:
        name = body["name"]
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="name 必须为非空字符串")
        t.name = name.strip()
    if "is_active" in body:
        val = body["is_active"]
        if val not in (0, 1, True, False):
            raise HTTPException(status_code=400, detail="is_active 必须为 0 或 1")
        t.is_active = int(val)
    if body.get("regenerate"):
        t.token = AccessToken.generate()
    db.commit()
    db.refresh(t)
    return success_response(data=t.to_dict(include_token=bool(body.get("regenerate"))))


@router.delete("/{token_id}")
def delete_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除令牌"""
    t = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    db.delete(t)
    db.commit()
    log_audit(user_id=current_user.id, action="delete_access_token", resource=f"token:{token_id}", result="success")
    return None
