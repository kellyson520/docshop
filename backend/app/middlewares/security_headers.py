"""
安全头中间件。

为响应附加安全相关 HTTP 头。普通页面默认禁止被 iframe 嵌入；
文件预览相关响应允许同源嵌入，其中 HTML 预览额外允许内联脚本，
以支持站内预览播放器与交互式 HTML 文件。
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils.logger import get_logger
from app.utils.request_scheme import is_https_request

security_logger = get_logger("middlewares.security_headers")


def _is_preview_embed_request(path: str) -> bool:
    normalized = (path or "").lower()
    return (
        normalized.endswith("/preview")
        or "/preview?" in normalized
        or "/preview/pdf" in normalized
        or "/pages/" in normalized
        or "/preview-assets/" in normalized
    )


def _default_csp() -> str:
    return (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self' https://cdn.jsdelivr.net; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )


def _preview_embed_csp(*, allow_inline_scripts: bool) -> str:
    script_src = "script-src 'self' https://cdn.jsdelivr.net;"
    if allow_inline_scripts:
        script_src = "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"

    return (
        "default-src 'self' data: blob: https:; "
        f"{script_src} "
        "style-src 'self' 'unsafe-inline' https:; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data: https:; "
        "media-src 'self' data: blob: https:; "
        "connect-src 'self' data: blob: https:; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        security_logger.info("安全头中间件已初始化")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        is_https = is_https_request(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet, noimageindex"
        if is_https:
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        is_preview_embed_request = _is_preview_embed_request(request.url.path)
        content_type = str(response.headers.get("content-type", "")).lower()
        is_html_preview_response = is_preview_embed_request and content_type.startswith("text/html")

        response.headers["X-Frame-Options"] = "SAMEORIGIN" if is_preview_embed_request else "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            _preview_embed_csp(
                allow_inline_scripts=is_html_preview_response,
            )
            if is_preview_embed_request
            else _default_csp()
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=(), "
            "ch-ua-model=(self), "
            "ch-ua-platform-version=(self), "
            "ch-ua-arch=(self), "
            "ch-ua-bitness=(self)"
        )
        response.headers["Accept-CH"] = (
            "Sec-CH-UA-Model, Sec-CH-UA-Platform-Version, "
            "Sec-CH-UA-Arch, Sec-CH-UA-Bitness"
        )

        if is_html_preview_response:
            response.headers["Cache-Control"] = "private, no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"

        if settings.is_production() and is_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
