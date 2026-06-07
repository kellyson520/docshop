"""
访问令牌模型

用于主页门禁控制。
"""

import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Integer
from app.database import Base


class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, default="默认令牌")
    is_active = Column(Integer, nullable=False, default=1)
    created_by = Column(String(36), nullable=False)
    created_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self):
        return {
            "id": self.id,
            "token": self.token,
            "name": self.name,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def generate():
        """生成一个安全的随机令牌"""
        return secrets.token_urlsafe(32)
