"""
安全头中间件测试

测试 security_headers.py 中的功能，包括安全头的存在性、
HSTS 头在不同环境下的行为和 CSP 头内容等。
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.middlewares.security_headers import SecurityHeadersMiddleware


# ===== 辅助函数：创建模拟请求和响应 =====

def _create_mock_request(*, scheme="http", forwarded_proto=None):
    """创建模拟请求对象"""
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/test"
    mock_request.url.scheme = scheme
    mock_request.headers = {}
    if forwarded_proto is not None:
        mock_request.headers["x-forwarded-proto"] = forwarded_proto
    return mock_request


def _create_mock_response():
    """创建模拟响应对象"""
    mock_response = MagicMock()
    mock_response.headers = {'content-type': 'application/json'}
    return mock_response


async def _call_middleware(
    middleware,
    *,
    path="/api/v1/test",
    content_type="application/json",
    scheme="http",
    forwarded_proto=None,
):
    """
    辅助函数：调用中间件并返回响应

    Args:
        middleware: 安全头中间件实例

    Returns:
        模拟响应对象（已添加安全头）
    """
    mock_request = _create_mock_request(scheme=scheme, forwarded_proto=forwarded_proto)
    mock_request.url.path = path
    mock_response = _create_mock_response()
    mock_response.headers['content-type'] = content_type
    call_next = AsyncMock(return_value=mock_response)

    response = await middleware.dispatch(mock_request, call_next)
    return response


# ===== test_security_headers_present: 测试所有安全头都存在 =====

class TestSecurityHeadersPresent:
    """测试所有必需的安全头都存在"""

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """
        测试所有安全头都存在：中间件应为每个响应添加以下安全头：
        - X-Content-Type-Options
        - X-Frame-Options
        - X-XSS-Protection
        - Content-Security-Policy
        - Referrer-Policy
        - Permissions-Policy
        """
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware, scheme="https")

        # 验证所有安全头都存在
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_x_content_type_options(self):
        """测试 X-Content-Type-Options 头的值"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware, scheme="https")

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options(self):
        """测试 X-Frame-Options 头的值"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_x_xss_protection(self):
        """测试 X-XSS-Protection 头的值"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_referrer_policy(self):
        """测试 Referrer-Policy 头的值"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


# ===== test_hsts_in_production: 测试生产环境包含HSTS头 =====

class TestHstsInProduction:
    """测试生产环境下的 HSTS 头"""

    @pytest.mark.asyncio
    async def test_hsts_in_production(self):
        """
        测试生产环境包含HSTS头：当 is_production() 返回 True 时，
        响应应包含 Strict-Transport-Security 头。
        """
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = True

            response = await _call_middleware(middleware, scheme="https")

        # 生产环境应包含 HSTS 头
        assert "Strict-Transport-Security" in response.headers
        hsts_value = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts_value
        assert "includeSubDomains" in hsts_value
        assert "preload" in hsts_value


# ===== test_no_hsts_in_development: 测试开发环境不包含HSTS头 =====

class TestNoHstsInDevelopment:
    """测试开发环境下不包含 HSTS 头"""

    @pytest.mark.asyncio
    async def test_no_hsts_in_development(self):
        """
        测试开发环境不包含HSTS头：当 is_production() 返回 False 时，
        响应不应包含 Strict-Transport-Security 头。
        """
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        # 开发环境不应包含 HSTS 头
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_no_hsts_for_plain_http_even_in_production(self):
        """生产环境下的纯 HTTP 请求也不应包含 HSTS。"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = True

            response = await _call_middleware(middleware, scheme="http")

        assert "Strict-Transport-Security" not in response.headers


# ===== test_csp_header: 测试CSP头内容 =====

class TestCspHeader:
    """测试 Content-Security-Policy 头内容"""

    @pytest.mark.asyncio
    async def test_csp_header(self):
        """
        测试CSP头内容：Content-Security-Policy 头应包含必要的安全指令，
        包括 default-src、script-src、style-src、img-src 等。
        """
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        csp = response.headers["Content-Security-Policy"]

        # 验证 CSP 包含必要的安全指令
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp
        assert "img-src 'self'" in csp
        assert "font-src 'self'" in csp
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp

    @pytest.mark.asyncio
    async def test_csp_style_allows_unsafe_inline(self):
        """测试CSP允许内联样式：style-src 应包含 'unsafe-inline'"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in csp

    @pytest.mark.asyncio
    async def test_csp_img_allows_data(self):
        """测试CSP允许 data URI 图片：img-src 应包含 'data:'"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        csp = response.headers["Content-Security-Policy"]
        assert "img-src 'self' data:" in csp

    @pytest.mark.asyncio
    async def test_permissions_policy(self):
        """测试 Permissions-Policy 头：应禁用摄像头、麦克风等敏感权限"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware)

        pp = response.headers["Permissions-Policy"]

        # 验证敏感权限都被禁用
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp
        assert "payment=()" in pp

    @pytest.mark.asyncio
    async def test_html_preview_allows_same_origin_iframe_and_inline_scripts(self):
        """HTML 预览需要允许同源 iframe 与内联脚本执行。"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(
                middleware,
                path="/api/v1/files/file-1/preview",
                content_type="text/html; charset=utf-8",
            )

        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp

    @pytest.mark.asyncio
    async def test_html_preview_disables_cache_without_adding_nested_csp_sandbox(self):
        """HTML 预览应加 sandbox 并禁止浏览器持久缓存。"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(
                middleware,
                path="/api/v1/files/file-1/preview",
                content_type="text/html; charset=utf-8",
            )

        csp = response.headers["Content-Security-Policy"]
        assert "sandbox " not in csp
        assert response.headers["Cache-Control"] == "private, no-store, max-age=0"
        assert response.headers["Pragma"] == "no-cache"

    @pytest.mark.asyncio
    async def test_global_security_headers_add_anti_index_and_https_cross_origin_guards(self):
        """HTTPS 响应应带基础反索引和跨源隔离头。"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = False

            response = await _call_middleware(middleware, scheme="https")

        assert response.headers["X-Robots-Tag"] == "noindex, nofollow, noarchive, nosnippet, noimageindex"
        assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
        assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"

    @pytest.mark.asyncio
    async def test_http_request_omits_cross_origin_isolation_headers(self):
        """HTTP 请求不应返回 COOP/CORP，避免浏览器 ignored 警告。"""
        middleware = SecurityHeadersMiddleware(app=MagicMock())

        with patch("app.middlewares.security_headers.settings") as mock_settings:
            mock_settings.is_production.return_value = True

            response = await _call_middleware(middleware, scheme="http")

        assert response.headers["X-Robots-Tag"] == "noindex, nofollow, noarchive, nosnippet, noimageindex"
        assert "Cross-Origin-Opener-Policy" not in response.headers
        assert "Cross-Origin-Resource-Policy" not in response.headers
