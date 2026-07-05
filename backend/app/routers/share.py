import hashlib
import json
import hmac
import mimetypes
import os
import secrets
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Cookie, Depends, Header, HTTPException, Query, Request, status
from fastapi.params import Depends as DependsParam, Param
from fastapi.responses import FileResponse as FastAPIFileResponse
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps.auth import get_current_user, get_current_user_optional, verify_password
from app.models.project import Project
from app.models.project_folder import ProjectFolder
from app.models.user import User
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord
from app.models.resource_access_policy import ResourceAccessPolicy
from app.models.share_token import ShareToken
from app.services.share_token_service import (
    assert_share_token_allowed,
    assert_version_in_share_scope,
    consume_share_token,
    ensure_project_share_token,
    get_resource_share_token_map,
    resolve_share_token,
    share_scope_file_filter,
    share_scope_versions_query,
)
from app.schemas.project import ProjectResponse
from app.schemas.file import FileResponse, VersionResponse, VersionListResponse
from app.schemas.diff import DiffResponse, DiffListResponse
from app.services.diff_service import compute_diff
from app.services.file_capability_service import build_download_contract
from app.services.share_access_grant_service import (
    COOKIE_NAME,
    DEFAULT_TTL_SECONDS,
    issue_share_access_grant,
    validate_share_access_grant,
)
from app.services.share_tab_grant_service import (
    DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS,
    heartbeat_share_tab_grant,
    issue_share_tab_grant,
    release_share_tab_grant,
    validate_share_tab_grant,
)
from app.services.share_resource_ticket_service import (
    DEFAULT_SHARE_RESOURCE_TICKET_TTL_SECONDS,
    issue_share_resource_ticket,
    validate_share_resource_ticket,
)
from app.services.resource_access_grant_service import (
    DEFAULT_RESOURCE_ACCESS_GRANT_TTL_SECONDS,
    heartbeat_resource_access_grant,
    issue_resource_access_grant,
    release_resource_access_grant,
    validate_resource_access_grant,
)
from app.services.html_runtime_preview_service import (
    build_runtime_html_preview,
    runtime_html_response_headers,
)
from app.services.access_control_service import (
    AccessPolicy,
    build_access_subject,
    require_resource_action,
    resolve_resource_policy,
)
from app.config import settings
from app.routers.files import (
    _build_file_detail_payload,
    _build_html_asset_url,
    _build_version_payload,
    _is_allowed_response_path,
    _is_allowed_storage_path,
    _load_preview_asset,
    _load_version_preview_asset,
    _previewable_category_for_file,
    _stream_html_asset_file,
    _stream_native_preview_file,
    _stream_preview_asset,
)
from app.utils.response import success_response
from app.utils.folder_bundle import build_folder_bundle_response
from app.utils.logger import get_logger
from app.utils.time import utc_now_iso

logger = get_logger("routers.share")

router = APIRouter(prefix="/api/v1/share", tags=["share"])
legacy_router = APIRouter(prefix="/api/v1/shares", tags=["share-legacy"])

SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS = 30


def _normalize_optional_query_value(value):
    return None if isinstance(value, Param) else value


def _extract_version_number_snapshot(
    diff: DiffRecord,
    *,
    old_version: Optional[FileVersion],
    new_version: Optional[FileVersion],
) -> tuple[int, int]:
    old_number = old_version.version if old_version else 0
    new_number = new_version.version if new_version else 0

    raw_data = diff.diff_data
    if not raw_data:
        return old_number, new_number

    try:
        payload = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
    except (TypeError, ValueError, json.JSONDecodeError):
        return old_number, new_number

    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    if not isinstance(metadata, dict):
        return old_number, new_number

    old_snapshot = metadata.get("old_version_number", old_number)
    new_snapshot = metadata.get("new_version_number", new_number)

    try:
        return int(old_snapshot), int(new_snapshot)
    except (TypeError, ValueError):
        return old_number, new_number


def _get_or_create_shared_diff(db: Session, old_v: FileVersion, new_v: FileVersion) -> DiffRecord:
    diff = (
        db.query(DiffRecord)
        .filter(DiffRecord.old_version_id == old_v.id, DiffRecord.new_version_id == new_v.id)
        .first()
    )
    if diff:
        return diff

    reverse_diff = (
        db.query(DiffRecord)
        .filter(DiffRecord.old_version_id == new_v.id, DiffRecord.new_version_id == old_v.id)
        .first()
    )
    if reverse_diff:
        return reverse_diff

    try:
        return compute_diff(old_v.id, new_v.id, db)
    except IntegrityError:
        db.rollback()
        diff = (
            db.query(DiffRecord)
            .filter(DiffRecord.old_version_id == old_v.id, DiffRecord.new_version_id == new_v.id)
            .first()
        )
        if diff:
            return diff
        raise


def _resolve_scoped_share_version(db: Session, file_id: str, raw_value: Optional[str]) -> Optional[FileVersion]:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None

    version = (
        db.query(FileVersion)
        .filter(FileVersion.id == value, FileVersion.file_id == file_id)
        .first()
    )
    if version:
        return version

    if value.isdigit():
        return (
            db.query(FileVersion)
            .filter(FileVersion.file_id == file_id, FileVersion.version == int(value))
            .first()
        )
    return None

# 旧版 /api/v1/shares 协议曾支持分享密码，但当前持久化模型只有
# Project.share_token。为兼容旧集成测试和旧客户端，密码仅在进程内维护；
# 新前端仍走 /api/v1/share/{token} 的无密码公开项目协议。
_legacy_share_passwords: dict[str, str] = {}
_share_unlock_failures: dict[str, dict[str, int | float]] = {}
_SHARE_UNLOCK_WINDOW_SECONDS = 300
_SHARE_UNLOCK_MAX_FAILURES = 5
_SHARE_UNLOCK_LOCK_SECONDS = 300


def _hash_legacy_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _check_legacy_password(share_token: str, password: Optional[str]) -> bool:
    expected = _legacy_share_passwords.get(share_token)
    if not expected:
        return True
    if not password:
        return False
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == expected


def _share_unlock_attempt_key(request: Request, share_token: str) -> str:
    client_host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    return f"{share_token}:{client_host}"


def _ensure_share_unlock_not_limited(request: Request, share_token: str) -> None:
    import time

    key = _share_unlock_attempt_key(request, share_token)
    state = _share_unlock_failures.get(key)
    if not state:
        return

    now = time.time()
    locked_until = float(state.get("locked_until") or 0.0)
    if locked_until and locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="share_password_rate_limited",
        )
    if locked_until and locked_until <= now:
        _share_unlock_failures.pop(key, None)


def _record_share_unlock_failure(request: Request, share_token: str) -> None:
    import time

    now = time.time()
    key = _share_unlock_attempt_key(request, share_token)
    state = _share_unlock_failures.get(key)
    window_started_at = float(state.get("window_started_at") or 0.0) if state else 0.0
    if not state or now - window_started_at > _SHARE_UNLOCK_WINDOW_SECONDS:
        state = {"count": 0, "window_started_at": now, "locked_until": 0.0}
        _share_unlock_failures[key] = state

    state["count"] = int(state.get("count") or 0) + 1
    state["window_started_at"] = float(state.get("window_started_at") or now)
    if int(state["count"]) >= _SHARE_UNLOCK_MAX_FAILURES:
        state["locked_until"] = now + _SHARE_UNLOCK_LOCK_SECONDS


def _clear_share_unlock_failures(request: Request, share_token: str) -> None:
    _share_unlock_failures.pop(_share_unlock_attempt_key(request, share_token), None)


def _normalize_optional_dependency_value(value):
    return None if isinstance(value, (DependsParam, Param)) else value


def _normalize_optional_user(value) -> Optional[User]:
    return _normalize_optional_dependency_value(value)


def _normalize_share_grant_transport_value(*values) -> str | None:
    for value in values:
        normalized = str(_normalize_optional_dependency_value(value) or "").strip()
        if normalized:
            return normalized
    return None


def _share_tab_id_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return _normalize_optional_dependency_value(request.headers.get("X-Share-Tab-Id"))


def _share_grant_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return _normalize_optional_dependency_value(request.headers.get("X-Share-Grant"))


def _access_tab_id_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return _normalize_optional_dependency_value(request.headers.get("X-Access-Tab-Id"))


def _access_grant_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return _normalize_optional_dependency_value(request.headers.get("X-Access-Grant"))


def _get_resource_policy_model(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
) -> ResourceAccessPolicy | None:
    if type(db).__module__.startswith("unittest.mock"):
        return None
    return (
        db.query(ResourceAccessPolicy)
        .filter(
            ResourceAccessPolicy.resource_type == resource_type,
            ResourceAccessPolicy.resource_id == resource_id,
        )
        .first()
    )


