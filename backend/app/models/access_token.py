"""
访问令牌模型

用于主页门禁控制。
"""

import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Integer
from app.utils.time import utc_now, utc_now_iso
from app.database import Base


class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, default="默认令牌")
    is_active = Column(Integer, nullable=False, default=1)
    created_by = Column(String(36), nullable=False)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    def token_preview(self) -> str:
        """Return a non-sensitive token preview for list/update responses."""
        if not self.token:
            return ""
        if len(self.token) <= 12:
            return f"{self.token[:2]}***{self.token[-2:]}"
        return f"{self.token[:4]}***{self.token[-4:]}"

    def to_dict(self, include_token: bool = False):
        data = {
            "id": self.id,
            "token_preview": self.token_preview(),
            "name": self.name,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_token:
            data["token"] = self.token
        return data

    @staticmethod
    def generate():
        """生成一个安全的随机令牌"""
        return secrets.token_urlsafe(32)
