"""
错误处理中间件

统一处理应用中抛出的所有异常，将异常转换为标准响应格式。
支持自定义业务异常和未知系统异常的不同处理方式。
"""

import traceback
import time
from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils.logger import logger, error_logger
from app.exceptions import DocDistException, get_http_status
from app.schemas.response import ApiResponse


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    全局错误处理中间件
    
    捕获所有未处理的异常，统一返回标准格式的错误响应。
    区分已知业务异常和未知系统异常，分别记录日志。
    
    Attributes:
        include_traceback: 是否在响应中包含堆栈跟踪（仅开发环境）
    """
    
    def __init__(self, app, include_traceback: bool = False):
        """
        初始化错误处理中间件
        
        Args:
            app: FastAPI 应用实例
            include_traceback: 是否在错误响应中包含堆栈跟踪
        """
        super().__init__(app)
        self.include_traceback = include_traceback
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并捕获异常
        
        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            Response: HTTP 响应对象
        """
        start_time = time.time()
        
        try:
            # 正常处理请求
            response = await call_next(request)
            return response
            
        except DocDistException as exc:
            # 处理已知业务异常
            return await self._handle_business_exception(request, exc, start_time)
            
        except Exception as exc:
            # 处理未知系统异常
            return await self._handle_system_exception(request, exc, start_time)
    
    async def _handle_business_exception(
        self, 
        request: Request, 
        exc: DocDistException,
        start_time: float
    ) -> JSONResponse:
        """
        处理已知业务异常
        
        记录警告日志，返回包含错误码的标准响应。
        
        Args:
            request: HTTP 请求对象
            exc: 业务异常实例
            start_time: 请求开始时间
            
        Returns:
            JSONResponse: 错误响应
        """
        process_time = time.time() - start_time
        
        # 获取客户端信息
        client_host = self._get_client_host(request)
        
        # 记录警告日志
        logger.warning(
            f"Business exception - {request.method} {request.url.path} - "
            f"Code: {exc.code}, Message: {exc.message}, "
            f"Client: {client_host}, Time: {process_time:.3f}s"
        )
        
        # 构建响应
        http_status = get_http_status(exc.code)
        response_data = ApiResponse(
            code=exc.code,
            message=exc.message,
            data=None
        )
        
        # 开发环境可包含详细错误信息
        if self.include_traceback and exc.details:
            response_content = response_data.model_dump()
            response_content["details"] = exc.details
        else:
            response_content = response_data.model_dump()
        
        return JSONResponse(
            status_code=http_status,
            content=response_content
        )
    
    async def _handle_system_exception(
        self, 
        request: Request, 
        exc: Exception,
        start_time: float
    ) -> JSONResponse:
        """
        处理未知系统异常
        
        记录详细错误日志（包含堆栈跟踪），返回通用错误响应。
        
        Args:
            request: HTTP 请求对象
            exc: 系统异常实例
            start_time: 请求开始时间
            
        Returns:
            JSONResponse: 错误响应
        """
        process_time = time.time() - start_time
        
        # 获取客户端信息
        client_host = self._get_client_host(request)
        
        # 获取堆栈跟踪
        error_trace = traceback.format_exc()
        
        # 记录详细错误日志
        error_logger.error(
            f"Unhandled exception - {request.method} {request.url.path}\n"
            f"Client: {client_host}\n"
            f"Time: {process_time:.3f}s\n"
            f"Exception: {type(exc).__name__}: {str(exc)}\n"
            f"Traceback:\n{error_trace}"
        )
        
        # 构建响应
        response_data = ApiResponse(
            code=99999,
            message="服务器内部错误",
            data=None
        )
        
        response_content = response_data.model_dump()
        
        # 仅开发环境可包含堆栈跟踪（双重保护：ENVIRONMENT + include_traceback）
        if self.include_traceback and not settings.is_production():
            response_content["debug"] = {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "traceback": error_trace.split("\n")
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_content
        )
    
    def _get_client_host(self, request: Request) -> str:
        """
        获取客户端主机地址
        
        优先从 X-Forwarded-For 头获取（支持代理），
        否则使用直接连接的客户端地址。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            str: 客户端主机地址
        """
        try:
            # 检查代理头
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # 取第一个地址（原始客户端）
                return forwarded_for.split(",")[0].strip()
            
            # 检查 X-Real-IP 头
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip
            
            # 使用直接连接的客户端地址
            if request.client:
                return request.client.host
            
            return "unknown"
            
        except Exception as e:
            logger.warning(f"Failed to get client host: {e}")
            return "unknown"


class RequestValidationErrorHandler:
    """
    请求参数校验错误处理器
    
    处理 Pydantic 参数校验失败的情况，返回友好的错误信息。
    """
    
    @staticmethod
    def format_validation_errors(errors: list) -> dict:
        """
        格式化校验错误信息
        
        Args:
            errors: Pydantic 错误列表
            
        Returns:
            dict: 格式化后的错误信息
        """
        formatted_errors = []
        
        for error in errors:
            location = ".".join(str(loc) for loc in error.get("loc", []))
            msg = error.get("msg", "")
            error_type = error.get("type", "")
            
            formatted_errors.append({
                "field": location,
                "message": msg,
                "type": error_type
            })
        
        return {
            "code": 40001,
            "message": "请求参数校验失败",
            "errors": formatted_errors
        }