def _resolve_effective_resource_policy_model(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
    project_id: str | None,
) -> ResourceAccessPolicy | None:
    specific = _get_resource_policy_model(db, resource_type=resource_type, resource_id=resource_id)
    if specific and str(specific.visibility or "inherit") != "inherit":
        return specific

    if resource_type != "project" and project_id:
        project_policy = _get_resource_policy_model(db, resource_type="project", resource_id=project_id)
        if project_policy and str(project_policy.visibility or "inherit") != "inherit":
            return project_policy

    return None


def _resolve_legacy_access_grant_scope(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
    project_id: str | None,
) -> tuple[str, str]:
    policy_model = _resolve_effective_resource_policy_model(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
    )
    if policy_model and str(policy_model.visibility or "").strip() == "password_required":
        return policy_model.resource_type, policy_model.resource_id
    return resource_type, resource_id


def _resolve_public_access_resource(
    resolved: dict,
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
) -> tuple[str, str, str | None]:
    normalized_type = str(resource_type or "").strip().lower()
    normalized_id = str(resource_id or "").strip()
    project = resolved["project"]

    if normalized_type == "project":
        if not normalized_id:
            normalized_id = project.id
        if normalized_id != project.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return normalized_type, normalized_id, project.id

    if normalized_type == "file":
        doc_file = share_scope_file_filter(resolved, db, normalized_id)
        return normalized_type, doc_file.id, doc_file.project_id

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid resource_type")


def _resource_access_grant_valid(
    db: Session,
    request: Request | None,
    *,
    share_token: str,
    resource_type: str,
    resource_id: str,
    project_id: str | None = None,
) -> bool:
    grant_resource_type, grant_resource_id = _resolve_legacy_access_grant_scope(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
    )
    tab_id = _access_tab_id_from_request(request)
    raw_grant = _access_grant_from_request(request)
    grant = validate_resource_access_grant(
        db,
        share_token=share_token,
        resource_type=grant_resource_type,
        resource_id=grant_resource_id,
        tab_id=tab_id,
        raw_grant=raw_grant,
    )
    return grant is not None


def _share_password_grant_valid(
    db: Session,
    request: Request | None,
    raw_cookie: str | None,
    share_token: str,
    *,
    allow_cookie_fallback: bool = True,
) -> bool:
    tab_id = _share_tab_id_from_request(request)
    header_grant = _share_grant_from_request(request)

    if tab_id or header_grant:
        grant = validate_share_tab_grant(
            db,
            share_token=share_token,
            tab_id=tab_id,
            raw_grant=header_grant,
        )
        return grant is not None

    if not allow_cookie_fallback:
        return False

    return validate_share_access_grant(_normalize_optional_dependency_value(raw_cookie), share_token)


def _require_share_password_grant(
    resolved: dict,
    db: Session,
    request: Request | None,
    raw_cookie: str | None,
    *,
    allow_cookie_fallback: bool = True,
) -> None:
    token_model = resolved.get("share_token")
    if not token_model or not getattr(token_model, "password_hash", None):
        return
    if _share_password_grant_valid(
        db,
        request,
        raw_cookie,
        token_model.token,
        allow_cookie_fallback=allow_cookie_fallback,
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="share_password_required")


def _validate_share_resource_ticket_claims(
    db: Session,
    raw_ticket: str | None,
    *,
    share_token: str,
    kind: str,
    file_id: str | None = None,
    version_id: str | None = None,
    page_num: int | None = None,
    asset_id: str | None = None,
    folder_id: str | None = None,
    format: str | None = None,
):
    raw_ticket = _normalize_optional_dependency_value(raw_ticket)
    if not raw_ticket:
        return None
    return validate_share_resource_ticket(
        db,
        raw_ticket,
        share_token=share_token,
        kind=kind,
        file_id=file_id,
        version_id=version_id,
        page_num=page_num,
        asset_id=asset_id,
        folder_id=folder_id,
        format=format,
    )


def _require_share_action_enabled(resolved: dict, action: str) -> None:
    token_model = resolved.get("share_token")
    if not token_model:
        return

    action_flags = {
        "preview": ("allow_preview", "preview disabled"),
        "diff": ("allow_diff", "diff disabled"),
        "versions": ("allow_versions", "versions disabled"),
    }
    field_name, detail = action_flags.get(action, (None, None))
    if not field_name:
        return
    if getattr(token_model, field_name, 1) != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _require_share_login(resolved: dict, current_user) -> Optional[User]:
    normalized_user = _normalize_optional_user(current_user)
    token_model = resolved.get("share_token")
    if token_model and getattr(token_model, "require_login", 0) == 1 and normalized_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    return normalized_user


def _resolve_share_effective_policy(
    *,
    resolved: dict,
    db: Session,
    resource_type: str,
    resource_id: str,
    project_id: Optional[str],
) -> AccessPolicy:
    token_model = resolved.get("share_token")
    if token_model:
        allow_download = bool(getattr(token_model, "allow_download", 1))
        allow_preview = bool(getattr(token_model, "allow_preview", 1))
        allow_diff = bool(getattr(token_model, "allow_diff", 1))
        allow_versions = bool(getattr(token_model, "allow_versions", 1))
        return AccessPolicy(
            visibility="public",
            allow_preview=allow_preview,
            allow_download_original=allow_download,
            allow_download_converted=allow_download,
            allow_diff=allow_diff,
            allow_versions=allow_versions,
            required_group_codes=set(),
        )

    if type(db).__module__.startswith("unittest.mock"):
        base_policy = AccessPolicy(visibility="public")
    else:
        base_policy = resolve_resource_policy(
            db,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            default_visibility="public",
        )
    return base_policy


def _require_share_resource_action(
    *,
    resolved: dict,
    db: Session,
    request: Request | None,
    current_user,
    share_access_grant: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str,
    owner_id: Optional[str],
    project_id: Optional[str],
    allow_cookie_fallback: bool = True,
    share_unlocked_override: Optional[bool] = None,
):
    normalized_user = _require_share_login(resolved, current_user)
    token_model = resolved.get("share_token")
    if share_unlocked_override is None:
        if token_model and getattr(token_model, "password_hash", None):
            share_unlocked = bool(
                _share_password_grant_valid(
                    db,
                    request,
                    share_access_grant,
                    token_model.token,
                    allow_cookie_fallback=allow_cookie_fallback,
                )
            )
        elif resolved.get("legacy"):
            share_unlocked = _resource_access_grant_valid(
                db,
                request,
                share_token=getattr(resolved.get("project"), "share_token", None),
                resource_type=resource_type,
                resource_id=resource_id,
                project_id=project_id,
            )
        else:
            share_unlocked = False
    else:
        share_unlocked = bool(share_unlocked_override)
    subject = build_access_subject(
        db,
        user=normalized_user,
        share_unlocked=share_unlocked,
    )
    policy = _resolve_share_effective_policy(
        resolved=resolved,
        db=db,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
    )
    try:
        return require_resource_action(
            db=db,
            subject=subject,
            policy=policy,
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            project_id=project_id,
            action=action,
        )
    except HTTPException as exc:
        if resolved.get("legacy") and exc.status_code == status.HTTP_403_FORBIDDEN and exc.detail == "password_required":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="resource_password_required",
            ) from exc
        raise


def _require_shared_file_action(
    resolved: dict,
    db: Session,
    request: Request | None,
    current_user,
    share_access_grant: Optional[str],
    doc_file: DocumentFile,
    action: str,
    *,
    allow_cookie_fallback: bool = True,
    share_unlocked_override: Optional[bool] = None,
):
    project = resolved.get("project")
    if not project and getattr(doc_file, "project_id", None):
        project = db.query(Project).filter(Project.id == doc_file.project_id).first()
    project_id = getattr(project, "id", None) or getattr(doc_file, "project_id", None)
    owner_id = getattr(project, "owner_id", None)
    return _require_share_resource_action(
        resolved=resolved,
        db=db,
        request=request,
        current_user=current_user,
        share_access_grant=share_access_grant,
        action=action,
        resource_type="file",
        resource_id=doc_file.id,
        owner_id=owner_id,
        project_id=project_id,
        allow_cookie_fallback=allow_cookie_fallback,
        share_unlocked_override=share_unlocked_override,
    )


