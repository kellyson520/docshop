"""
日志记录中间件

记录所有 HTTP 请求的访问日志，包括请求信息、响应状态和处理时间。
支持请求追踪 ID，便于日志关联和问题排查。
"""

import time
import uuid
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import access_logger, logger, get_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志记录中间件
    
    记录所有 HTTP 请求的详细信息，包括：
    - 请求方法、路径、查询参数
    - 客户端 IP 地址
    - 请求头信息（可选）
    - 响应状态码
    - 处理时间
    - 请求追踪 ID
    
    Attributes:
        log_request_body: 是否记录请求体（谨慎使用，可能包含敏感信息）
        log_headers: 是否记录请求头
    """
    
    def __init__(
        self, 
        app, 
        log_request_body: bool = False,
        log_headers: bool = False
    ):
        """
        初始化日志中间件
        
        Args:
            app: FastAPI 应用实例
            log_request_body: 是否记录请求体
            log_headers: 是否记录请求头
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_headers = log_headers
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录日志
        
        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            Response: HTTP 响应对象
        """
        # 生成请求追踪 ID
        request_id = self._get_or_create_request_id(request)
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取客户端信息
        client_host = self._get_client_host(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 构建访问日志消息
        access_message = (
            f"{client_host} - \"{request.method} {request.url.path}{self._get_query_string(request)}\" "
            f"- RequestID: {request_id}"
        )
        
        # 记录请求日志
        access_logger.info(access_message)
        
        # 详细日志（调试用，已过滤敏感头）
        if self.log_headers:
            safe_headers = {
                k: ("***" if k.lower() in ("authorization", "cookie", "x-api-key") else v)
                for k, v in request.headers.items()
            }
            logger.debug(
                f"Request headers - RequestID: {request_id}, "
                f"Headers: {safe_headers}"
            )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 添加自定义响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            # 记录响应日志
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s - "
                f"RequestID: {request_id}"
            )
            
            # 记录慢请求警告
            if process_time > 5.0:
                logger.warning(
                    f"Slow request detected - {request.method} {request.url.path} - "
                    f"Time: {process_time:.3f}s - RequestID: {request_id}"
                )
            
            return response
            
        except Exception as exc:
            # 计算处理时间（即使出错）
            process_time = time.time() - start_time
            
            # 记录异常日志
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Exception: {type(exc).__name__} - "
                f"Time: {process_time:.3f}s - "
                f"RequestID: {request_id}"
            )
            
            # 重新抛出异常，让错误处理中间件处理
            raise
    
    def _get_or_create_request_id(self, request: Request) -> str:
        """
        获取或创建请求追踪 ID
        
        优先从请求头中获取（支持分布式追踪），
        否则生成新的 UUID。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            str: 请求追踪 ID
        """
        # 检查请求头中是否有追踪 ID
        request_id = request.headers.get("X-Request-ID")
        if request_id:
            return request_id
        
        # 生成新的追踪 ID
        return str(uuid.uuid4())
    
    def _get_client_host(self, request: Request) -> str:
        """
        获取客户端主机地址
        
        优先从代理头获取，支持负载均衡和 CDN 环境。
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            str: 客户端主机地址
        """
        try:
            # 检查 X-Forwarded-For 头
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
            
        except Exception:
            return "unknown"
    
    def _get_query_string(self, request: Request) -> str:
        """
        获取查询字符串（已过滤敏感参数）
        
        Args:
            request: HTTP 请求对象
            
        Returns:
            str: 查询字符串（包含?前缀）或空字符串
        """
        _SENSITIVE_PARAMS = {"token", "password", "secret", "key", "apikey", "api_key"}
        params = dict(request.query_params)
        safe_params = {
            k: ("***" if k.lower() in _SENSITIVE_PARAMS else v)
            for k, v in params.items()
        }
        query_string = "&".join(f"{k}={v}" for k, v in safe_params.items())
        if query_string:
            return f"?{query_string}"
        return ""


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    性能日志记录中间件
    
    专门用于记录性能指标，如数据库查询时间、外部 API 调用时间等。
    可与 LoggingMiddleware 配合使用。
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录性能指标
        
        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            Response: HTTP 响应对象
        """
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # 使用高精度计时器
            process_time = time.perf_counter() - start_time
            
            # 记录性能指标
            logger.debug(
                f"Performance metrics - {request.method} {request.url.path} - "
                f"Total time: {process_time:.6f}s"
            )
            
            return response
            
        except Exception:
            process_time = time.perf_counter() - start_time
            logger.error(
                f"Performance metrics (failed) - {request.method} {request.url.path} - "
                f"Time before exception: {process_time:.6f}s"
            )
            raise
