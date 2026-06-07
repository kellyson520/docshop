"""
用户追踪中间件

自动采集用户访问信息，包括设备信息、地理位置、请求响应等。
支持配置化开关和隐私保护功能。
"""
import uuid
import json
import time
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import SessionLocal
from app.models.tracking_config import TrackingConfig
from app.models.access_log import AccessLog
from app.models.user_session import UserSession
from app.utils.logger import get_logger

logger = get_logger("tracking")


class TrackingMiddleware(BaseHTTPMiddleware):
    """
    用户追踪中间件

    自动记录用户访问信息，包括：
    - 请求/响应信息
    - 设备信息（通过User-Agent解析）
    - 地理位置（可选）
    - 会话管理

    特性：
    - 异步记录，不阻塞响应
    - 支持配置化开关
    - IP匿名化支持
    - 内网IP排除
    - 异常处理，不影响正常请求
    """

    def __init__(self, app, geoip_path: str = None):
        """
        初始化追踪中间件

        Args:
            app: FastAPI应用实例
            geoip_path: GeoIP数据库路径（可选）
        """
        super().__init__(app)
        self.geoip_path = geoip_path
        self.geoip_reader = None

        # 尝试加载GeoIP数据库
        if geoip_path:
            try:
                import geoip2.database
                self.geoip_reader = geoip2.database.Reader(geoip_path)
                logger.info(f"GeoIP数据库已加载: {geoip_path}")
            except ImportError:
                logger.warning("geoip2库未安装，地理位置追踪将不可用")
            except Exception as e:
                logger.warning(f"GeoIP数据库加载失败: {e}")

    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录访问日志

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件/处理函数

        Returns:
            Response: HTTP响应
        """
        # 检查追踪配置
        config = await self._get_tracking_config()

        # 如果追踪被禁用，直接返回
        if not config or not config.enable_tracking:
            return await call_next(request)

        # 生成或获取设备ID（持久化 UUID）
        device_id = request.cookies.get("device_id")
        if not device_id:
            device_id = str(uuid.uuid4())
        request.state.device_id = device_id

        # 生成或获取会话ID
        session_id = self._get_or_create_session_id(request)
        request.state.session_id = session_id
        request.state.new_session = False

        # 检查是否是新会话
        if not request.cookies.get("session_id"):
            request.state.new_session = True

        # 游客指纹（多因素）
        if not getattr(request.state, "user_id", None):
            fp_raw = f"{self._get_client_ip(request)}|{request.headers.get('user-agent','')}|{request.headers.get('accept-language','')}"
            request.state.device_fingerprint = hashlib.sha256(fp_raw.encode()).hexdigest()[:16]

        # 记录开始时间
        start_time = time.time()

        try:
            # 处理请求
            response = await call_next(request)

            # 计算响应时间
            response_time = int((time.time() - start_time) * 1000)

            # 异步记录访问日志（不阻塞响应）
            # 创建新任务但不等待完成
            asyncio.create_task(
                self._log_access(request, response, response_time, config)
            )

            # 设置设备ID Cookie（持久化，1年）
            if not request.cookies.get("device_id"):
                response.set_cookie(
                    key="device_id", value=device_id,
                    max_age=86400 * 365, httponly=True,
                    samesite="lax", secure=settings.is_production(),
                )

            # 设置会话Cookie
            if getattr(request.state, "new_session", False):
                response.set_cookie(
                    key="session_id", value=session_id,
                    max_age=86400 * 30, httponly=True,
                    samesite="lax", secure=settings.is_production(),
                )

            return response

        except Exception as e:
            # 记录异常但不影响请求处理
            logger.error(f"追踪中间件处理请求时出错: {e}")
            # 继续处理请求
            return await call_next(request)

    async def _get_tracking_config(self) -> Optional[TrackingConfig]:
        """
        获取追踪配置

        Returns:
            TrackingConfig: 追踪配置对象，出错时返回None
        """
        db = SessionLocal()
        try:
            config = db.query(TrackingConfig).first()
            if not config:
                # 创建默认配置
                config = TrackingConfig()
                db.add(config)
                db.commit()
                db.refresh(config)
                logger.info("已创建默认追踪配置")
            return config
        except Exception as e:
            logger.error(f"获取追踪配置失败: {e}")
            return None
        finally:
            db.close()

    def _get_or_create_session_id(self, request: Request) -> str:
        """
        获取或创建会话ID

        Args:
            request: FastAPI请求对象

        Returns:
            str: 会话ID
        """
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        return str(uuid.uuid4())

    async def _log_access(
        self,
        request: Request,
        response,
        response_time: int,
        config: TrackingConfig
    ):
        """
        记录访问日志

        Args:
            request: FastAPI请求对象
            response: HTTP响应对象
            response_time: 响应时间（毫秒）
            config: 追踪配置
        """
        db = SessionLocal()
        try:
            # 获取IP地址
            ip = self._get_client_ip(request)

            # 检查是否排除的内网IP
            if config.should_exclude_ip(ip):
                logger.debug(f"IP {ip} 在排除列表中，跳过记录")
                return

            # 解析User-Agent
            user_agent_str = request.headers.get("user-agent", "")
            device_info = self._parse_user_agent(user_agent_str) if user_agent_str else {}

            # 解析地理位置
            location_info = {}
            if config.enable_location_tracking:
                location_info = self._get_location(ip, config)

            # 获取用户和设备信息
            user_id = getattr(request.state, "user_id", None)
            device_id = getattr(request.state, "device_id", "")
            fingerprint = getattr(request.state, "device_fingerprint", "")

            # 匿名化IP
            if config.anonymize_ip:
                ip = self._anonymize_ip(ip)

            # 创建访问日志
            log = AccessLog(
                timestamp=datetime.utcnow().isoformat() + "Z",
                user_id=user_id,
                is_authenticated=1 if user_id else 0,
                ip_address=ip,
                ip_country=location_info.get("country"),
                ip_city=location_info.get("city"),
                ip_isp=location_info.get("isp"),
                ip_asn=location_info.get("asn"),
                user_agent=user_agent_str[:500] if user_agent_str else None,
                device_type=device_info.get("device_type"),
                device_brand=device_info.get("device_brand"),
                device_model=device_info.get("device_model"),
                os_name=device_info.get("os_name"),
                os_version=device_info.get("os_version"),
                browser_name=device_info.get("browser_name"),
                browser_version=device_info.get("browser_version"),
                screen_resolution=device_info.get("screen_resolution"),
                request_method=request.method,
                request_path=str(request.url.path),
                request_query=str(request.url.query) if request.url.query else None,
                referer=request.headers.get("referer"),
                response_status=response.status_code,
                response_time_ms=response_time,
                session_id=request.state.session_id,
                raw_data=json.dumps({
                    "headers": dict(request.headers),
                    "path_params": dict(request.path_params) if hasattr(request, "path_params") else {},
                }) if config.enable_behavior_tracking else None
            )

            db.add(log)
            db.commit()

            # 更新会话统计
            self._update_session(db, request, user_id, device_info)

            logger.debug(f"访问日志已记录: {request.method} {request.url.path}")

        except Exception as e:
            logger.error(f"记录访问日志失败: {e}")
            db.rollback()
        finally:
            db.close()

    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端真实IP

        优先从代理头获取，其次从直接连接获取。

        Args:
            request: FastAPI请求对象

        Returns:
            str: IP地址
        """
        # 优先从代理头获取
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    def _anonymize_ip(self, ip: str) -> str:
        """
        匿名化IP地址

        IPv4保留前3段，IPv6保留前4段。

        Args:
            ip: IP地址

        Returns:
            str: 匿名化后的IP
        """
        if "." in ip:  # IPv4
            parts = ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
        elif ":" in ip:  # IPv6
            parts = ip.split(":")
            if len(parts) >= 4:
                return ":".join(parts[:4]) + ":xxxx:xxxx:xxxx"
        return ip

    def _get_location(self, ip: str, config: TrackingConfig) -> Dict[str, Any]:
        """
        获取地理位置信息

        Args:
            ip: IP地址
            config: 追踪配置

        Returns:
            dict: 地理位置信息
        """
        if not config.enable_location_tracking or not self.geoip_reader:
            return {}

        try:
            response = self.geoip_reader.city(ip)
            return {
                "country": response.country.iso_code,
                "city": response.city.name,
                "isp": getattr(response.traits, "isp", None),
                "asn": str(response.traits.autonomous_system_number) if response.traits.autonomous_system_number else None
            }
        except Exception:
            # 忽略GeoIP查询错误
            return {}

    def _parse_user_agent(self, user_agent_str: str) -> Dict[str, Any]:
        """
        解析User-Agent字符串

        Args:
            user_agent_str: User-Agent字符串

        Returns:
            dict: 设备信息
        """
        try:
            from user_agents import parse
            ua = parse(user_agent_str)

            device_type = "unknown"
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            elif ua.is_pc:
                device_type = "desktop"

            return {
                "device_type": device_type,
                "device_brand": ua.device.brand,
                "device_model": ua.device.model,
                "os_name": ua.os.family,
                "os_version": ua.os.version_string,
                "browser_name": ua.browser.family,
                "browser_version": ua.browser.version_string,
                "screen_resolution": None,  # 无法从User-Agent获取
            }
        except ImportError:
            logger.debug("user_agents库未安装，使用简单解析")
            return self._simple_user_agent_parse(user_agent_str)
        except Exception as e:
            logger.warning(f"User-Agent解析失败: {e}")
            return {"device_type": "unknown"}

    def _simple_user_agent_parse(self, user_agent_str: str) -> Dict[str, Any]:
        """
        简单User-Agent解析（备用方案）

        Args:
            user_agent_str: User-Agent字符串

        Returns:
            dict: 基础设备信息
        """
        ua_lower = user_agent_str.lower()

        # 检测设备类型
        device_type = "unknown"
        if "mobile" in ua_lower or "android" in ua_lower and "tablet" not in ua_lower:
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"
        elif "windows" in ua_lower or "macintosh" in ua_lower or "linux" in ua_lower:
            device_type = "desktop"

        # 检测操作系统
        os_name = "unknown"
        if "windows" in ua_lower:
            os_name = "Windows"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            os_name = "macOS"
        elif "linux" in ua_lower:
            os_name = "Linux"
        elif "android" in ua_lower:
            os_name = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            os_name = "iOS"

        # 检测浏览器
        browser_name = "unknown"
        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser_name = "Chrome"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser_name = "Safari"
        elif "firefox" in ua_lower:
            browser_name = "Firefox"
        elif "edg" in ua_lower:
            browser_name = "Edge"

        # 提取设备型号（从 UA 中匹配）
        device_model = None
        import re
        if "iphone" in ua_lower:
            device_brand = "Apple"
            m = re.search(r'iphone(\d+),?(\d+)?', ua_lower)
            device_model = f"iPhone{m.group(1)}" if m else "iPhone"
        elif "ipad" in ua_lower:
            device_brand = "Apple"
            device_model = "iPad"
        elif "android" in ua_lower:
            m = re.search(r';\s*([^;]+?)\s*build', ua_lower)
            device_model = m.group(1).strip() if m else None
            m2 = re.search(r';\s*([a-zA-Z0-9\s\-]+?)\)', ua_lower)
            if not device_model and m2:
                device_model = m2.group(1).strip()
            device_brand = device_model.split()[0] if device_model else None
        elif "windows" in ua_lower:
            device_brand = "Microsoft"
            device_model = "PC"
        elif "mac" in ua_lower:
            device_brand = "Apple"
            device_model = "Mac"
        else:
            device_brand = None

        return {
            "device_type": device_type,
            "device_brand": device_brand,
            "device_model": device_model,
            "os_name": os_name,
            "os_version": None,
            "browser_name": browser_name,
            "browser_version": None,
            "screen_resolution": None,
        }

    def _update_session(
        self,
        db: SessionLocal,
        request: Request,
        user_id: str,
        device_info: Dict[str, Any]
    ):
        """
        更新会话统计

        Args:
            db: 数据库会话
            request: FastAPI请求对象
            user_id: 用户ID
            device_info: 设备信息
        """
        try:
            session = db.query(UserSession).filter(
                UserSession.session_id == request.state.session_id
            ).first()

            ip = self._get_client_ip(request)

            if session:
                # 更新现有会话
                session.update_last_seen(ip)
                session.increment_page_view()
                if user_id and not session.user_id:
                    session.user_id = user_id
            else:
                # 创建新会话
                user_agent = request.headers.get("user-agent", "")
                session = UserSession.create_session(
                    session_id=request.state.session_id,
                    user_id=user_id,
                    ip=ip,
                    user_agent=user_agent,
                    device_info=device_info,
                )
                db.add(session)

            db.commit()

        except Exception as e:
            logger.error(f"更新会话统计失败: {e}")
            db.rollback()
