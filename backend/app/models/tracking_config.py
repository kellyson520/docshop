"""
追踪配置模型

管理用户追踪系统的配置选项，支持开启/关闭各类追踪功能。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text
from app.database import Base


class TrackingConfig(Base):
    """
    追踪配置模型

    存储用户追踪系统的全局配置，包括：
    - 各类追踪功能的开关
    - 数据保留策略
    - 隐私设置（IP匿名化、排除内网IP等）
    """

    __tablename__ = "tracking_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 追踪开关（1=开启，0=关闭）
    enable_tracking = Column(Integer, default=1)  # 总开关
    enable_ip_tracking = Column(Integer, default=1)  # IP追踪
    enable_device_tracking = Column(Integer, default=1)  # 设备信息追踪
    enable_location_tracking = Column(Integer, default=1)  # 地理位置追踪
    enable_behavior_tracking = Column(Integer, default=1)  # 行为追踪（原始数据）

    # 数据保留策略
    data_retention_days = Column(Integer, default=90)  # 默认保留90天

    # 隐私设置
    anonymize_ip = Column(Integer, default=0)  # 是否匿名化IP（1=是，0=否）
    exclude_internal_ips = Column(Text, default="")  # 排除的内网IP，逗号分隔

    # 时间戳
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

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "enable_tracking": bool(self.enable_tracking),
            "enable_ip_tracking": bool(self.enable_ip_tracking),
            "enable_device_tracking": bool(self.enable_device_tracking),
            "enable_location_tracking": bool(self.enable_location_tracking),
            "enable_behavior_tracking": bool(self.enable_behavior_tracking),
            "data_retention_days": self.data_retention_days,
            "anonymize_ip": bool(self.anonymize_ip),
            "exclude_internal_ips": self.exclude_internal_ips,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def is_tracking_enabled(self, tracking_type: str = None) -> bool:
        """
        检查追踪是否启用

        Args:
            tracking_type: 追踪类型（ip/device/location/behavior），None表示检查总开关

        Returns:
            bool: 是否启用
        """
        if not self.enable_tracking:
            return False

        if tracking_type is None:
            return True

        tracking_map = {
            "ip": self.enable_ip_tracking,
            "device": self.enable_device_tracking,
            "location": self.enable_location_tracking,
            "behavior": self.enable_behavior_tracking,
        }

        return bool(tracking_map.get(tracking_type, 1))

    def should_exclude_ip(self, ip: str) -> bool:
        """
        检查IP是否应该被排除

        Args:
            ip: IP地址

        Returns:
            bool: 是否应该排除
        """
        if not self.exclude_internal_ips:
            return False

        excluded_ips = [ip.strip() for ip in self.exclude_internal_ips.split(",") if ip.strip()]
        return ip in excluded_ips
