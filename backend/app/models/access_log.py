"""
访问日志模型

记录用户访问详情，包括设备信息、地理位置、请求响应等。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index
from app.database import Base


class AccessLog(Base):
    """
    访问日志模型

    详细记录每次用户访问的信息，包括：
    - 时间信息
    - 用户信息（可能未登录）
    - 网络信息（IP、地理位置）
    - 设备信息（User-Agent解析）
    - 请求信息（方法、路径、参数）
    - 响应信息（状态码、响应时间）
    - 业务信息（操作类型、目标对象）
    - 会话信息
    """

    __tablename__ = "access_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 时间信息
    timestamp = Column(String(30), nullable=False, index=True)

    # 用户信息（可能未登录）
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    is_authenticated = Column(Integer, default=0)  # 1=已认证，0=未认证

    # 网络信息
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6支持
    ip_country = Column(String(2))  # ISO国家代码
    ip_city = Column(String(100))
    ip_isp = Column(String(100))  # 运营商
    ip_asn = Column(String(50))   # ASN编号

    # 设备信息
    user_agent = Column(Text)
    device_type = Column(String(20))  # desktop/mobile/tablet/unknown
    device_brand = Column(String(50))  # Apple/Samsung/Xiaomi
    device_model = Column(String(100))
    os_name = Column(String(50))   # Windows/macOS/iOS/Android
    os_version = Column(String(50))
    browser_name = Column(String(50))  # Chrome/Safari/Firefox
    browser_version = Column(String(50))
    screen_resolution = Column(String(20))  # 1920x1080

    # 请求信息
    request_method = Column(String(10))
    request_path = Column(Text)
    request_query = Column(Text)
    referer = Column(Text)
    referer_host = Column(String(255))
    referer_domain = Column(String(255))
    referer_type = Column(String(32))

    # 响应信息
    response_status = Column(Integer)
    response_time_ms = Column(Integer)  # 响应时间（毫秒）

    # 业务信息
    action_type = Column(String(50))  # view/download/upload/login
    target_id = Column(String(36))    # 操作对象ID
    target_type = Column(String(50))  # file/project/card

    # 会话信息
    session_id = Column(String(64))

    # 原始数据（JSON格式，用于扩展）
    raw_data = Column(Text)

    # 软删除标记
    is_deleted = Column(Integer, default=0)  # 1=已删除，0=正常
    deleted_at = Column(String(30), nullable=True)

    # 复合索引优化查询
    __table_args__ = (
        Index("idx_access_log_timestamp", "timestamp"),
        Index("idx_access_log_user", "user_id", "timestamp"),
        Index("idx_access_log_session", "session_id", "timestamp"),
        Index("idx_access_log_ip", "ip_address", "timestamp"),
    )

    def to_dict(self, include_raw: bool = False) -> dict:
        """
        转换为字典

        Args:
            include_raw: 是否包含原始数据

        Returns:
            dict: 日志数据字典
        """
        data = {
            "id": self.id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "is_authenticated": bool(self.is_authenticated),
            "ip_address": self.ip_address,
            "ip_country": self.ip_country,
            "ip_city": self.ip_city,
            "ip_isp": self.ip_isp,
            "ip_asn": self.ip_asn,
            "device_type": self.device_type,
            "device_brand": self.device_brand,
            "device_model": self.device_model,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "browser_name": self.browser_name,
            "browser_version": self.browser_version,
            "screen_resolution": self.screen_resolution,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "request_query": self.request_query,
            "referer": self.referer,
            "referer_host": self.referer_host,
            "referer_domain": self.referer_domain,
            "referer_type": self.referer_type,
            "response_status": self.response_status,
            "response_time_ms": self.response_time_ms,
            "action_type": self.action_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "session_id": self.session_id,
            "is_deleted": bool(self.is_deleted),
        }

        if self.raw_data:
            import json
            try:
                raw = json.loads(self.raw_data)
                if isinstance(raw, dict) and isinstance(raw.get("business"), dict):
                    data["business_context"] = raw["business"]
            except json.JSONDecodeError:
                pass

        if include_raw and self.raw_data:
            import json
            try:
                data["raw_data"] = json.loads(self.raw_data)
            except json.JSONDecodeError:
                data["raw_data"] = self.raw_data

        return data

    def soft_delete(self):
        """软删除"""
        self.is_deleted = 1
        self.deleted_at = datetime.utcnow().isoformat() + "Z"

    @classmethod
    def from_request(
        cls,
        request,
        response_status: int = None,
        response_time_ms: int = None,
        user_id: str = None,
        session_id: str = None,
        device_info: dict = None,
        location_info: dict = None,
    ) -> "AccessLog":
        """
        从请求创建访问日志

        Args:
            request: FastAPI请求对象
            response_status: 响应状态码
            response_time_ms: 响应时间（毫秒）
            user_id: 用户ID
            session_id: 会话ID
            device_info: 设备信息字典
            location_info: 地理位置信息字典

        Returns:
            AccessLog: 访问日志实例
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # 获取IP地址
        ip_address = cls._get_client_ip(request)

        # 获取User-Agent
        user_agent = request.headers.get("user-agent", "")[:500] if hasattr(request, "headers") else None

        # 解析请求路径和查询参数
        request_path = str(request.url.path) if hasattr(request, "url") else None
        request_query = str(request.url.query) if hasattr(request, "url") else None
        request_method = request.method if hasattr(request, "method") else None
        referer = request.headers.get("referer") if hasattr(request, "headers") else None

        log = cls(
            timestamp=timestamp,
            user_id=user_id,
            is_authenticated=1 if user_id else 0,
            ip_address=ip_address,
            ip_country=location_info.get("country") if location_info else None,
            ip_city=location_info.get("city") if location_info else None,
            ip_isp=location_info.get("isp") if location_info else None,
            ip_asn=location_info.get("asn") if location_info else None,
            user_agent=user_agent,
            device_type=device_info.get("device_type") if device_info else None,
            device_brand=device_info.get("device_brand") if device_info else None,
            device_model=device_info.get("device_model") if device_info else None,
            os_name=device_info.get("os_name") if device_info else None,
            os_version=device_info.get("os_version") if device_info else None,
            browser_name=device_info.get("browser_name") if device_info else None,
            browser_version=device_info.get("browser_version") if device_info else None,
            screen_resolution=device_info.get("screen_resolution") if device_info else None,
            request_method=request_method,
            request_path=request_path,
            request_query=request_query,
            referer=referer,
            referer_host=None,
            referer_domain=None,
            referer_type=None,
            response_status=response_status,
            response_time_ms=response_time_ms,
            session_id=session_id,
        )

        return log

    @staticmethod
    def _get_client_ip(request) -> str:
        """
        获取客户端真实IP

        Args:
            request: FastAPI请求对象

        Returns:
            str: IP地址
        """
        if not hasattr(request, "headers"):
            return "unknown"

        # 优先从代理头获取
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"
