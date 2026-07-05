import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.share_tab_grant import ShareTabGrant

DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS = 45


def _utcnow() -> datetime:
    return datetime.now()


def _normalize_token(value: str | None) -> str:
    return str(value or "").strip()


def _hash_grant(raw_grant: str) -> str:
    return hashlib.sha256(raw_grant.encode("utf-8")).hexdigest()


def _resolve_active_grant(
    db: Session,
    *,
    share_token: str,
    tab_id: str,
    raw_grant: str | None,
    allow_expired: bool = False,
) -> ShareTabGrant | None:
    normalized_share_token = _normalize_token(share_token)
    normalized_tab_id = _normalize_token(tab_id)
    normalized_raw_grant = _normalize_token(raw_grant)
    if not normalized_share_token or not normalized_tab_id or not normalized_raw_grant:
        return None

    grant = (
        db.query(ShareTabGrant)
        .filter(
            ShareTabGrant.share_token == normalized_share_token,
            ShareTabGrant.tab_id == normalized_tab_id,
            ShareTabGrant.grant_hash == _hash_grant(normalized_raw_grant),
            ShareTabGrant.released_at.is_(None),
        )
        .order_by(ShareTabGrant.issued_at.desc())
        .first()
    )
    if grant is None:
        return None
    if not allow_expired and grant.expires_at <= _utcnow():
        return None
    return grant


def issue_share_tab_grant(
    db: Session,
    *,
    share_token: str,
    tab_id: str,
    ttl_seconds: int = DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS,
) -> str:
    normalized_share_token = _normalize_token(share_token)
    normalized_tab_id = _normalize_token(tab_id)
    if not normalized_share_token or not normalized_tab_id:
        raise ValueError("share_token and tab_id are required")

    now = _utcnow()
    raw_grant = secrets.token_urlsafe(32)
    expires_at = now + timedelta(seconds=max(1, int(ttl_seconds)))

    (
        db.query(ShareTabGrant)
        .filter(
            ShareTabGrant.share_token == normalized_share_token,
            ShareTabGrant.tab_id == normalized_tab_id,
            ShareTabGrant.released_at.is_(None),
        )
        .update({"released_at": now}, synchronize_session=False)
    )

    grant = ShareTabGrant(
        share_token=normalized_share_token,
        tab_id=normalized_tab_id,
        grant_hash=_hash_grant(raw_grant),
        issued_at=now,
        last_seen_at=now,
        expires_at=expires_at,
    )
    db.add(grant)
    db.commit()
    return raw_grant


def validate_share_tab_grant(
    db: Session,
    share_token: str,
    tab_id: str,
    raw_grant: str | None,
) -> ShareTabGrant | None:
    return _resolve_active_grant(
        db,
        share_token=share_token,
        tab_id=tab_id,
        raw_grant=raw_grant,
        allow_expired=False,
    )


def heartbeat_share_tab_grant(
    db: Session,
    share_token: str,
    tab_id: str,
    raw_grant: str | None,
    ttl_seconds: int = DEFAULT_SHARE_TAB_GRANT_TTL_SECONDS,
) -> ShareTabGrant | None:
    grant = _resolve_active_grant(
        db,
        share_token=share_token,
        tab_id=tab_id,
        raw_grant=raw_grant,
        allow_expired=False,
    )
    if grant is None:
        return None

    now = _utcnow()
    grant.last_seen_at = now
    grant.expires_at = now + timedelta(seconds=max(1, int(ttl_seconds)))
    db.commit()
    db.refresh(grant)
    return grant


def release_share_tab_grant(
    db: Session,
    share_token: str,
    tab_id: str,
    raw_grant: str | None,
) -> bool:
    grant = _resolve_active_grant(
        db,
        share_token=share_token,
        tab_id=tab_id,
        raw_grant=raw_grant,
        allow_expired=True,
    )
    if grant is None:
        return False

    now = _utcnow()
    grant.last_seen_at = now
    grant.released_at = now
    db.commit()
    return True
