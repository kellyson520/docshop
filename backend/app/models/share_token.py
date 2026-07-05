import secrets
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Index

from app.utils.time import utc_now, utc_now_iso
from app.database import Base


class ShareToken(Base):
    __tablename__ = "share_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False, default="分享令牌")
    resource_type = Column(String(20), nullable=False, default="project")  # project / file / version
    resource_id = Column(String(36), nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    allow_download = Column(Integer, nullable=False, default=1)
    require_login = Column(Integer, nullable=False, default=0)
    password_hash = Column(String(255), nullable=True)
    password_hint = Column(String(120), nullable=True)
    allow_preview = Column(Integer, nullable=False, default=1)
    allow_diff = Column(Integer, nullable=False, default=1)
    allow_versions = Column(Integer, nullable=False, default=1)
    policy_mode = Column(String(40), nullable=False, default="override_with_token_policy")
    max_views = Column(Integer, nullable=False, default=0)
    view_count = Column(Integer, nullable=False, default=0)
    max_downloads = Column(Integer, nullable=False, default=0)
    download_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(String(30), nullable=True)
    created_by = Column(String(36), nullable=False)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    __table_args__ = (
        Index("idx_share_tokens_resource", "resource_type", "resource_id"),
    )

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(32)

    def token_preview(self) -> str:
        if not self.token:
            return ""
        if len(self.token) <= 12:
            return f"{self.token[:2]}***{self.token[-2:]}"
        return f"{self.token[:4]}***{self.token[-4:]}"

    def to_dict(self, include_token: bool = False) -> dict:
        data = {
            "id": self.id,
            "token_preview": self.token_preview(),
            "name": self.name,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "is_active": self.is_active,
            "allow_download": self.allow_download,
            "require_login": bool(self.require_login),
            "password_hint": self.password_hint,
            "allow_preview": bool(self.allow_preview),
            "allow_diff": bool(self.allow_diff),
            "allow_versions": bool(self.allow_versions),
            "policy_mode": self.policy_mode,
            "max_views": self.max_views,
            "view_count": self.view_count,
            "max_downloads": self.max_downloads,
            "download_count": self.download_count,
            "expires_at": self.expires_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_token:
            data["token"] = self.token
        return data


class SharePolicy(Base):
    __tablename__ = "share_policies"

    id = Column(String(36), primary_key=True, default="default")
    enabled = Column(Integer, nullable=False, default=1)
    allow_anonymous_creation = Column(Integer, nullable=False, default=0)
    allow_user_creation = Column(Integer, nullable=False, default=1)
    allowed_resource_types = Column(String(120), nullable=False, default="project,file,version")
    default_max_views = Column(Integer, nullable=False, default=0)
    default_max_downloads = Column(Integer, nullable=False, default=0)
    default_allow_download = Column(Integer, nullable=False, default=1)
    max_expiry_days = Column(Integer, nullable=False, default=0)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    def allowed_types_list(self) -> list[str]:
        return [item.strip() for item in str(self.allowed_resource_types or "").split(",") if item.strip()]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "enabled": bool(self.enabled),
            "allow_anonymous_creation": bool(self.allow_anonymous_creation),
            "allow_user_creation": bool(self.allow_user_creation),
            "allowed_resource_types": self.allowed_types_list(),
            "default_max_views": self.default_max_views,
            "default_max_downloads": self.default_max_downloads,
            "default_allow_download": bool(self.default_allow_download),
            "max_expiry_days": self.max_expiry_days,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
