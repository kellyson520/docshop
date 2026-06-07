"""
安全头中间件

为所有响应添加安全相关的 HTTP 头，防御常见的 Web 攻击。
包括 X-Content-Type-Options、X-Frame-Options、CSP、HSTS 等。
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils.logger import get_logger

# 获取模块日志器
security_logger = get_logger("middlewares.security_headers")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头中间件

    为所有 HTTP 响应添加标准安全头，包括：
    - X-Content-Type-Options: 防止 MIME 类型嗅探
    - X-Frame-Options: 防止点击劫持
    - X-XSS-Protection: 启用浏览器 XSS 过滤
    - Content-Security-Policy: 内容安全策略
    - Referrer-Policy: 引用策略控制
    - Permissions-Policy: 权限策略控制
    - Strict-Transport-Security: 强制 HTTPS（仅生产环境）
    """

    def __init__(self, app):
        """
        初始化安全头中间件

        Args:
            app: FastAPI 应用实例
        """
        super().__init__(app)
        security_logger.info("安全头中间件已初始化")

    async def dispatch(self, request: Request, call_next):
        """
        处理请求并添加安全响应头

        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 添加了安全头的 HTTP 响应对象
        """
        response = await call_next(request)

        # X-Content-Type-Options: 防止浏览器猜测（嗅探）MIME 类型
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: 禁止页面被嵌入到 iframe 中（防止点击劫持）
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection: 启用浏览器内置的 XSS 过滤器
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content-Security-Policy: 限制页面可以加载的资源来源
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Referrer-Policy: 控制 Referer 头的发送策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: 限制浏览器功能的使用权限
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Strict-Transport-Security: 仅在生产环境启用，强制使用 HTTPS
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