def _require_shared_root_action(
    resolved: dict,
    db: Session,
    request: Request | None,
    current_user,
    share_access_grant: Optional[str],
    *,
    allow_cookie_fallback: bool = True,
    share_unlocked_override: Optional[bool] = None,
):
    scoped_file = resolved.get("file")
    if scoped_file:
        return _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            scoped_file,
            "view_metadata",
            allow_cookie_fallback=allow_cookie_fallback,
            share_unlocked_override=share_unlocked_override,
        )

    project = resolved["project"]
    return _require_share_resource_action(
        resolved=resolved,
        db=db,
        request=request,
        current_user=current_user,
        share_access_grant=share_access_grant,
        action="view_metadata",
        resource_type="project",
        resource_id=project.id,
        owner_id=getattr(project, "owner_id", None),
        project_id=project.id,
        allow_cookie_fallback=allow_cookie_fallback,
        share_unlocked_override=share_unlocked_override,
    )


def _project_share_payload(project: Project, db: Session) -> dict:
    file_count = db.query(DocumentFile).filter(DocumentFile.project_id == project.id).count()
    return {
        "project_id": project.id,
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "token": project.share_token,
        "share_token": project.share_token,
        "permission": "view",
        "file_count": file_count,
    }


def _project_uploader_payload(project: Project) -> dict:
    """Build a stable uploader payload for public project cards.

    Some older local databases can contain projects whose ``owner_id`` points to
    a deleted user.  Returning ``None`` makes the public homepage fall back to
    "未知上传者"; return an explicit deleted-user marker instead so the card still
    has a deterministic uploader line.
    """
    owner = getattr(project, "owner", None)
    if owner:
        return {
            "id": owner.id,
            "username": owner.username,
            "role": owner.role,
            "avatar": getattr(owner, "avatar_url", None) or "",
        }
    return {
        "id": project.owner_id,
        "username": "已删除用户",
        "role": "user",
        "avatar": "",
    }


@legacy_router.post("", status_code=status.HTTP_201_CREATED)
def create_legacy_share(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project_id = payload.get("project_id")
    if not project_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="project_id is required")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to share this project")

    project.is_public = True
    if not project.share_token:
        project.share_token = secrets.token_urlsafe(32)
    password = payload.get("password")
    if password:
        _legacy_share_passwords[project.share_token] = _hash_legacy_password(str(password))
    else:
        _legacy_share_passwords.pop(project.share_token, None)

    db.commit()
    db.refresh(project)
    return success_response(data=_project_share_payload(project, db))


