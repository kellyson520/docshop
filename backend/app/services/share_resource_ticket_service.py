import base64
import hashlib
import hmac
import json
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.models.resource_access_grant import ResourceAccessGrant
from app.models.share_tab_grant import ShareTabGrant
from app.services.resource_access_grant_service import validate_resource_access_grant
from app.services.share_tab_grant_service import _utcnow, validate_share_tab_grant

DEFAULT_SHARE_RESOURCE_TICKET_TTL_SECONDS = 60


def _normalize_required(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


def _normalize_optional(value) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _normalize_page_num(value) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payload(encoded_payload: str) -> dict | None:
    try:
        padding = "=" * (-len(encoded_payload) % 4)
        raw = base64.urlsafe_b64decode(f"{encoded_payload}{padding}".encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (TypeError, ValueError, json.JSONDecodeError, base64.binascii.Error):
        return None
    return payload if isinstance(payload, dict) else None


def _sign_payload(encoded_payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _decode_ticket(raw_ticket: str | None) -> dict | None:
    if not raw_ticket or "." not in raw_ticket:
        return None

    try:
        encoded_payload, signature = str(raw_ticket).split(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(signature, _sign_payload(encoded_payload)):
        return None

    payload = _decode_payload(encoded_payload)
    if payload is None:
        return None

    expires_at = int(payload.get("exp") or 0)
    if expires_at <= int(time.time()):
        return None

    return payload


def issue_share_resource_ticket(
    db: Session,
    *,
    share_token: str,
    tab_id: str,
    raw_grant: str,
    kind: str,
    file_id: str | None = None,
    version_id: str | None = None,
    page_num: int | None = None,
    asset_id: str | None = None,
    folder_id: str | None = None,
    format: str | None = None,
    access_resource_type: str | None = None,
    access_resource_id: str | None = None,
    ttl_seconds: int = DEFAULT_SHARE_RESOURCE_TICKET_TTL_SECONDS,
) -> str:
    normalized_share_token = _normalize_required(share_token, "share_token")
    normalized_tab_id = _normalize_required(tab_id, "tab_id")
    normalized_kind = _normalize_required(kind, "kind")
    normalized_access_resource_type = _normalize_optional(access_resource_type)
    normalized_access_resource_id = _normalize_optional(access_resource_id)

    if normalized_access_resource_type and normalized_access_resource_id:
        grant = validate_resource_access_grant(
            db,
            share_token=normalized_share_token,
            resource_type=normalized_access_resource_type,
            resource_id=normalized_access_resource_id,
            tab_id=normalized_tab_id,
            raw_grant=raw_grant,
        )
        if grant is None:
            raise ValueError("active resource access grant required")
        grant_kind = "resource_access"
    else:
        grant = validate_share_tab_grant(
            db,
            share_token=normalized_share_token,
            tab_id=normalized_tab_id,
            raw_grant=raw_grant,
        )
        if grant is None:
            raise ValueError("active share tab grant required")
        grant_kind = "share_tab"

    payload = {
        "share_token": normalized_share_token,
        "tab_id": normalized_tab_id,
        "grant_id": grant.id,
        "grant_kind": grant_kind,
        "kind": normalized_kind,
        "file_id": _normalize_optional(file_id),
        "version_id": _normalize_optional(version_id),
        "page_num": _normalize_page_num(page_num),
        "asset_id": _normalize_optional(asset_id),
        "folder_id": _normalize_optional(folder_id),
        "format": _normalize_optional(format),
        "access_resource_type": normalized_access_resource_type,
        "access_resource_id": normalized_access_resource_id,
        "exp": int(time.time()) + max(1, int(ttl_seconds)),
    }
    encoded_payload = _encode_payload(payload)
    signature = _sign_payload(encoded_payload)
    return f"{encoded_payload}.{signature}"


def validate_share_resource_ticket(
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
) -> dict | None:
    payload = _decode_ticket(raw_ticket)
    if payload is None:
        return None

    normalized_share_token = _normalize_required(share_token, "share_token")
    normalized_kind = _normalize_required(kind, "kind")
    normalized_file_id = _normalize_optional(file_id)
    normalized_version_id = _normalize_optional(version_id)
    normalized_page_num = _normalize_page_num(page_num)
    normalized_asset_id = _normalize_optional(asset_id)
    normalized_folder_id = _normalize_optional(folder_id)
    normalized_format = _normalize_optional(format)
    normalized_tab_id = _normalize_optional(payload.get("tab_id"))
    normalized_grant_id = _normalize_optional(payload.get("grant_id"))
    normalized_grant_kind = _normalize_optional(payload.get("grant_kind")) or "share_tab"

    if payload.get("share_token") != normalized_share_token:
        return None
    if payload.get("kind") != normalized_kind:
        return None
    if _normalize_optional(payload.get("file_id")) != normalized_file_id:
        return None
    if _normalize_optional(payload.get("version_id")) != normalized_version_id:
        return None
    if _normalize_page_num(payload.get("page_num")) != normalized_page_num:
        return None
    if _normalize_optional(payload.get("asset_id")) != normalized_asset_id:
        return None
    if _normalize_optional(payload.get("folder_id")) != normalized_folder_id:
        return None
    if _normalize_optional(payload.get("format")) != normalized_format:
        return None
    if not normalized_tab_id or not normalized_grant_id:
        return None

    normalized_access_resource_type = _normalize_optional(payload.get("access_resource_type"))
    normalized_access_resource_id = _normalize_optional(payload.get("access_resource_id"))

    if normalized_grant_kind == "resource_access":
        if not normalized_access_resource_type or not normalized_access_resource_id:
            return None
        grant = (
            db.query(ResourceAccessGrant)
            .filter(
                ResourceAccessGrant.id == normalized_grant_id,
                ResourceAccessGrant.released_at.is_(None),
            )
            .first()
        )
        if grant is None or grant.expires_at <= _utcnow():
            return None
        if (
            grant.share_token != normalized_share_token
            or grant.tab_id != normalized_tab_id
            or grant.resource_type != normalized_access_resource_type
            or grant.resource_id != normalized_access_resource_id
        ):
            return None
    else:
        grant = (
            db.query(ShareTabGrant)
            .filter(
                ShareTabGrant.id == normalized_grant_id,
                ShareTabGrant.released_at.is_(None),
            )
            .first()
        )
        if grant is None or grant.expires_at <= _utcnow():
            return None
        if grant.share_token != normalized_share_token or grant.tab_id != normalized_tab_id:
            return None

    return {
        "share_token": normalized_share_token,
        "tab_id": normalized_tab_id,
        "grant_id": normalized_grant_id,
        "grant_kind": normalized_grant_kind,
        "kind": normalized_kind,
        "file_id": normalized_file_id,
        "version_id": normalized_version_id,
        "page_num": normalized_page_num,
        "asset_id": normalized_asset_id,
        "folder_id": normalized_folder_id,
        "format": normalized_format,
        "access_resource_type": normalized_access_resource_type,
        "access_resource_id": normalized_access_resource_id,
        "exp": int(payload.get("exp") or 0),
    }
