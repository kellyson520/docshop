import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String

from app.database import Base
from app.utils.time import utc_now_iso


class ResourceAccessPolicy(Base):
    __tablename__ = "resource_access_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_type = Column(String(20), nullable=False, index=True)
    resource_id = Column(String(36), nullable=False, index=True)
    visibility = Column(String(30), nullable=False, default="inherit")
    password_hash = Column(String(255), nullable=True)
    password_hint = Column(String(120), nullable=True)
    allow_preview = Column(Integer, nullable=False, default=1)
    allow_download_original = Column(Integer, nullable=False, default=1)
    allow_download_converted = Column(Integer, nullable=False, default=1)
    allow_diff = Column(Integer, nullable=False, default=1)
    allow_versions = Column(Integer, nullable=False, default=1)
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    __table_args__ = (
        Index("idx_resource_access_policy_resource", "resource_type", "resource_id", unique=True),
    )


class ResourceAccessGroup(Base):
    __tablename__ = "resource_access_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id = Column(String(36), ForeignKey("resource_access_policies.id"), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey("user_groups.id"), nullable=False, index=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    __table_args__ = (
        Index("idx_resource_access_group_policy_group", "policy_id", "group_id", unique=True),
    )