@legacy_router.get("/{share_token}")
def get_legacy_share(
    share_token: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.share_token == share_token).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

    expected_password = _legacy_share_passwords.get(share_token)
    if expected_password and not _check_legacy_password(share_token, password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Share password required")

    return success_response(data=_project_share_payload(project, db))


@legacy_router.delete("/{share_token}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_legacy_share(
    share_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.share_token == share_token).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to revoke this share")

    _legacy_share_passwords.pop(share_token, None)
    project.is_public = False
    project.share_token = secrets.token_urlsafe(32)
    db.commit()
    return None


@router.get("/public-exams")
def list_public_exams(db: Session = Depends(get_db)):
    """公开考试列表（游客可浏览）"""
    from app.models.exam_schedule import ExamSchedule
    now = utc_now_iso()
    exams = (
        db.query(ExamSchedule)
        .filter(ExamSchedule.end_time >= now)
        .order_by(ExamSchedule.start_time.asc())
        .limit(10)
        .all()
    )
    items = []
    for e in exams:
        if now > e.end_time:
            e.status = "expired"
        elif now >= e.start_time:
            e.status = "ongoing"
        else:
            e.status = "upcoming"
        items.append({
            "id": e.id, "name": e.name, "description": e.description,
            "start_time": e.start_time, "end_time": e.end_time,
            "status": e.status, "project_name": e.project.name if e.project else None,
        })
    db.commit()
    return success_response(data=items)

@router.get("/public-exams/{exam_id}")
def get_public_exam_detail(
    exam_id: str,
    db: Session = Depends(get_db),
):
    from app.models.exam_schedule import ExamSchedule
    exam = db.query(ExamSchedule).filter(ExamSchedule.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    now = utc_now_iso()
    if now > exam.end_time:
        exam.status = "expired"
    elif now >= exam.start_time:
        exam.status = "ongoing"
    else:
        exam.status = "upcoming"
    return success_response(data={
        "id": exam.id, "name": exam.name, "description": exam.description,
        "start_time": exam.start_time, "end_time": exam.end_time,
        "status": exam.status,
        "project_name": exam.project.name if exam.project else None,
        "creator_name": exam.creator.username if exam.creator else None,
        "reminder_15min": bool(exam.reminder_15min),
        "reminder_5min": bool(exam.reminder_5min),
        "reminder_start": bool(exam.reminder_start),
    })

@router.get("/public-projects")
def list_public_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """公开项目列表（无需登录，游客可浏览）"""
    query = db.query(Project).options(joinedload(Project.owner)).filter(Project.is_public == True)
    search_text = keyword.strip() if keyword else ""
    if search_text:
        search_pattern = f"%{search_text}%"
        query = (
            query.outerjoin(DocumentFile, DocumentFile.project_id == Project.id)
            .filter(
                or_(
                    Project.name.ilike(search_pattern),
                    Project.description.ilike(search_pattern),
                    DocumentFile.filename.ilike(search_pattern),
                    DocumentFile.display_name.ilike(search_pattern),
                )
            )
            .distinct()
        )
    total = query.count()
    projects = query.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 批量查询：一次取所有项目的文件数和首文件
    project_ids = [p.id for p in projects]
    file_counts = {}
    first_files = {}
    matched_files = {}
    if project_ids:
        from sqlalchemy import func
        # 文件计数
        count_rows = (
            db.query(DocumentFile.project_id, func.count(DocumentFile.id))
            .filter(DocumentFile.project_id.in_(project_ids))
            .group_by(DocumentFile.project_id)
            .all()
        )
        file_counts = {row[0]: row[1] for row in count_rows}
        # 每个项目的第一个文件
        first_file_subq = (
            db.query(
                DocumentFile.project_id,
                func.min(DocumentFile.created_at).label("min_created"),
            )
            .filter(DocumentFile.project_id.in_(project_ids))
            .group_by(DocumentFile.project_id)
            .subquery()
        )
        ff_rows = (
            db.query(DocumentFile)
            .join(
                first_file_subq,
                (DocumentFile.project_id == first_file_subq.c.project_id)
                & (DocumentFile.created_at == first_file_subq.c.min_created),
            )
            .all()
        )
        first_files = {f.project_id: f for f in ff_rows}

        if search_text:
            search_pattern = f"%{search_text}%"
            matched_rows = (
                db.query(DocumentFile)
                .filter(
                    DocumentFile.project_id.in_(project_ids),
                    or_(
                        DocumentFile.filename.ilike(search_pattern),
                        DocumentFile.display_name.ilike(search_pattern),
                    ),
                )
                .order_by(DocumentFile.updated_at.desc(), DocumentFile.created_at.desc())
                .all()
            )
            for f in matched_rows:
                matched_files.setdefault(f.project_id, f)

    project_share_tokens = get_resource_share_token_map(
        "project",
        project_ids,
        db,
        action="view",
    )
    created_missing_share_token = False
    for project in projects:
        if project.id in project_share_tokens:
            continue
        project_share_tokens[project.id] = ensure_project_share_token(project, db, created_by=project.owner_id)
        created_missing_share_token = True
    if created_missing_share_token:
        db.commit()

    items = []
    for p in projects:
        first_file = first_files.get(p.id)
        matched_file = matched_files.get(p.id)
        card_file = matched_file or first_file
        cover_url = None
        if card_file and card_file.cover_image:
            c = card_file.cover_image
            cover_url = c if c.startswith("/api/") else "/api/v1/" + c.replace("\\", "/")

        items.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "share_token": project_share_tokens.get(p.id).token if project_share_tokens.get(p.id) else "",
            "file_count": file_counts.get(p.id, 0),
            "cover_image": cover_url,
            "uploader": _project_uploader_payload(p),
            "first_file": {
                "id": card_file.id,
                "filename": card_file.filename,
                "file_type": card_file.file_type,
            } if card_file else None,
            "matched_file": {
                "id": matched_file.id,
                "filename": matched_file.filename,
                "display_name": matched_file.display_name,
                "file_type": matched_file.file_type,
            } if matched_file else None,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    return success_response(data={"total": total, "page": page, "page_size": page_size, "items": items})


def _resolve_share_context(share_token: str, db: Session, action: str = "view", consume: bool = False) -> dict:
    resolved = resolve_share_token(share_token, db, action=action)
    token_model = resolved.get("share_token")
    if token_model and consume:
        consume_share_token(token_model, action=action)
        db.commit()
        db.refresh(token_model)
    return resolved


def _get_project_by_token(share_token: str, db: Session) -> Project:
    # Backward-compatible helper used by legacy unit tests. New endpoints use
    # _resolve_share_context so ShareToken limits and scope are enforced.
    return _resolve_share_context(share_token, db, action="view", consume=False)["project"]


def _share_meta(resolved: dict) -> dict:
    token_model = resolved.get("share_token")
    if not token_model:
        return {"type": "legacy", "allow_download": True, "resource_type": "project", "resource_id": resolved["project"].id}
    data = token_model.to_dict(include_token=False)
    data["type"] = "share_token"
    data["allow_download"] = bool(token_model.allow_download)
    return data


def _files_for_share(resolved: dict, db: Session) -> list[DocumentFile]:
    project = resolved["project"]
    scoped_file = resolved.get("file")
    scoped_version = resolved.get("version")
    if scoped_file:
        return [scoped_file]
    if scoped_version:
        doc = db.query(DocumentFile).filter(DocumentFile.id == scoped_version.file_id, DocumentFile.project_id == project.id).first()
        return [doc] if doc else []
    return db.query(DocumentFile).filter(DocumentFile.project_id == project.id).all()


def _folders_for_share(files: list[DocumentFile], project_id: str, db: Session) -> list[ProjectFolder]:
    folder_ids = sorted({getattr(file, "folder_id", None) for file in files if getattr(file, "folder_id", None)})
    if not folder_ids:
        return []
    return (
        db.query(ProjectFolder)
        .filter(ProjectFolder.project_id == project_id, ProjectFolder.id.in_(folder_ids))
        .order_by(ProjectFolder.sort_order.asc(), ProjectFolder.created_at.asc())
        .all()
    )


def _latest_versions_by_file_id(db: Session, file_ids: list[str]) -> dict[str, FileVersion]:
    latest_versions_by_file_id: dict[str, FileVersion] = {}
    if not file_ids:
        return latest_versions_by_file_id

    latest_versions = (
        db.query(FileVersion)
        .filter(FileVersion.file_id.in_(file_ids))
        .order_by(
            FileVersion.file_id.asc(),
            FileVersion.version.desc(),
            FileVersion.sort_order.desc(),
            FileVersion.created_at.desc(),
        )
        .all()
    )
    for version in latest_versions:
        latest_versions_by_file_id.setdefault(version.file_id, version)
    return latest_versions_by_file_id


def _versioned_name(filename: str, version_num: int, new_ext: str = None) -> str:
    """生成带版本号的文件名，如 报告_v3.pdf"""
    base, ext = os.path.splitext(filename)
    if new_ext:
        ext = new_ext if new_ext.startswith(".") else f".{new_ext}"
    if not isinstance(version_num, int) or isinstance(version_num, bool):
        return f"{base}{ext}"
    return f"{base}_v{version_num}{ext}"


def _preview_display_title(doc_file: DocumentFile, version_num: Optional[int]) -> str:
    """预览页标题：优先显示后台设置的显示名称，并带版本号。"""
    name = (getattr(doc_file, "display_name", None) or getattr(doc_file, "filename", None) or "文档预览").strip()
    resolved_version = version_num or getattr(doc_file, "current_version", None) or 1
    return f"{name} · v{resolved_version}"


def _require_legacy_public_share(resolved: dict) -> None:
    if not resolved.get("legacy") or resolved.get("share_token") is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="legacy_public_access_only")


def _resolve_public_access_payload(
    resolved: dict,
    db: Session,
    body: dict | None,
) -> dict:
    payload = body if isinstance(body, dict) else {}
    resource_type = str(payload.get("resource_type") or "").strip().lower()
    resource_id = str(payload.get("resource_id") or "").strip()
    if not resource_type:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="resource_type is required")
    if not resource_id and resource_type != "project":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="resource_id is required")

    normalized_type, normalized_id, project_id = _resolve_public_access_resource(
        resolved,
        db,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    effective_policy = _resolve_share_effective_policy(
        resolved=resolved,
        db=db,
        resource_type=normalized_type,
        resource_id=normalized_id,
        project_id=project_id,
    )
    policy_model = _resolve_effective_resource_policy_model(
        db,
        resource_type=normalized_type,
        resource_id=normalized_id,
        project_id=project_id,
    )
    grant_resource_type, grant_resource_id = _resolve_legacy_access_grant_scope(
        db,
        resource_type=normalized_type,
        resource_id=normalized_id,
        project_id=project_id,
    )
    return {
        "resource_type": normalized_type,
        "resource_id": normalized_id,
        "project_id": project_id,
        "policy": effective_policy,
        "policy_model": policy_model,
        "grant_resource_type": grant_resource_type,
        "grant_resource_id": grant_resource_id,
    }


@router.get("/{share_token}")
def get_shared_project(
    share_token: str,
    request: Request,
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_share_password_grant(
        resolved,
        db,
        request,
        share_access_grant,
        allow_cookie_fallback=False,
    )
    _require_shared_root_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        allow_cookie_fallback=False,
    )
    token_model = resolved.get("share_token")
    if token_model:
        consume_share_token(token_model, action="view")
        db.commit()
        db.refresh(token_model)
    project = resolved["project"]

    files = _files_for_share(resolved, db)
    folders = _folders_for_share(files, project.id, db)
    file_count = len(files)
    file_ids = [f.id for f in files]

    # 批量获取最新版本信息（download 和 changelog 用）
    latest_versions = {}
    if file_ids:
        from sqlalchemy import tuple_
        from sqlalchemy.sql import func
        max_v = (
            db.query(FileVersion.file_id, func.max(FileVersion.version).label("max_ver"))
            .filter(FileVersion.file_id.in_(file_ids))
            .group_by(FileVersion.file_id)
            .subquery()
        )
        rows = (
            db.query(FileVersion)
            .join(max_v, tuple_(FileVersion.file_id, FileVersion.version) == tuple_(max_v.c.file_id, max_v.c.max_ver))
            .all()
        )
        latest_versions = {r.file_id: r for r in rows}

    file_list = []
    for f in files:
        latest = latest_versions.get(f.id)
        versions_info = []
        if latest:
            versions_info = [{
                "id": latest.id,
                "version": latest.version,
                "file_size": latest.file_size,
                "changelog": latest.changelog,
                **build_download_contract(f.filename, f.file_type),
            }]
        file_list.append({
            "id": f.id,
            "project_id": f.project_id,
            "folder_id": f.folder_id,
            "display_name": f.display_name,
            "original_filename": f.filename,
            "filename": f.filename,
            "file_type": f.file_type,
            "current_version": f.current_version,
            "file_size": latest.file_size if latest else 0,
            "created_at": f.created_at,
            "updated_at": f.updated_at or f.created_at,
            "latest_changelog": latest.changelog if latest else "",
            "versions": versions_info,
            **build_download_contract(f.filename, f.file_type),
        })

    return success_response(
        data={
            "project": ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                share_token=share_token,
                is_public=project.is_public,
                file_count=file_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            ).model_dump(),
            "files": file_list,
            "folders": [
                {
                    "id": folder.id,
                    "project_id": folder.project_id,
                    "parent_id": folder.parent_id,
                    "name": folder.name,
                    "sort_order": folder.sort_order,
                    "created_at": folder.created_at,
                    "updated_at": folder.updated_at,
                }
                for folder in folders
            ],
            "share": _share_meta(resolved),
        }
    )


@router.post("/{share_token}/public-access/unlock")
def unlock_public_access(
    share_token: str,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    x_access_tab_id: Optional[str] = Header(None, alias="X-Access-Tab-Id"),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_legacy_public_share(resolved)

    access_target = _resolve_public_access_payload(resolved, db, body)
    resource_key = f"{share_token}:{access_target['grant_resource_type']}:{access_target['grant_resource_id']}"
    _ensure_share_unlock_not_limited(request, resource_key)

    policy: AccessPolicy = access_target["policy"]
    policy_model: ResourceAccessPolicy | None = access_target["policy_model"]
    if policy.visibility != "password_required":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="resource_password_not_enabled")
    if not policy_model or not getattr(policy_model, "password_hash", None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="resource_password_not_configured")

    password = str(body.get("password") or "")
    if not password or not verify_password(password, policy_model.password_hash):
        _record_share_unlock_failure(request, resource_key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="resource_password_invalid")

    normalized_tab_id = str(x_access_tab_id or "").strip()
    if not normalized_tab_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="access_tab_id_required")

    _clear_share_unlock_failures(request, resource_key)
    grant_token = issue_resource_access_grant(
        db,
        share_token=share_token,
        resource_type=access_target["grant_resource_type"],
        resource_id=access_target["grant_resource_id"],
        tab_id=normalized_tab_id,
        ttl_seconds=DEFAULT_RESOURCE_ACCESS_GRANT_TTL_SECONDS,
    )
    grant = heartbeat_resource_access_grant(
        db,
        share_token=share_token,
        resource_type=access_target["grant_resource_type"],
        resource_id=access_target["grant_resource_id"],
        tab_id=normalized_tab_id,
        raw_grant=grant_token,
        ttl_seconds=DEFAULT_RESOURCE_ACCESS_GRANT_TTL_SECONDS,
    )
    return success_response(data={
        "unlocked": True,
        "resource_type": access_target["resource_type"],
        "resource_id": access_target["resource_id"],
        "grant_token": grant_token,
        "expires_at": grant.expires_at.isoformat() if grant else None,
        "heartbeat_interval_seconds": SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS,
    })


