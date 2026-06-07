"""
用户会话模型

管理用户会话信息，用于追踪用户访问行为。
"""
import uuid
import hashlib
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index
from app.database import Base


class UserSession(Base):
    """
    用户会话模型

    记录用户会话信息，包括：
    - 首次访问信息
    - 最后访问信息
    - 访问统计
    - 设备指纹
    """

    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(64), unique=True, nullable=False, index=True)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # 首次访问信息
    first_seen_at = Column(String(30))
    first_ip = Column(String(45))
    first_user_agent = Column(Text)

    # 最后访问信息
    last_seen_at = Column(String(30))
    last_ip = Column(String(45))

    # 统计信息
    visit_count = Column(Integer, default=1)
    page_view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)

    # 设备指纹（用于识别同一设备）
    device_fingerprint = Column(String(64), index=True)

    # 设备信息（首次访问时记录）
    device_type = Column(String(20))
    os_name = Column(String(50))
    browser_name = Column(String(50))

    # 软删除标记
    is_deleted = Column(Integer, default=0)
    deleted_at = Column(String(30), nullable=True)

    # 复合索引
    __table_args__ = (
        Index("idx_user_session_user", "user_id", "last_seen_at"),
        Index("idx_user_session_fingerprint", "device_fingerprint", "last_seen_at"),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "first_seen_at": self.first_seen_at,
            "first_ip": self.first_ip,
            "first_user_agent": self.first_user_agent,
            "last_seen_at": self.last_seen_at,
            "last_ip": self.last_ip,
            "visit_count": self.visit_count,
            "page_view_count": self.page_view_count,
            "download_count": self.download_count,
            "device_fingerprint": self.device_fingerprint,
            "device_type": self.device_type,
            "os_name": self.os_name,
            "browser_name": self.browser_name,
            "is_deleted": bool(self.is_deleted),
        }

    def update_last_seen(self, ip: str = None):
        """
        更新最后访问时间

        Args:
            ip: 当前IP地址
        """
        self.last_seen_at = datetime.utcnow().isoformat() + "Z"
        if ip:
            self.last_ip = ip
        self.visit_count += 1

    def increment_page_view(self):
        """增加页面浏览计数"""
        self.page_view_count += 1

    def increment_download(self):
        """增加下载计数"""
        self.download_count += 1

    def soft_delete(self):
        """软删除"""
        self.is_deleted = 1
        self.deleted_at = datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def generate_fingerprint(user_agent: str, ip: str = None) -> str:
        """
        生成设备指纹

        基于User-Agent和IP生成简单的设备指纹，用于识别同一设备。
        注意：这不是一个强指纹，仅用于基础追踪。

        Args:
            user_agent: User-Agent字符串
            ip: IP地址（可选）

        Returns:
            str: 设备指纹（SHA256前16位）
        """
        data = user_agent if user_agent else ""
        if ip:
            data += f"|{ip}"

        return hashlib.sha256(data.encode()).hexdigest()[:64]

    @classmethod
    def create_session(
        cls,
        session_id: str,
        user_id: str = None,
        ip: str = None,
        user_agent: str = None,
        device_info: dict = None,
    ) -> "UserSession":
        """
        创建新会话

        Args:
            session_id: 会话ID
            user_id: 用户ID
            ip: IP地址
            user_agent: User-Agent字符串
            device_info: 设备信息字典

        Returns:
            UserSession: 会话实例
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        fingerprint = cls.generate_fingerprint(user_agent or "", ip)

        return cls(
            session_id=session_id,
            user_id=user_id,
            first_seen_at=timestamp,
            first_ip=ip,
            first_user_agent=user_agent[:500] if user_agent else None,
            last_seen_at=timestamp,
            last_ip=ip,
            device_fingerprint=fingerprint,
            device_type=device_info.get("device_type") if device_info else None,
            os_name=device_info.get("os_name") if device_info else None,
            browser_name=device_info.get("browser_name") if device_info else None,
        )
