"""
限流中间件

基于内存的滑动窗口限流实现，不依赖 Redis，适合小规模部署。
支持按 IP 限流和按用户限流两种模式。
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.exceptions import RateLimitExceeded
from app.utils.logger import logger, get_logger

# 获取模块日志器
rate_limit_logger = get_logger("middlewares.rate_limit")


class SlidingWindowCounter:
    """
    滑动窗口计数器

    基于内存的滑动窗口限流算法实现。
    每个窗口记录请求时间戳列表，通过清理过期记录实现滑动窗口效果。

    Attributes:
        max_requests: 窗口内允许的最大请求数
        window_seconds: 窗口大小（秒）
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        初始化滑动窗口计数器

        Args:
            max_requests: 窗口内允许的最大请求数
            window_seconds: 窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # 存储每个 key 的请求时间戳列表
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        检查请求是否被允许

        Args:
            key: 限流标识（IP 或 用户ID）

        Returns:
            Tuple[bool, int]: (是否允许, 建议重试等待秒数)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # 清理过期记录
        timestamps = self._requests[key]
        # 使用列表推导式过滤掉过期的时间戳
        self._requests[key] = [
            ts for ts in timestamps if ts > window_start
        ]
        timestamps = self._requests[key]

        if self.max_requests <= 0:
            # 如果最大请求数小于等于0，拒绝所有请求
            return False, self.window_seconds
        
        if len(timestamps) < self.max_requests:
            # 允许请求，记录当前时间戳
            timestamps.append(now)
            return True, 0
        else:
            # 计算需要等待的时间（最早记录的过期时间）
            if timestamps:
                retry_after = int(timestamps[0] - window_start) + 1
                return False, max(retry_after, 1)
            else:
                # 如果列表为空但超过了限制，允许请求（边界情况）
                return True, 0

    def cleanup(self):
        """
        清理所有过期的请求记录

        定期调用以释放内存。
        """
        now = time.time()
        window_start = now - self.window_seconds

        # 清理空列表或全部过期的 key
        expired_keys = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [
                ts for ts in timestamps if ts > window_start
            ]
            if not self._requests[key]:
                expired_keys.append(key)

        for key in expired_keys:
            del self._requests[key]

    def get_stats(self) -> Dict[str, int]:
        """
        获取当前限流统计信息

        Returns:
            Dict[str, int]: 各 key 的当前请求数
        """
        return {key: len(ts) for key, ts in self._requests.items()}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件

    基于 IP 和用户身份的请求频率限制。
    已认证用户按用户ID限流，未认证用户按IP限流。

    Attributes:
        counter: 滑动窗口计数器实例
        enabled: 是否启用限流
    """

    # 不需要限流的路径前缀
    SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app):
        """
        初始化限流中间件

        Args:
            app: FastAPI 应用实例
        """
        super().__init__(app)
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.counter = SlidingWindowCounter(
            max_requests=settings.RATE_LIMIT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW,
        )
        rate_limit_logger.info(
            f"限流中间件已初始化 - 启用: {self.enabled}, "
            f"最大请求数: {settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}s"
        )

    async def dispatch(self, request: Request, call_next):
        """
        处理请求并进行限流检查

        Args:
            request: HTTP 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: HTTP 响应对象
        """
        # 未启用限流，直接放行
        if not self.enabled:
            return await call_next(request)

        # 跳过不需要限流的路径
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # 获取限流标识
        limit_key = self._get_limit_key(request)

        # 检查是否被允许
        allowed, retry_after = self.counter.is_allowed(limit_key)

        if not allowed:
            rate_limit_logger.warning(
                f"请求被限流 - Key: {limit_key}, "
                f"Path: {request.url.path}, "
                f"Retry-After: {retry_after}s"
            )
            return await self._build_rate_limit_response(request, retry_after)

        # 定期清理（每 100 次请求清理一次）
        if hasattr(self, '_request_count'):
            self._request_count += 1
            if self._request_count % 100 == 0:
                self.counter.cleanup()
        else:
            self._request_count = 1

        return await call_next(request)

    def _get_limit_key(self, request: Request) -> str:
        """
        获取限流标识

        优先使用用户ID（已认证用户），否则使用客户端IP。

        Args:
            request: HTTP 请求对象

        Returns:
            str: 限流标识
        """
        # 尝试获取已认证用户ID
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"

        # 使用客户端IP
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端 IP 地址

        优先从代理头获取，支持负载均衡环境。

        Args:
            request: HTTP 请求对象

        Returns:
            str: 客户端 IP 地址
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"

    async def _build_rate_limit_response(
        self,
        request: Request,
        retry_after: int
    ) -> JSONResponse:
        """
        构建限流响应

        返回 429 状态码和 Retry-After 头。

        Args:
            request: HTTP 请求对象
            retry_after: 建议重试等待时间（秒）

        Returns:
            JSONResponse: 限流响应
        """
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "code": 40003,
                "message": "请求过于频繁，请稍后再试",
                "data": None,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                "X-RateLimit-Window": str(settings.RATE_LIMIT_WINDOW),
                "X-RateLimit-Remaining": "0",
            }
        )
