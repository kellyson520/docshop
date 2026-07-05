
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.time import utc_now, utc_now_iso
from app.database import get_db
from app.deps.auth import get_current_admin, get_current_user, get_password_hash
from app.models.share_token import ShareToken
from app.models.user import User
from app.services.share_token_service import (
    VALID_RESOURCE_TYPES,
    assert_policy_allows_creation,
    assert_resource_owner,
    get_or_create_share_policy,
)
from app.utils.logger import log_audit
from app.utils.response import success_response

router = APIRouter(prefix="/api/v1/share-tokens", tags=["share-tokens"])
CANONICAL_SHARE_POLICY_MODE = "override_with_token_policy"


def _now() -> str:
    return utc_now_iso()


def _normalize_positive_int(value, default=0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, number)


def _parse_expires_at(value, max_expiry_days: int = 0) -> str | None:
    if not value:
        return None
    text = str(value)
    try:
        expires = datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid expires_at")
    if max_expiry_days and expires > utc_now() + timedelta(days=max_expiry_days):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expires_at exceeds policy")
    return text


def _normalize_optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _apply_phase1_share_access_fields(token: ShareToken, body: dict, *, on_create: bool = False) -> None:
    if on_create or "require_login" in body:
        token.require_login = 1 if body.get("require_login") else 0
    if on_create or "allow_preview" in body:
        token.allow_preview = 1 if body.get("allow_preview", 1) else 0
    if on_create or "allow_diff" in body:
        token.allow_diff = 1 if body.get("allow_diff", 1) else 0
    if on_create or "allow_versions" in body:
        token.allow_versions = 1 if body.get("allow_versions", 1) else 0
    token.policy_mode = CANONICAL_SHARE_POLICY_MODE
    if on_create or "password_hint" in body:
        token.password_hint = _normalize_optional_text(body.get("password_hint"))
    if "password" in body:
        raw_password = str(body.get("password") or "")
        token.password_hash = get_password_hash(raw_password) if raw_password else None


def _share_token_payload(token: ShareToken, include_token: bool = False) -> dict:
    data = token.to_dict(include_token=include_token)
    data["share_url"] = f"/s/{token.token if include_token else token.token_preview()}"
    data["allow_download"] = bool(token.allow_download)
    data["is_active"] = int(token.is_active)
    return data


def _can_manage(token: ShareToken, user: User) -> bool:
    return user.role == "admin" or token.created_by == user.id


@router.get("/policy")
def get_policy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    policy = get_or_create_share_policy(db)
    return success_response(data=policy.to_dict())


@router.put("/policy")
def update_policy(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    policy = get_or_create_share_policy(db)

    if "enabled" in body:
        policy.enabled = 1 if body.get("enabled") else 0
    if "allow_anonymous_creation" in body:
        policy.allow_anonymous_creation = 1 if body.get("allow_anonymous_creation") else 0
    if "allow_user_creation" in body:
        policy.allow_user_creation = 1 if body.get("allow_user_creation") else 0
    if "allowed_resource_types" in body:
        types = body.get("allowed_resource_types") or []
        if not isinstance(types, list) or any(t not in VALID_RESOURCE_TYPES for t in types):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid allowed_resource_types")
        policy.allowed_resource_types = ",".join(types)
    if "default_max_views" in body:
        policy.default_max_views = _normalize_positive_int(body.get("default_max_views"))
    if "default_max_downloads" in body:
        policy.default_max_downloads = _normalize_positive_int(body.get("default_max_downloads"))
    if "default_allow_download" in body:
        policy.default_allow_download = 1 if body.get("default_allow_download") else 0
    if "max_expiry_days" in body:
        policy.max_expiry_days = _normalize_positive_int(body.get("max_expiry_days"))
    policy.updated_at = _now()
    db.commit()
    db.refresh(policy)
    return success_response(data=policy.to_dict())


@router.get("")
def list_share_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ShareToken)
    if current_user.role != "admin":
        query = query.filter(ShareToken.created_by == current_user.id)
    items = query.order_by(ShareToken.created_at.desc()).all()
    return success_response(data={"items": [_share_token_payload(t, include_token=True) for t in items]})


@router.post("")
def create_share_token(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = get_or_create_share_policy(db)
    resource_type = str(body.get("resource_type") or "project")
    resource_id = str(body.get("resource_id") or "")
    if resource_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid resource_type")
    if not resource_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="resource_id is required")

    assert_policy_allows_creation(policy, resource_type, current_user)
    assert_resource_owner(resource_type, resource_id, db, current_user)

    token = ShareToken(
        token=ShareToken.generate(),
        name=str(body.get("name") or "分享链接")[:120],
        resource_type=resource_type,
        resource_id=resource_id,
        is_active=1 if body.get("is_active", 1) else 0,
        allow_download=1 if body.get("allow_download", policy.default_allow_download) else 0,
        max_views=_normalize_positive_int(body.get("max_views"), policy.default_max_views),
        max_downloads=_normalize_positive_int(body.get("max_downloads"), policy.default_max_downloads),
        expires_at=_parse_expires_at(body.get("expires_at"), policy.max_expiry_days),
        created_by=current_user.id,
    )
    _apply_phase1_share_access_fields(token, body, on_create=True)
    db.add(token)
    db.commit()
    db.refresh(token)
    log_audit(user_id=current_user.id, action="create_share_token", resource=f"share_token:{token.id}", result="success")
    return success_response(data=_share_token_payload(token, include_token=True))


@router.put("/{token_id}")
def update_share_token(
    token_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = db.query(ShareToken).filter(ShareToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")
    if not _can_manage(token, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission")
    policy = get_or_create_share_policy(db)

    if "name" in body:
        token.name = str(body.get("name") or token.name)[:120]
    if "is_active" in body:
        token.is_active = 1 if body.get("is_active") else 0
    if "allow_download" in body:
        token.allow_download = 1 if body.get("allow_download") else 0
    if "max_views" in body:
        token.max_views = _normalize_positive_int(body.get("max_views"))
    if "max_downloads" in body:
        token.max_downloads = _normalize_positive_int(body.get("max_downloads"))
    if "expires_at" in body:
        token.expires_at = _parse_expires_at(body.get("expires_at"), policy.max_expiry_days)
    _apply_phase1_share_access_fields(token, body)
    token.updated_at = _now()
    db.commit()
    db.refresh(token)
    return success_response(data=_share_token_payload(token, include_token=False))


@router.post("/{token_id}/regenerate")
def regenerate_share_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = db.query(ShareToken).filter(ShareToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")
    if not _can_manage(token, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission")
    token.token = ShareToken.generate()
    token.view_count = 0
    token.download_count = 0
    token.updated_at = _now()
    db.commit()
    db.refresh(token)
    return success_response(data=_share_token_payload(token, include_token=True))


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_share_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = db.query(ShareToken).filter(ShareToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")
    if not _can_manage(token, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission")
    db.delete(token)
    db.commit()
    log_audit(user_id=current_user.id, action="delete_share_token", resource=f"share_token:{token_id}", result="success")
    return None
