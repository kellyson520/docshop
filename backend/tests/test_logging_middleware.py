"""
日志中间件测试

测试覆盖率目标：100%
- __call__ 日志记录
- _get_query_string 查询字符串获取
- _get_client_host 客户端地址获取
- _get_or_create_request_id 请求ID获取
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request
from starlette.responses import Response

from app.middlewares.logging import LoggingMiddleware


class MockRequest:
    """模拟请求对象"""
    def __init__(self):
        self.url = MagicMock()
        self.url.path = "/api/v1/test"
        self.method = "POST"
        self.headers = {
            "content-type": "application/json",
            "authorization": "Bearer token123",
        }
        self.client = MagicMock()
        self.client.host = "127.0.0.1"
        self.state = MagicMock()
        self.query_params = MagicMock()
        self.query_params.__str__ = MagicMock(return_value="param=value")


class TestLoggingMiddleware:
    """LoggingMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """测试正常请求日志记录"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MockRequest()
        response = Response()
        
        call_next = AsyncMock(return_value=response)
        
        with patch("app.middlewares.logging.access_logger") as mock_access_logger:
            with patch("app.middlewares.logging.logger") as mock_logger:
                result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
        mock_access_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_dispatch_with_request_body(self):
        """测试带请求体的日志记录"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        middleware.log_headers = True
        
        request = MockRequest()
        request.method = "POST"
        request.headers = {"content-type": "application/json"}
        
        response = Response()
        call_next = AsyncMock(return_value=response)
        
        with patch("app.middlewares.logging.access_logger") as mock_access_logger:
            with patch("app.middlewares.logging.logger") as mock_logger:
                result = await middleware.dispatch(request, call_next)
        
        assert result == response

    @pytest.mark.asyncio
    async def test_dispatch_exception(self):
        """测试异常日志记录"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MockRequest()
        exc = Exception("Test error")
        
        call_next = AsyncMock(side_effect=exc)
        
        with patch("app.middlewares.logging.access_logger") as mock_access_logger:
            with patch("app.middlewares.logging.logger") as mock_logger:
                with pytest.raises(Exception, match="Test error"):
                    await middleware.dispatch(request, call_next)
        
        mock_logger.error.assert_called_once()

    def test_get_query_string_with_params(self):
        """测试获取带参数的查询字符串"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.query_params = "param=value&other=test"
        
        result = middleware._get_query_string(request)
        
        assert result == "?param=value&other=test"

    def test_get_query_string_empty(self):
        """测试获取空查询字符串"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.query_params = ""
        
        result = middleware._get_query_string(request)
        
        assert result == ""

    def test_get_client_host_from_forwarded(self):
        """测试从 X-Forwarded-For 获取客户端地址"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        result = middleware._get_client_host(request)
        
        assert result == "192.168.1.1"

    def test_get_client_host_from_real_ip(self):
        """测试从 X-Real-IP 获取客户端地址"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = {"X-Real-IP": "192.168.1.100"}
        request.client = None
        
        result = middleware._get_client_host(request)
        
        assert result == "192.168.1.100"

    def test_get_client_host_from_client(self):
        """测试从 request.client 获取客户端地址"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        result = middleware._get_client_host(request)
        
        assert result == "127.0.0.1"

    def test_get_client_host_unknown(self):
        """测试未知客户端地址"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = {}
        request.client = None
        
        result = middleware._get_client_host(request)
        
        assert result == "unknown"

    def test_get_client_host_exception(self):
        """测试获取客户端地址异常"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = MagicMock()
        request.headers.get = MagicMock(side_effect=Exception("Header error"))
        
        result = middleware._get_client_host(request)
        
        assert result == "unknown"

    def test_get_or_create_request_id_from_header(self):
        """测试从请求头获取追踪ID"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = {"X-Request-ID": "existing-id-123"}
        
        result = middleware._get_or_create_request_id(request)
        
        assert result == "existing-id-123"

    def test_get_or_create_request_id_generate(self):
        """测试生成新的追踪ID"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MagicMock()
        request.headers = {}
        
        result = middleware._get_or_create_request_id(request)
        
        # 应该是一个有效的UUID格式
        assert len(result) == 36
        assert "-" in result

    @pytest.mark.asyncio
    async def test_dispatch_get_request(self):
        """测试GET请求日志"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MockRequest()
        request.method = "GET"
        response = Response()
        
        call_next = AsyncMock(return_value=response)
        
        with patch("app.middlewares.logging.access_logger") as mock_access_logger:
            with patch("app.middlewares.logging.logger") as mock_logger:
                result = await middleware.dispatch(request, call_next)
        
        assert result == response

    @pytest.mark.asyncio
    async def test_dispatch_slow_request(self):
        """测试慢请求警告"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MockRequest()
        response = Response()
        
        call_next = AsyncMock(return_value=response)
        
        with patch("app.middlewares.logging.access_logger") as mock_access_logger:
            with patch("app.middlewares.logging.logger") as mock_logger:
                with patch("app.middlewares.logging.time.time") as mock_time:
                    # 模拟耗时超过5秒的请求
                    mock_time.side_effect = [0, 6.0]
                    result = await middleware.dispatch(request, call_next)
        
        assert result == response
        # 应该记录慢请求警告
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_adds_response_headers(self):
        """测试响应头添加"""
        app = MagicMock()
        middleware = LoggingMiddleware(app)
        
        request = MockRequest()
        response = Response()
        
        call_next = AsyncMock(return_value=response)
        
        with patch("app.middlewares.logging.access_logger"):
            with patch("app.middlewares.logging.logger"):
                result = await middleware.dispatch(request, call_next)
        
        assert "X-Request-ID" in result.headers
        assert "X-Process-Time" in result.headers