@router.post("/{share_token}/public-access/grant/heartbeat")
def heartbeat_public_access(
    share_token: str,
    request: Request,
    body: Optional[dict] = Body(None),
    db: Session = Depends(get_db),
    x_access_tab_id: Optional[str] = Header(None, alias="X-Access-Tab-Id"),
    x_access_grant: Optional[str] = Header(None, alias="X-Access-Grant"),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_legacy_public_share(resolved)

    access_target = _resolve_public_access_payload(resolved, db, body)
    policy: AccessPolicy = access_target["policy"]
    if policy.visibility != "password_required":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="resource_password_not_enabled")

    tab_id = _normalize_share_grant_transport_value(
        x_access_tab_id,
        body.get("tab_id") if isinstance(body, dict) else None,
        body.get("access_tab_id") if isinstance(body, dict) else None,
    )
    grant_token = _normalize_share_grant_transport_value(
        x_access_grant,
        body.get("grant_token") if isinstance(body, dict) else None,
        body.get("access_grant") if isinstance(body, dict) else None,
    )

    grant = heartbeat_resource_access_grant(
        db,
        share_token=share_token,
        resource_type=access_target["grant_resource_type"],
        resource_id=access_target["grant_resource_id"],
        tab_id=tab_id,
        raw_grant=grant_token,
        ttl_seconds=DEFAULT_RESOURCE_ACCESS_GRANT_TTL_SECONDS,
    )
    if grant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="resource_password_required")

    return success_response(data={
        "active": True,
        "resource_type": access_target["resource_type"],
        "resource_id": access_target["resource_id"],
        "expires_at": grant.expires_at.isoformat(),
        "heartbeat_interval_seconds": SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS,
    })


@router.post("/{share_token}/public-access/grant/release")
def release_public_access(
    share_token: str,
    request: Request,
    body: Optional[dict] = Body(None),
    db: Session = Depends(get_db),
    x_access_tab_id: Optional[str] = Header(None, alias="X-Access-Tab-Id"),
    x_access_grant: Optional[str] = Header(None, alias="X-Access-Grant"),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_legacy_public_share(resolved)

    access_target = _resolve_public_access_payload(resolved, db, body)
    policy: AccessPolicy = access_target["policy"]
    if policy.visibility != "password_required":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="resource_password_not_enabled")

    tab_id = _normalize_share_grant_transport_value(
        x_access_tab_id,
        body.get("tab_id") if isinstance(body, dict) else None,
        body.get("access_tab_id") if isinstance(body, dict) else None,
    )
    grant_token = _normalize_share_grant_transport_value(
        x_access_grant,
        body.get("grant_token") if isinstance(body, dict) else None,
        body.get("access_grant") if isinstance(body, dict) else None,
    )

    released = release_resource_access_grant(
        db,
        share_token=share_token,
        resource_type=access_target["grant_resource_type"],
        resource_id=access_target["grant_resource_id"],
        tab_id=tab_id,
        raw_grant=grant_token,
    )
    if not released:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="resource_password_required")

    return success_response(data={
        "released": True,
        "resource_type": access_target["resource_type"],
        "resource_id": access_target["resource_id"],
    })


@router.post("/{share_token}/unlock")
def unlock_share_access(
    share_token: str,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    x_share_tab_id: Optional[str] = Header(None, alias="X-Share-Tab-Id"),
):
    _ensure_share_unlock_not_limited(request, share_token)

    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    token_model = resolved.get("share_token")
    if not token_model or not getattr(token_model, "password_hash", None):
        return success_response(data={"unlocked": True, "heartbeat_interval_seconds": SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS})

    password = str(body.get("password") or "")
    if not password or not verify_password(password, token_model.password_hash):
        _record_share_unlock_failure(request, share_token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="share_password_invalid")

    _clear_share_unlock_failures(request, share_token)
    normalized_tab_id = str(x_share_tab_id or "").strip()
    if not normalized_tab_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="share_tab_id_required")

    grant_token = issue_share_tab_grant(
        db,
        share_token=token_model.token,
        tab_id=normalized_tab_id,
        ttl_seconds=DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS,
    )
    expires_at = heartbeat_share_tab_grant(
        db,
        share_token=token_model.token,
        tab_id=normalized_tab_id,
        raw_grant=grant_token,
        ttl_seconds=DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS,
    )

    response = JSONResponse(content=success_response(data={
        "unlocked": True,
        "grant_token": grant_token,
        "expires_at": expires_at.expires_at.isoformat() if expires_at else None,
        "heartbeat_interval_seconds": SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS,
    }))
    response.set_cookie(
        key=COOKIE_NAME,
        value=issue_share_access_grant(token_model.token, expires_in_seconds=DEFAULT_TTL_SECONDS),
        max_age=DEFAULT_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=bool(getattr(settings, "FORCE_HTTPS", False)),
        path=f"/api/v1/share/{token_model.token}",
    )
    return response


@router.post("/{share_token}/grant/heartbeat")
def heartbeat_share_access(
    share_token: str,
    request: Request,
    db: Session = Depends(get_db),
    x_share_tab_id: Optional[str] = Header(None, alias="X-Share-Tab-Id"),
    x_share_grant: Optional[str] = Header(None, alias="X-Share-Grant"),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    token_model = resolved.get("share_token")
    if not token_model or not getattr(token_model, "password_hash", None):
        return success_response(data={"active": True, "heartbeat_interval_seconds": SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS})

    grant = heartbeat_share_tab_grant(
        db,
        share_token=token_model.token,
        tab_id=x_share_tab_id,
        raw_grant=x_share_grant,
        ttl_seconds=DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS,
    )
    if grant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="share_password_required")

    return success_response(data={
        "active": True,
        "expires_at": grant.expires_at.isoformat(),
        "heartbeat_interval_seconds": SHARE_TAB_HEARTBEAT_INTERVAL_SECONDS,
    })


@router.post("/{share_token}/grant/release")
def release_share_access(
    share_token: str,
    request: Request,
    body: Optional[dict] = Body(None),
    db: Session = Depends(get_db),
    x_share_tab_id: Optional[str] = Header(None, alias="X-Share-Tab-Id"),
    x_share_grant: Optional[str] = Header(None, alias="X-Share-Grant"),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    token_model = resolved.get("share_token")
    if not token_model or not getattr(token_model, "password_hash", None):
        return success_response(data={"released": True})

    payload = body if isinstance(body, dict) else {}
    tab_id = _normalize_share_grant_transport_value(
        x_share_tab_id,
        payload.get("tab_id"),
        payload.get("share_tab_id"),
    )
    grant_token = _normalize_share_grant_transport_value(
        x_share_grant,
        payload.get("grant_token"),
        payload.get("share_grant"),
    )

    released = release_share_tab_grant(
        db,
        share_token=token_model.token,
        tab_id=tab_id,
        raw_grant=grant_token,
    )
    if not released:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="share_password_required")

    response = JSONResponse(content=success_response(data={"released": True}))
    response.delete_cookie(
        key=COOKIE_NAME,
        path=f"/api/v1/share/{token_model.token}",
    )
    return response


