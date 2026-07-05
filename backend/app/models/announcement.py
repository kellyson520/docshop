"""
公告模型

支持纯文本内容与富内容块配置。
"""

import json
import uuid

from sqlalchemy import Column, Integer, String, Text

from app.database import Base
from app.utils.time import utc_now_iso


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(String(255), nullable=True)
    content_blocks_json = Column(Text, nullable=False, default="[]")
    popup_config_json = Column(Text, nullable=False, default="{}")
    display_mode = Column(String(20), nullable=False, default="scroll")
    push_method = Column(String(20), nullable=False, default="all")
    target_user_id = Column(String(36), nullable=True)
    start_time = Column(String(30), nullable=True)
    end_time = Column(String(30), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    priority = Column(Integer, nullable=False, default=0)
    created_by = Column(String(36), nullable=False)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "content_blocks": self._load_json(self.content_blocks_json, []),
            "popup_config": self._load_json(self.popup_config_json, {}),
            "display_mode": self.display_mode,
            "push_method": self.push_method,
            "target_user_id": self.target_user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_active": self.is_active,
            "priority": self.priority,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def _load_json(value, fallback):
        if not value:
            return fallback
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return fallback
