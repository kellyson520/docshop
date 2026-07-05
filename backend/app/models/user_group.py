import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String

from app.database import Base
from app.utils.time import utc_now_iso


class UserGroup(Base):
    __tablename__ = "user_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), unique=True, nullable=False)
    code = Column(String(80), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())


class UserGroupMember(Base):
    __tablename__ = "user_group_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey("user_groups.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    __table_args__ = (
        Index("idx_user_group_members_group_user", "group_id", "user_id", unique=True),
    )
