"""
考试安排模型模块

提供考试安排和提醒相关的数据库模型。
包含考试状态管理、提醒触发和关闭等功能。
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class ExamStatus(str, PyEnum):
    """
    考试状态枚举

    Attributes:
        upcoming: 即将开始
        ongoing: 进行中
        expired: 已结束
    """
    upcoming = "upcoming"  # 即将开始
    ongoing = "ongoing"    # 进行中
    expired = "expired"    # 已结束


class ExamSchedule(Base):
    """
    考试安排模型

    存储考试的基本信息、时间安排和提醒设置。

    Attributes:
        id: 考试ID
        name: 考试名称
        description: 考试描述
        start_time: 开始时间（ISO格式）
        end_time: 结束时间（ISO格式）
        project_id: 关联项目ID
        status: 考试状态
        reminder_15min: 是否启用15分钟前提醒
        reminder_5min: 是否启用5分钟前提醒
        reminder_start: 是否启用开始时提醒
        created_by: 创建者ID
        created_at: 创建时间
        updated_at: 更新时间
    """
    __tablename__ = "exam_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(String(30), nullable=False, index=True)
    end_time = Column(String(30), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=ExamStatus.upcoming.value, index=True)
    reminder_15min = Column(Integer, nullable=False, default=1)  # 0=关闭, 1=启用
    reminder_5min = Column(Integer, nullable=False, default=1)   # 0=关闭, 1=启用
    reminder_start = Column(Integer, nullable=False, default=1)  # 0=关闭, 1=启用
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.utcnow().isoformat() + "Z",
    )
    updated_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.utcnow().isoformat() + "Z",
    )

    # 关联关系
    project = relationship("Project", back_populates="exams")
    creator = relationship("User")
    reminders = relationship(
        "ExamReminder",
        back_populates="exam",
        cascade="all, delete-orphan"
    )

    # 复合索引
    __table_args__ = (
        Index('idx_exam_status_time', 'status', 'start_time'),
        Index('idx_exam_project', 'project_id', 'status'),
    )

    @staticmethod
    def _parse_dt(dt_str: str) -> datetime:
        """安全解析 datetime 字符串，始终返回 aware datetime"""
        if not dt_str:
            return datetime.now(timezone.utc)
        s = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def update_status(self) -> "ExamSchedule":
        """
        更新考试状态

        根据当前时间和考试时间自动更新状态。

        Returns:
            ExamSchedule: 返回自身实例，支持链式调用
        """
        now = datetime.now(timezone.utc)
        start = self._parse_dt(self.start_time)
        end = self._parse_dt(self.end_time)

        if now < start:
            self.status = ExamStatus.upcoming.value
        elif start <= now <= end:
            self.status = ExamStatus.ongoing.value
        else:
            self.status = ExamStatus.expired.value

        return self

    def is_expired(self) -> bool:
        """检查考试是否已结束"""
        now = datetime.now(timezone.utc)
        end = self._parse_dt(self.end_time)
        return now > end

    def is_upcoming(self) -> bool:
        """检查考试是否即将开始（未开始）"""
        now = datetime.now(timezone.utc)
        start = self._parse_dt(self.start_time)
        return now < start

    def is_ongoing(self) -> bool:
        """检查考试是否正在进行中"""
        now = datetime.now(timezone.utc)
        start = self._parse_dt(self.start_time)
        end = self._parse_dt(self.end_time)
        return start <= now <= end

    def get_time_until_start(self) -> float:
        """获取距离考试开始的分钟数（负数表示已开始）"""
        now = datetime.now(timezone.utc)
        start = self._parse_dt(self.start_time)
        diff = start - now
        return diff.total_seconds() / 60

    def get_time_until_end(self) -> float:
        """获取距离考试结束的分钟数（负数表示已结束）"""
        now = datetime.now(timezone.utc)
        end = self._parse_dt(self.end_time)
        diff = end - now
        return diff.total_seconds() / 60


class ExamReminder(Base):
    """
    考试提醒记录模型

    存储用户的考试提醒触发和关闭状态。

    Attributes:
        id: 提醒记录ID
        exam_id: 关联考试ID
        user_id: 关联用户ID
        reminder_type: 提醒类型（15min/5min/start）
        is_triggered: 是否已触发
        is_dismissed: 是否已关闭
        triggered_at: 触发时间
        dismissed_at: 关闭时间
        created_at: 创建时间
    """
    __tablename__ = "exam_reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = Column(String(36), ForeignKey("exam_schedules.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    reminder_type = Column(String(20), nullable=False)  # 15min, 5min, start
    is_triggered = Column(Integer, nullable=False, default=0)  # 0=未触发, 1=已触发
    is_dismissed = Column(Integer, nullable=False, default=0)  # 0=未关闭, 1=已关闭
    triggered_at = Column(String(30), nullable=True)
    dismissed_at = Column(String(30), nullable=True)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.utcnow().isoformat() + "Z",
    )

    # 关联关系
    exam = relationship("ExamSchedule", back_populates="reminders")
    user = relationship("User")

    # 复合索引
    __table_args__ = (
        Index('idx_reminder_user_exam', 'user_id', 'exam_id'),
        Index('idx_reminder_triggered', 'is_triggered', 'is_dismissed'),
    )

    def mark_triggered(self) -> "ExamReminder":
        """
        标记提醒为已触发

        Returns:
            ExamReminder: 返回自身实例，支持链式调用
        """
        if not self.is_triggered:
            self.is_triggered = 1
            self.triggered_at = datetime.utcnow().isoformat() + "Z"
        return self

    def mark_dismissed(self) -> "ExamReminder":
        """
        标记提醒为已关闭

        Returns:
            ExamReminder: 返回自身实例，支持链式调用
        """
        if not self.is_dismissed:
            self.is_dismissed = 1
            self.dismissed_at = datetime.utcnow().isoformat() + "Z"
        return self

    def is_active(self) -> bool:
        """
        检查提醒是否处于活动状态（已触发但未关闭）

        Returns:
            bool: 活动状态返回 True
        """
        return self.is_triggered == 1 and self.is_dismissed == 0

    def reset(self) -> "ExamReminder":
        """
        重置提醒状态

        Returns:
            ExamReminder: 返回自身实例，支持链式调用
        """
        self.is_triggered = 0
        self.is_dismissed = 0
        self.triggered_at = None
        self.dismissed_at = None
        return self