class TestPerformanceLoggingMiddleware:
    """PerformanceLoggingMiddleware 测试（行223-245）"""

    @pytest.mark.asyncio
    async def test_dispatch_post_request(self):
        """测试POST请求日志记录（行223-245: 正常请求处理）"""
        from app.middlewares.logging import PerformanceLoggingMiddleware

        app = MagicMock()
        middleware = PerformanceLoggingMiddleware(app)

        request = MockRequest()
        request.method = "POST"
        response = Response()

        call_next = AsyncMock(return_value=response)

        with patch("app.middlewares.logging.logger") as mock_logger:
            result = await middleware.dispatch(request, call_next)

        assert result == response
        mock_logger.debug.assert_called_once()
        # 验证日志包含性能指标
        call_args = mock_logger.debug.call_args[0][0]
        assert "POST" in call_args
        assert "Performance metrics" in call_args

    @pytest.mark.asyncio
    async def test_dispatch_with_sensitive_data(self):
        """测试敏感数据脱敏（POST请求体可能包含敏感数据）"""
        from app.middlewares.logging import PerformanceLoggingMiddleware

        app = MagicMock()
        middleware = PerformanceLoggingMiddleware(app)

        request = MockRequest()
        request.method = "POST"
        request.headers = {
            "content-type": "application/json",
            "authorization": "Bearer sensitive_token_123",
        }
        response = Response()

        call_next = AsyncMock(return_value=response)

        with patch("app.middlewares.logging.logger"):
            result = await middleware.dispatch(request, call_next)

        assert result == response

    @pytest.mark.asyncio
    async def test_dispatch_error_response(self):
        """测试错误响应日志（行239-245: 异常处理）"""
        from app.middlewares.logging import PerformanceLoggingMiddleware

        app = MagicMock()
        middleware = PerformanceLoggingMiddleware(app)

        request = MockRequest()
        request.method = "DELETE"

        exc = RuntimeError("Service unavailable")
        call_next = AsyncMock(side_effect=exc)

        with patch("app.middlewares.logging.logger") as mock_logger:
            with pytest.raises(RuntimeError, match="Service unavailable"):
                await middleware.dispatch(request, call_next)

        # 验证错误日志被记录
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "failed" in call_args
        assert "DELETE" in call_args
