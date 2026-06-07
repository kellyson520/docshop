"""
错误处理中间件测试

测试覆盖率目标：100%
- __call__ 异常捕获
- _handle_exception 各种异常处理
- _create_error_response 错误响应构建
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.middlewares.error_handler import ErrorHandlerMiddleware, RequestValidationErrorHandler
from app.exceptions import DocDistException, ValidationError, ResourceNotFound


class MockHeaders:
    """模拟请求头对象"""
    def __init__(self, headers=None):
        self._headers = headers or {}
    
    def get(self, key, default=None):
        return self._headers.get(key.lower(), default)


class MockRequest:
    """模拟请求对象"""
    def __init__(self):
        self.url = MagicMock()
        self.url.path = "/api/v1/test"
        self.method = "GET"
        self.headers = MockHeaders()
        self.client = MagicMock()
        self.client.host = "127.0.0.1"


class TestErrorHandlerMiddleware:
    """ErrorHandlerMiddleware 测试"""

    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """测试正常请求处理"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        response = MagicMock()
        
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_business_exception(self):
        """测试业务异常处理"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        exc = ValidationError(message="Invalid input", field="name")
        
        call_next = AsyncMock(side_effect=exc)
        
        result = await middleware.dispatch(request, call_next)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_dispatch_system_exception(self):
        """测试系统异常处理"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        exc = Exception("System error")
        
        call_next = AsyncMock(side_effect=exc)
        
        result = await middleware.dispatch(request, call_next)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_handle_business_exception(self):
        """测试处理业务异常"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        exc = ValidationError(message="Invalid input", field="name")
        
        with patch("app.middlewares.error_handler.logger") as mock_logger:
            result = await middleware._handle_business_exception(request, exc, 0.0)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == status.HTTP_400_BAD_REQUEST
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_business_exception_with_traceback(self):
        """测试带堆栈跟踪的业务异常"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app, include_traceback=True)
        
        request = MockRequest()
        exc = ValidationError(message="Invalid input", field="name", details={"extra": "info"})
        
        result = await middleware._handle_business_exception(request, exc, 0.0)
        
        assert isinstance(result, JSONResponse)
        body = result.body.decode()
        assert "details" in body

    @pytest.mark.asyncio
    async def test_handle_system_exception(self):
        """测试处理系统异常"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        exc = Exception("System error")
        
        with patch("app.middlewares.error_handler.error_logger") as mock_logger:
            result = await middleware._handle_system_exception(request, exc, 0.0)
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_system_exception_with_traceback(self):
        """测试带堆栈跟踪的系统异常"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app, include_traceback=True)
        
        request = MockRequest()
        exc = ValueError("Test error")
        
        result = await middleware._handle_system_exception(request, exc, 0.0)
        
        assert isinstance(result, JSONResponse)
        body = result.body.decode()
        assert "debug" in body

    def test_get_client_host_from_forwarded(self):
        """测试从X-Forwarded-For获取客户端主机"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        request.headers = MockHeaders({"x-forwarded-for": "192.168.1.1, 10.0.0.1"})
        
        result = middleware._get_client_host(request)
        
        assert result == "192.168.1.1"

    def test_get_client_host_from_real_ip(self):
        """测试从X-Real-IP获取客户端主机"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        request.headers = MockHeaders({"x-real-ip": "192.168.1.2"})
        
        result = middleware._get_client_host(request)
        
        assert result == "192.168.1.2"

    def test_get_client_host_from_client(self):
        """测试从request.client获取客户端主机"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        request.headers = MockHeaders({})
        request.client.host = "192.168.1.3"
        
        result = middleware._get_client_host(request)
        
        assert result == "192.168.1.3"

    def test_get_client_host_unknown(self):
        """测试未知客户端主机"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        request.headers = MockHeaders({})
        request.client = None
        
        result = middleware._get_client_host(request)
        
        assert result == "unknown"

    def test_get_client_host_exception(self):
        """测试获取客户端主机异常"""
        app = MagicMock()
        middleware = ErrorHandlerMiddleware(app)
        
        request = MockRequest()
        request.headers = MockHeaders({"x-forwarded-for": "192.168.1.1"})
        
        # 模拟 headers.get 抛出异常
        def raise_exception(*args, **kwargs):
            raise Exception("Header error")
        
        request.headers.get = raise_exception
        result = middleware._get_client_host(request)
        
        assert result == "unknown"


class TestRequestValidationErrorHandler:
    """RequestValidationErrorHandler 测试"""

    def test_format_validation_errors(self):
        """测试格式化验证错误"""
        errors = [
            {
                "loc": ["body", "name"],
                "msg": "field required",
                "type": "value_error.missing"
            },
            {
                "loc": ["body", "email"],
                "msg": "invalid email format",
                "type": "value_error.email"
            }
        ]
        
        result = RequestValidationErrorHandler.format_validation_errors(errors)
        
        assert result["code"] == 40001
        assert result["message"] == "请求参数校验失败"
        assert len(result["errors"]) == 2
        assert result["errors"][0]["field"] == "body.name"
        assert result["errors"][0]["message"] == "field required"

    def test_format_validation_errors_empty(self):
        """测试格式化空验证错误"""
        errors = []
        
        result = RequestValidationErrorHandler.format_validation_errors(errors)
        
        assert result["code"] == 40001
        assert result["message"] == "请求参数校验失败"
        assert len(result["errors"]) == 0

    def test_format_validation_errors_nested(self):
        """测试格式化嵌套验证错误"""
        errors = [
            {
                "loc": ["body", "address", "street"],
                "msg": "field required",
                "type": "value_error.missing"
            }
        ]
        
        result = RequestValidationErrorHandler.format_validation_errors(errors)
        
        assert result["errors"][0]["field"] == "body.address.street"