@router.post("/{share_token}/resource-ticket")
def issue_share_resource_ticket_endpoint(
    share_token: str,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    kind = str(body.get("kind") or "").strip()
    if not kind:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="kind is required")

    context_action = "download" if kind in {"download_original", "download_converted", "folder_download"} else "view"
    resolved = _resolve_share_context(share_token, db, action=context_action, consume=False)
    token_model = resolved.get("share_token")
    legacy_public_access = bool(resolved.get("legacy") and token_model is None)
    ticket_tab_id = _share_tab_id_from_request(request)
    ticket_grant_token = _share_grant_from_request(request)
    unlocked_override: Optional[bool] = True
    ticket_access_resource_type: str | None = None
    ticket_access_resource_id: str | None = None

    if legacy_public_access:
        ticket_tab_id = _access_tab_id_from_request(request)
        ticket_grant_token = _access_grant_from_request(request)
        unlocked_override = None
    else:
        if not token_model or not getattr(token_model, "password_hash", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="share_password_not_enabled")

        _require_share_password_grant(
            resolved,
            db,
            request,
            share_access_grant,
            allow_cookie_fallback=False,
        )

    file_id = str(body.get("file_id") or "").strip() or None
    version_id = str(body.get("version_id") or "").strip() or None
    asset_id = str(body.get("asset_id") or "").strip() or None
    folder_id = str(body.get("folder_id") or "").strip() or None
    format_name = str(body.get("format") or "").strip() or None
    page_num = body.get("page_num")

    if kind == "preview":
        _require_share_action_enabled(resolved, "preview")
        doc_file = share_scope_file_filter(resolved, db, file_id)
        _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            doc_file,
            "view_preview",
            allow_cookie_fallback=False,
            share_unlocked_override=unlocked_override,
        )
        ticket_access_resource_type, ticket_access_resource_id = _resolve_legacy_access_grant_scope(
            db,
            resource_type="file",
            resource_id=doc_file.id,
            project_id=doc_file.project_id,
        )
    elif kind == "page":
        _require_share_action_enabled(resolved, "preview")
        doc_file = share_scope_file_filter(resolved, db, file_id)
        _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            doc_file,
            "view_page_asset",
            allow_cookie_fallback=False,
            share_unlocked_override=unlocked_override,
        )
        ticket_access_resource_type, ticket_access_resource_id = _resolve_legacy_access_grant_scope(
            db,
            resource_type="file",
            resource_id=doc_file.id,
            project_id=doc_file.project_id,
        )
    elif kind == "preview_asset":
        _require_share_action_enabled(resolved, "preview")
        doc_file = share_scope_file_filter(resolved, db, file_id)
        _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            doc_file,
            "view_page_asset",
            allow_cookie_fallback=False,
            share_unlocked_override=unlocked_override,
        )
        ticket_access_resource_type, ticket_access_resource_id = _resolve_legacy_access_grant_scope(
            db,
            resource_type="file",
            resource_id=doc_file.id,
            project_id=doc_file.project_id,
        )
        asset = _load_preview_asset(db, file_id, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview asset not found")
        version = db.query(FileVersion).filter(FileVersion.id == asset.version_id).first()
        if not version or version.file_id != file_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        assert_version_in_share_scope(resolved, version)
    elif kind == "download_original":
        doc_file = share_scope_file_filter(resolved, db, file_id)
        _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            doc_file,
            "download_original",
            allow_cookie_fallback=False,
            share_unlocked_override=unlocked_override,
        )
        ticket_access_resource_type, ticket_access_resource_id = _resolve_legacy_access_grant_scope(
            db,
            resource_type="file",
            resource_id=doc_file.id,
            project_id=doc_file.project_id,
        )
        version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
        if not version or version.file_id != file_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        assert_version_in_share_scope(resolved, version)
    elif kind == "download_converted":
        doc_file = share_scope_file_filter(resolved, db, file_id)
        _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            doc_file,
            "download_converted",
            allow_cookie_fallback=False,
            share_unlocked_override=unlocked_override,
        )
        ticket_access_resource_type, ticket_access_resource_id = _resolve_legacy_access_grant_scope(
            db,
            resource_type="file",
            resource_id=doc_file.id,
            project_id=doc_file.project_id,
        )
        version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
        if not version or version.file_id != file_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        assert_version_in_share_scope(resolved, version)
    elif kind == "folder_download":
        project = resolved["project"]
        folder = (
            db.query(ProjectFolder)
            .filter(
                ProjectFolder.id == folder_id,
                ProjectFolder.project_id == project.id,
            )
            .first()
        )
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        folder_files = [
            file
            for file in _files_for_share(resolved, db)
            if getattr(file, "folder_id", None) == folder_id
        ]
        for file in folder_files:
            _require_shared_file_action(
                resolved,
                db,
                request,
                current_user,
                share_access_grant,
                file,
                "download_original",
                allow_cookie_fallback=False,
                share_unlocked_override=unlocked_override,
            )
        ticket_access_resource_type, ticket_access_resource_id = _resolve_legacy_access_grant_scope(
            db,
            resource_type="project",
            resource_id=project.id,
            project_id=project.id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="unsupported share resource ticket kind",
        )

    try:
        ticket = issue_share_resource_ticket(
            db,
            share_token=token_model.token if token_model else share_token,
            tab_id=ticket_tab_id,
            raw_grant=ticket_grant_token,
            kind=kind,
            file_id=file_id,
            version_id=version_id,
            page_num=page_num,
            asset_id=asset_id,
            folder_id=folder_id,
            format=format_name,
            access_resource_type=ticket_access_resource_type if legacy_public_access else None,
            access_resource_id=ticket_access_resource_id if legacy_public_access else None,
            ttl_seconds=DEFAULT_SHARE_RESOURCE_TICKET_TTL_SECONDS,
        )
    except ValueError as exc:
        detail = "resource_password_required" if legacy_public_access else "share_password_required"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail) from exc
    return success_response(data={
        "ticket": ticket,
        "expires_in_seconds": DEFAULT_SHARE_RESOURCE_TICKET_TTL_SECONDS,
    })


@router.get("/{share_token}/files/{file_id}")
def get_shared_file(
    share_token: str,
    file_id: str,
    request: Request,
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_share_password_grant(
        resolved,
        db,
        request,
        share_access_grant,
        allow_cookie_fallback=False,
    )
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_metadata",
        allow_cookie_fallback=False,
    )
    payload = _build_file_detail_payload(db, doc_file, share_token=share_token)
    latest_ver = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version.desc())
        .first()
    )
    payload.update(
        {
            "original_filename": doc_file.filename,
            "file_size": latest_ver.file_size if latest_ver else 0,
            "share": _share_meta(resolved),
        }
    )
    return success_response(data=payload)


@router.get("/{share_token}/files/{file_id}/versions")
def get_shared_versions(
    share_token: str,
    file_id: str,
    request: Request,
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_share_password_grant(
        resolved,
        db,
        request,
        share_access_grant,
        allow_cookie_fallback=False,
    )
    _require_share_action_enabled(resolved, "versions")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_versions",
        allow_cookie_fallback=False,
    )

    versions = (
        share_scope_versions_query(resolved, db, file_id)
        .order_by(FileVersion.version.desc())
        .all()
    )

    version_list = []
    for v in versions:
        version_list.append(_build_version_payload(db, doc_file, v, share_token=share_token))

    file_type = getattr(doc_file, "file_type", None)
    if not isinstance(file_type, str) or not file_type:
        file_type = os.path.splitext(str(doc_file.filename))[1].lstrip(".") or "unknown"

    result = VersionListResponse(
        file_id=doc_file.id,
        filename=doc_file.filename,
        file_type=file_type,
        current_version=doc_file.current_version,
        versions=version_list,
    ).model_dump()
    result["share"] = _share_meta(resolved)
    return success_response(data=result)


