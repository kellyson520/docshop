"""
公告模型

支持多种展示模式和推送方式的公告系统。
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    # 展示模式: scroll(滚动), popup(弹窗), sidebar(侧边), bottom(底部)
    display_mode = Column(String(20), nullable=False, default="scroll")
    # 推送方式: all(全部用户), timed(时间段), single(单用户)
    push_method = Column(String(20), nullable=False, default="all")
    # 单用户推送目标
    target_user_id = Column(String(36), nullable=True)
    # 时间段推送
    start_time = Column(String(30), nullable=True)
    end_time = Column(String(30), nullable=True)
    # 状态: 1=启用, 0=禁用
    is_active = Column(Integer, nullable=False, default=1)
    # 优先级: 数字越大越优先
    priority = Column(Integer, nullable=False, default=0)
    created_by = Column(String(36), nullable=False)
    created_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
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
