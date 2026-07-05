from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import get_current_admin, get_password_hash
from app.models.resource_access_policy import ResourceAccessGroup, ResourceAccessPolicy
from app.models.user import User
from app.models.user_group import UserGroup, UserGroupMember
from app.utils.response import success_response
from app.utils.time import utc_now_iso

router = APIRouter(prefix="/api/v1/access-control", tags=["access-control"])

VALID_RESOURCE_TYPES = {"project", "file", "version"}
VALID_VISIBILITIES = {
    "inherit",
    "private",
    "login_required",
    "password_required",
    "groups_required",
    "public",
}


def _as_bool_flag(value, default: bool = True) -> int:
    if value is None:
        return 1 if default else 0
    return 1 if bool(value) else 0


def _group_payload(group: UserGroup, db: Session) -> dict:
    members = (
        db.query(UserGroupMember.user_id)
        .filter(UserGroupMember.group_id == group.id)
        .all()
    )
    member_ids = sorted({str(user_id) for (user_id,) in members if user_id})
    return {
        "id": group.id,
        "name": group.name,
        "code": group.code,
        "description": group.description,
        "is_active": bool(group.is_active),
        "member_user_ids": member_ids,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


def _policy_group_codes(db: Session, policy_id: str) -> list[str]:
    rows = (
        db.query(UserGroup.code)
        .join(ResourceAccessGroup, ResourceAccessGroup.group_id == UserGroup.id)
        .filter(ResourceAccessGroup.policy_id == policy_id)
        .order_by(UserGroup.code.asc())
        .all()
    )
    return [str(code) for (code,) in rows if code]


def _policy_payload(policy: ResourceAccessPolicy, db: Session) -> dict:
    allow_download_original = bool(policy.allow_download_original)
    allow_download_converted = bool(policy.allow_download_converted)
    return {
        "id": policy.id,
        "resource_type": policy.resource_type,
        "resource_id": policy.resource_id,
        "visibility": policy.visibility,
        "password_hint": policy.password_hint,
        "allow_preview": bool(policy.allow_preview),
        "allow_download": allow_download_original and allow_download_converted,
        "allow_download_original": allow_download_original,
        "allow_download_converted": allow_download_converted,
        "allow_diff": bool(policy.allow_diff),
        "allow_versions": bool(policy.allow_versions),
        "has_password": bool(policy.password_hash),
        "group_codes": _policy_group_codes(db, policy.id),
        "created_by": policy.created_by,
        "updated_by": policy.updated_by,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


def _resolve_groups_by_codes(db: Session, codes: list[str]) -> list[UserGroup]:
    normalized = []
    for code in codes:
        text = str(code or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    if not normalized:
        return []

    groups = (
        db.query(UserGroup)
        .filter(UserGroup.code.in_(normalized), UserGroup.is_active == 1)
        .all()
    )
    by_code = {group.code: group for group in groups}
    missing = [code for code in normalized if code not in by_code]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown group_codes: {', '.join(missing)}",
        )
    return [by_code[code] for code in normalized]


@router.get("/groups")
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    groups = db.query(UserGroup).order_by(UserGroup.code.asc()).all()
    return success_response(
        data={
            "items": [_group_payload(group, db) for group in groups],
        }
    )


@router.post("/groups")
def create_group(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    name = str(body.get("name") or "").strip()
    code = str(body.get("code") or "").strip().lower()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required")
    if not code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="code is required")

    group = UserGroup(
        name=name,
        code=code,
        description=str(body.get("description") or "").strip() or None,
        is_active=1 if body.get("is_active", True) else 0,
    )
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="group name or code already exists")
    db.refresh(group)
    return success_response(data=_group_payload(group, db))


@router.put("/groups/{group_id}/members")
def replace_group_members(
    group_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    group = db.query(UserGroup).filter(UserGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    user_ids = body.get("user_ids") or []
    if not isinstance(user_ids, list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_ids must be a list")

    normalized_user_ids = []
    for user_id in user_ids:
        text = str(user_id or "").strip()
        if text and text not in normalized_user_ids:
            normalized_user_ids.append(text)

    if normalized_user_ids:
        existing_users = db.query(User.id).filter(User.id.in_(normalized_user_ids)).all()
        found_ids = {str(user_id) for (user_id,) in existing_users if user_id}
        missing = [user_id for user_id in normalized_user_ids if user_id not in found_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"unknown user_ids: {', '.join(missing)}",
            )

    db.query(UserGroupMember).filter(UserGroupMember.group_id == group.id).delete(synchronize_session=False)
    for user_id in normalized_user_ids:
        db.add(UserGroupMember(group_id=group.id, user_id=user_id))
    group.updated_at = utc_now_iso()
    db.commit()
    db.refresh(group)
    return success_response(data=_group_payload(group, db))


@router.put("/policies/{resource_type}/{resource_id}")
def upsert_policy(
    resource_type: str,
    resource_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    normalized_type = str(resource_type or "").strip().lower()
    if normalized_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid resource_type")

    visibility = str(body.get("visibility") or "private").strip()
    if visibility not in VALID_VISIBILITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid visibility")

    group_codes = body.get("group_codes") or []
    if not isinstance(group_codes, list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="group_codes must be a list")
    groups = _resolve_groups_by_codes(db, group_codes)

    policy = (
        db.query(ResourceAccessPolicy)
        .filter(
            ResourceAccessPolicy.resource_type == normalized_type,
            ResourceAccessPolicy.resource_id == resource_id,
        )
        .first()
    )
    now = utc_now_iso()
    if not policy:
        policy = ResourceAccessPolicy(
            resource_type=normalized_type,
            resource_id=resource_id,
            created_by=current_user.id,
            updated_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(policy)
        db.flush()

    policy.visibility = visibility
    policy.password_hint = str(body.get("password_hint") or "").strip() or None
    policy.allow_preview = _as_bool_flag(body.get("allow_preview"), default=True)
    if "allow_download" in body:
        allow_download = _as_bool_flag(body.get("allow_download"), default=True)
        policy.allow_download_original = allow_download
        policy.allow_download_converted = allow_download
    else:
        policy.allow_download_original = _as_bool_flag(body.get("allow_download_original"), default=True)
        policy.allow_download_converted = _as_bool_flag(body.get("allow_download_converted"), default=True)
    policy.allow_diff = _as_bool_flag(body.get("allow_diff"), default=True)
    policy.allow_versions = _as_bool_flag(body.get("allow_versions"), default=True)
    password = str(body.get("password") or "")
    clear_password = bool(body.get("clear_password"))
    if password.strip():
        policy.password_hash = get_password_hash(password)
    elif clear_password:
        policy.password_hash = None
    policy.updated_by = current_user.id
    policy.updated_at = now

    db.query(ResourceAccessGroup).filter(ResourceAccessGroup.policy_id == policy.id).delete(synchronize_session=False)
    for group in groups:
        db.add(ResourceAccessGroup(policy_id=policy.id, group_id=group.id))

    db.commit()
    db.refresh(policy)
    return success_response(data=_policy_payload(policy, db))


@router.get("/policies/{resource_type}/{resource_id}")
def get_policy(
    resource_type: str,
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    normalized_type = str(resource_type or "").strip().lower()
    if normalized_type not in VALID_RESOURCE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid resource_type")

    policy = (
        db.query(ResourceAccessPolicy)
        .filter(
            ResourceAccessPolicy.resource_type == normalized_type,
            ResourceAccessPolicy.resource_id == resource_id,
        )
        .first()
    )
    if policy:
        return success_response(data=_policy_payload(policy, db))

    return success_response(
        data={
            "id": None,
            "resource_type": normalized_type,
            "resource_id": resource_id,
            "visibility": "private",
            "password_hint": None,
            "allow_preview": True,
            "allow_download": True,
            "allow_download_original": True,
            "allow_download_converted": True,
            "allow_diff": True,
            "allow_versions": True,
            "has_password": False,
            "group_codes": [],
            "created_by": None,
            "updated_by": None,
            "created_at": None,
            "updated_at": None,
        }
    )