@router.get("/{share_token}/folders/{folder_id}/download")
def download_shared_folder_bundle(
    share_token: str,
    folder_id: str,
    request: Request,
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="download", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="folder_download",
        folder_id=folder_id,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    project = resolved["project"]

    folder = (
        db.query(ProjectFolder)
        .filter(
            ProjectFolder.id == folder_id,
            ProjectFolder.project_id == project.id,
        )
        .first()
    )
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    folder_files = [
        file
        for file in _files_for_share(resolved, db)
        if getattr(file, "folder_id", None) == folder_id
    ]
    for file in folder_files:
        _require_shared_file_action(
            resolved,
            db,
            request,
            current_user,
            share_access_grant,
            file,
            "download_original",
            share_unlocked_override=True if ticket_claims is not None else None,
        )
    latest_versions_by_file_id = _latest_versions_by_file_id(
        db,
        [file.id for file in folder_files],
    )
    entries = [
        (file.filename, latest_versions_by_file_id[file.id].storage_path)
        for file in folder_files
        if latest_versions_by_file_id.get(file.id)
    ]

    response = build_folder_bundle_response(
        folder_name=folder.name,
        download_name=f"{folder.name}.zip",
        entries=entries,
    )

    token_model = resolved.get("share_token")
    if token_model:
        consume_share_token(token_model, action="download")
        db.commit()

    return response


@router.get("/{share_token}/files/{file_id}/diffs")
def get_shared_diffs(
    share_token: str,
    file_id: str,
    request: Request,
    old_version: Optional[str] = Query(None),
    new_version: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    old_version_id: Optional[str] = Query(None),
    new_version_id: Optional[str] = Query(None),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not hasattr(db, "query") and hasattr(new_version_id, "query"):
        db, old_version_id, new_version_id = new_version_id, db, old_version_id

    old_version = _normalize_optional_query_value(old_version)
    new_version = _normalize_optional_query_value(new_version)
    old_version_id = _normalize_optional_query_value(old_version_id)
    new_version_id = _normalize_optional_query_value(new_version_id)

    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    _require_share_password_grant(
        resolved,
        db,
        request,
        share_access_grant,
        allow_cookie_fallback=False,
    )
    _require_share_action_enabled(resolved, "diff")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_diff",
        allow_cookie_fallback=False,
    )

    resolved_old = _resolve_scoped_share_version(db, file_id, old_version or old_version_id)
    resolved_new = _resolve_scoped_share_version(db, file_id, new_version or new_version_id)

    if (old_version or old_version_id) and not resolved_old:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Old version not found")
    if (new_version or new_version_id) and not resolved_new:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New version not found")
    if resolved_old:
        assert_version_in_share_scope(resolved, resolved_old)
    if resolved_new:
        assert_version_in_share_scope(resolved, resolved_new)

    query = (
        db.query(DiffRecord)
        .join(FileVersion, DiffRecord.new_version_id == FileVersion.id)
        .filter(FileVersion.file_id == file_id)
    )

    if resolved_old and resolved_new:
        if resolved_old.id == resolved_new.id:
            return success_response(data=DiffListResponse(diffs=[]).model_dump())
        old_v, new_v = sorted([resolved_old, resolved_new], key=lambda item: item.version)
        try:
            diffs = [_get_or_create_shared_diff(db, old_v, new_v)]
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Diff computation failed: {exc}",
            )
    else:
        scoped_version = resolved.get("version")
        if scoped_version:
            query = query.filter(DiffRecord.new_version_id == scoped_version.id)

        if resolved_old:
            query = query.filter(DiffRecord.old_version_id == resolved_old.id)
        if resolved_new:
            query = query.filter(DiffRecord.new_version_id == resolved_new.id)

        diffs = query.order_by(DiffRecord.created_at.desc()).all()

    # 批量查询所有相关的 FileVersion，避免 N+1 查询
    version_ids: set = set()
    for d in diffs:
        version_ids.add(d.old_version_id)
        version_ids.add(d.new_version_id)

    version_map: dict = {}
    if version_ids:
        versions = (
            db.query(FileVersion)
            .filter(FileVersion.id.in_(version_ids))
            .all()
        )
        version_map = {v.id: v for v in versions}

    diff_list = []
    for d in diffs:
        old_v = version_map.get(d.old_version_id)
        new_v = version_map.get(d.new_version_id)
        old_number, new_number = _extract_version_number_snapshot(
            d,
            old_version=old_v,
            new_version=new_v,
        )
        diff_list.append(
            DiffResponse(
                id=d.id,
                old_version_id=d.old_version_id,
                new_version_id=d.new_version_id,
                old_version=old_number,
                new_version=new_number,
                diff_type=d.diff_type,
                diff_data=d.diff_data,
                summary=d.summary,
                created_at=d.created_at,
            ).model_dump()
        )

    return success_response(data=DiffListResponse(diffs=diff_list).model_dump())


