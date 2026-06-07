"""
安全头中间件测试

测试 security_headers.py 中的功能，包括安全头的存在性、
HSTS 头在不同环境下的行为和 CSP 头内容等。
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.middlewares.security_headers import SecurityHeadersMiddleware


# ===== 辅助函数：创建模拟请求和响应 =====

def _create_mock_request():
    """创建模拟请求对象"""
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/test"
    return mock_request


def _create_mock_response():
    """创建模拟响应对象"""
    mock_response = MagicMock()
    mock_response.headers = {}
    return mock_response


async def _call_middleware(middleware):
    """
    辅助函数：调用中间件并返回响应

    Args:
        middleware: 安全头中间件实例

    Returns:
        模拟响应对象（已添加安全头）
    """
    mock_request = _create_mock_request()
    mock_response = _create_mock_response()
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

            response = await _call_middleware(middleware)

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

            response = await _call_middleware(middleware)

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

            response = await _call_middleware(middleware)

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