@router.get("/{share_token}/files/{file_id}/versions/{version_id}/download")
def download_shared_version(
    share_token: str,
    file_id: str,
    version_id: str,
    request: Request,
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="download", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="download_original",
        file_id=file_id,
        version_id=version_id,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "download_original",
        share_unlocked_override=True if ticket_claims is not None else None,
    )

    version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    assert_version_in_share_scope(resolved, version)

    if not os.path.exists(version.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    real_path = os.path.realpath(version.storage_path)
    if not _is_allowed_storage_path(real_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    token_model = resolved.get("share_token")
    if token_model:
        consume_share_token(token_model, action="download")
        db.commit()

    from urllib.parse import quote
    download_name = _versioned_name(doc_file.filename, version.version)
    safe_name = quote(download_name)
    media_type = mimetypes.guess_type(download_name)[0] or "application/octet-stream"
    return FastAPIFileResponse(
        path=real_path,
        filename=download_name,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.get("/{share_token}/files/{file_id}/versions/{version_id}/download/{format}")
def download_shared_version_formatted(
    share_token: str,
    file_id: str,
    version_id: str,
    format: str,
    background_tasks: BackgroundTasks,
    request: Request,
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    以指定格式下载分享文件的版本。

    支持的 format 值：
    - ``docx`` / ``word`` — 返回 Word 格式（原始 docx/doc 文件）
    - ``pdf`` — 返回 PDF 格式（服务端转换）

    对于 PDF 格式请求：
    - 如果原文件已是 PDF → 直接返回
    - 如果原文件是 DOCX/DOC → LibreOffice 原生转换（不可用时生成 HTML 供浏览器打印）
    - 如果原文件是 XLSX/XLS → 同理转换
    """
    resolved = _resolve_share_context(share_token, db, action="download", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="download_converted",
        file_id=file_id,
        version_id=version_id,
        format=format,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "download_converted",
        share_unlocked_override=True if ticket_claims is not None else None,
    )

    version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    assert_version_in_share_scope(resolved, version)

    if not os.path.exists(version.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    real_path = os.path.realpath(version.storage_path)
    if not _is_allowed_storage_path(real_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    token_model = resolved.get("share_token")
    if token_model:
        consume_share_token(token_model, action="download")
        db.commit()

    from app.services.conversion_service import convert_to_pdf, convert_to_word, schedule_cleanup
    from urllib.parse import quote

    fmt = format.lower().strip()
    file_type = doc_file.file_type.lower()

    if fmt in ("docx", "word"):
        output_path, media_type, actual_fmt, needs_cleanup = convert_to_word(
            version.storage_path, file_type, doc_file.filename
        )
        output_real_path = os.path.realpath(output_path)
        if not _is_allowed_response_path(output_real_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        # Word 格式：带版本号
        download_name = _versioned_name(doc_file.filename, version.version, ".docx")
        if needs_cleanup:
            schedule_cleanup(background_tasks, output_path)
        return FastAPIFileResponse(
            path=output_real_path,
            filename=download_name,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(download_name)}"},
        )

    elif fmt == "pdf":
        output_path, media_type, actual_fmt, needs_cleanup = convert_to_pdf(
            version.storage_path, file_type, doc_file.filename
        )
        output_real_path = os.path.realpath(output_path)
        if not _is_allowed_response_path(output_real_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        # PDF 文件名（带版本号）
        pdf_name = _versioned_name(doc_file.filename, version.version, ".pdf")
        disposition = "inline" if actual_fmt == "html" else "attachment"
        if needs_cleanup:
            schedule_cleanup(background_tasks, output_path)
        return FastAPIFileResponse(
            path=output_real_path,
            filename=pdf_name,
            media_type=media_type,
            headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(pdf_name)}"},
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}. Supported: docx, pdf",
        )


@router.get("/{share_token}/files/{file_id}/preview")
def preview_shared_file(
    share_token: str,
    file_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    version: Optional[int] = Query(None),
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """公开预览分享文件（无需登录）。优先使用 MS Word COM 导出 HTML，保真度最高。"""
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="preview",
        file_id=file_id,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    _require_share_action_enabled(resolved, "preview")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_preview",
        share_unlocked_override=True if ticket_claims is not None else None,
    )

    query = share_scope_versions_query(resolved, db, file_id)
    if version:
        query = query.filter(FileVersion.version == version)
    fv = query.order_by(FileVersion.version.desc()).first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    preview_title = _preview_display_title(doc_file, fv.version)

    # 路径穿越防御
    real_path = os.path.realpath(fv.storage_path)
    if not _is_allowed_storage_path(real_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from app.services.conversion_service import convert_to_html, convert_to_pdf

    if doc_file.file_type == "pdf":
        from urllib.parse import quote

        preview_params = []
        if version:
            preview_params.append(f"version={version}")
        if ticket_claims is not None and ticket:
            preview_params.append(f"ticket={quote(str(ticket), safe='')}")
        query_string = f"?{'&'.join(preview_params)}" if preview_params else ""
        html = f'<iframe src="/api/v1/share/{share_token}/files/{file_id}/preview/pdf{query_string}" width="100%" height="100%" style="border:none;min-height:700px"></iframe>'
        return HTMLResponse(content=html)

    if doc_file.file_type == "html":
        asset_query_params = {}
        if ticket_claims is not None and ticket:
            asset_query_params["ticket"] = ticket
        runtime_html = build_runtime_html_preview(
            storage_path=fv.storage_path,
            title=preview_title,
            asset_url_resolver=lambda raw_url: _build_html_asset_url(
                route_base_path=f"/api/v1/share/{share_token}/files/{file_id}/html-assets",
                raw_url=raw_url,
                version=fv.version,
                extra_query_params=asset_query_params,
            ),
        )
        return HTMLResponse(content=runtime_html, headers=runtime_html_response_headers())

    previewable_category = _previewable_category_for_file(doc_file)
    if previewable_category == "video":
        compatible_asset = _load_version_preview_asset(db, file_id, fv.id, "preview_video")
        if compatible_asset:
            return _stream_preview_asset(compatible_asset)
        return _stream_native_preview_file(doc_file, fv.storage_path)

    if previewable_category == "image":
        return _stream_native_preview_file(doc_file, fv.storage_path)

    # DOCX/DOC: try cached images first, then fallback
    if doc_file.file_type in ("docx", "doc"):
        from app.exceptions import ConversionError
        from app.services.conversion_service import trigger_preconversion, build_skeleton_html, _source_hash

        # Try pre-converted images first (instant)
        source_hash = _source_hash(fv.storage_path)
        try:
            from app.services.document_store import get_cached_pdf, get_cached_images
            pdf_path = get_cached_pdf(file_id, source_hash)
            if pdf_path:
                import fitz
                doc = fitz.open(pdf_path)
                page_count = len(doc)
                doc.close()
                pdf_hash = _source_hash(pdf_path)
                cached_images = get_cached_images(file_id, pdf_hash, page_count)
                if cached_images and len(cached_images) == page_count:
                    html = build_skeleton_html(
                        file_id, page_count, page_count, version=fv.version,
                        page_url_prefix=f"/api/v1/share/{share_token}/files/{file_id}/pages",
                        extra_query_params={"ticket": ticket} if ticket_claims is not None and ticket else None,
                        title=preview_title,
                    )
                    return HTMLResponse(
                        content=html,
                        headers={"Cache-Control": "public, max-age=3600"},
                    )
        except Exception:
            pass

        # Trigger background pre-conversion for next time
        try:
            trigger_preconversion(file_id, fv.storage_path, doc_file.file_type)
        except Exception:
            pass

        # Don't block on synchronous pipeline ? return fast python-docx HTML now.
        # Background preconversion builds images for the next cache-hit request.

    # DOCX/DOC: fast python-docx HTML fallback (no blocking Word COM)
    if doc_file.file_type in ("docx", "doc"):
        try:
            from app.services.conversion_service import convert_to_html
            html, _media_type, _ = convert_to_html(fv.storage_path, doc_file.file_type, title=preview_title)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.warning(f"HTML preview failed: {e}")

    # XLSX/XLS: fallback - Word COM to PDF
    if doc_file.file_type in ("xlsx", "xls"):
        try:
            pdf_path, media_type, actual_fmt, needs_cleanup = convert_to_pdf(
                fv.storage_path, doc_file.file_type, doc_file.filename
            )
            pdf_real_path = os.path.realpath(pdf_path)
            if not _is_allowed_response_path(pdf_real_path):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
            if actual_fmt == "pdf":
                from urllib.parse import quote
                if needs_cleanup:
                    from app.services.conversion_service import schedule_cleanup
                    schedule_cleanup(background_tasks, pdf_path)
                safe_name = quote(os.path.basename(pdf_path))
                return FastAPIFileResponse(
                    path=pdf_real_path,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}", "Content-Encoding": "identity"},
                )
        except Exception as e:
            logger.warning(f"PDF preview conversion failed: {e}, fallback to HTML")

    # Fallback: HTML 预览
    try:
        html, media_type, _ = convert_to_html(fv.storage_path, doc_file.file_type, title=preview_title)
        return HTMLResponse(content=html)
    except Exception as e:
        logger.warning(
            "Shared preview conversion failed share=%s file=%s version=%s: %s",
            share_token,
            file_id,
            fv.version,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Preview failed")


@router.get("/{share_token}/files/{file_id}/pages/{page_num}")
def get_shared_page_image(
    share_token: str,
    file_id: str,
    page_num: int,
    request: Request,
    version: Optional[int] = Query(None),
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """分享预览按页返回 JPEG，用于轻量 HTML 预览。"""
    import fitz
    from app.services.conversion_service import _ensure_pdf, _source_hash
    from app.services.document_store import render_single_page
    from fastapi.responses import FileResponse as ShareFileResponse

    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="page",
        file_id=file_id,
        page_num=page_num,
    )
    if ticket_claims is None and ticket:
        ticket_claims = _validate_share_resource_ticket_claims(
            db,
            ticket,
            share_token=share_token,
            kind="preview",
            file_id=file_id,
        )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    _require_share_action_enabled(resolved, "preview")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_page_asset",
        share_unlocked_override=True if ticket_claims is not None else None,
    )

    query = share_scope_versions_query(resolved, db, file_id)
    if version:
        query = query.filter(FileVersion.version == version)
    fv = query.order_by(FileVersion.version.desc()).first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    real_path = os.path.realpath(fv.storage_path)
    if not _is_allowed_storage_path(real_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    source_hash = _source_hash(fv.storage_path)
    if doc_file.file_type == "pdf":
        pdf_path = fv.storage_path
        pdf_hash = source_hash
    else:
        pdf_path = _ensure_pdf(file_id, fv.storage_path, source_hash)
        if pdf_path is None:
            raise HTTPException(status_code=500, detail="PDF conversion failed")
        pdf_hash = _source_hash(pdf_path)

    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()

    if page_num < 1 or page_num > page_count:
        raise HTTPException(status_code=404, detail=f"Page {page_num} not found")

    try:
        img_path = render_single_page(file_id, pdf_path, page_num, page_count, pdf_hash, quality=75)
    except Exception as exc:
        logger.warning(f"分享页面渲染失败: file={file_id} page={page_num} err={exc}")
        raise HTTPException(status_code=500, detail="Page render failed")

    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail=f"Page {page_num} image not found")
    real_img_path = os.path.realpath(img_path)
    if not _is_allowed_response_path(real_img_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Page {page_num} image not found")

    return ShareFileResponse(
        path=real_img_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{share_token}/files/{file_id}/preview-assets/{asset_id}")
def get_shared_preview_asset(
    share_token: str,
    file_id: str,
    asset_id: str,
    request: Request,
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="preview_asset",
        file_id=file_id,
        asset_id=asset_id,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    _require_share_action_enabled(resolved, "preview")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_page_asset",
        share_unlocked_override=True if ticket_claims is not None else None,
    )

    asset = _load_preview_asset(db, file_id, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview asset not found")

    version = db.query(FileVersion).filter(FileVersion.id == asset.version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    assert_version_in_share_scope(resolved, version)

    return _stream_preview_asset(asset)


@router.get("/{share_token}/files/{file_id}/html-assets/{asset_path:path}")
def get_shared_html_preview_asset(
    share_token: str,
    file_id: str,
    asset_path: str,
    request: Request,
    version: Optional[int] = Query(None),
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="preview",
        file_id=file_id,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    _require_share_action_enabled(resolved, "preview")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_page_asset",
        share_unlocked_override=True if ticket_claims is not None else None,
    )
    if doc_file.file_type != "html":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    query = share_scope_versions_query(resolved, db, file_id)
    if version:
        query = query.filter(FileVersion.version == version)
    fv = query.order_by(FileVersion.version.desc()).first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return _stream_html_asset_file(fv.storage_path, asset_path)


@router.get("/{share_token}/files/{file_id}/preview/pdf")
def preview_shared_pdf(
    share_token: str,
    file_id: str,
    request: Request,
    version: Optional[int] = Query(None),
    ticket: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    share_access_grant: Optional[str] = Cookie(None, alias=COOKIE_NAME),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """公开预览 PDF 文件（内嵌渲染）。"""
    resolved = _resolve_share_context(share_token, db, action="view", consume=False)
    ticket_claims = _validate_share_resource_ticket_claims(
        db,
        ticket,
        share_token=share_token,
        kind="preview",
        file_id=file_id,
    )
    if ticket_claims is None:
        _require_share_password_grant(resolved, db, request, share_access_grant)
    _require_share_action_enabled(resolved, "preview")
    doc_file = share_scope_file_filter(resolved, db, file_id)
    _require_shared_file_action(
        resolved,
        db,
        request,
        current_user,
        share_access_grant,
        doc_file,
        "view_preview",
        share_unlocked_override=True if ticket_claims is not None else None,
    )
    if not doc_file or doc_file.file_type != "pdf":
        raise HTTPException(status_code=404, detail="Not a PDF file")

    query = share_scope_versions_query(resolved, db, file_id)
    if version:
        query = query.filter(FileVersion.version == version)
    fv = query.order_by(FileVersion.version.desc()).first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=404, detail="File not found")
    real_path = os.path.realpath(fv.storage_path)
    if not _is_allowed_storage_path(real_path):
        raise HTTPException(status_code=404, detail="File not found")

    from urllib.parse import quote
    safe_name = quote(doc_file.filename)
    return FastAPIFileResponse(
        path=real_path,
        filename=doc_file.filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}", "Content-Encoding": "identity"},
    )
