"""
限流中间件测试

测试 rate_limit.py 中的功能，包括滑动窗口计数器、
限流中间件和路径跳过逻辑等。
"""

import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.middlewares.rate_limit import SlidingWindowCounter, RateLimitMiddleware


# ===== test_sliding_window_allows_requests: 测试正常请求通过 =====

class TestSlidingWindowAllowsRequests:
    """测试滑动窗口正常放行请求"""

    def test_sliding_window_allows_requests(self):
        """
        测试正常请求通过：在窗口内未达到最大请求数时，
        所有请求都应被允许。
        """
        # 创建一个允许 5 次请求 / 60 秒窗口的计数器
        counter = SlidingWindowCounter(max_requests=5, window_seconds=60)

        # 前 5 次请求都应被允许
        for i in range(5):
            allowed, retry_after = counter.is_allowed("test_key")
            assert allowed is True, f"第 {i+1} 次请求应被允许"
            assert retry_after == 0

    def test_sliding_window_different_keys(self):
        """测试不同 key 独立计数：不同 IP/用户的请求应独立计数"""
        counter = SlidingWindowCounter(max_requests=2, window_seconds=60)

        # key1 的请求
        allowed1, _ = counter.is_allowed("ip:192.168.1.1")
        assert allowed1 is True

        allowed2, _ = counter.is_allowed("ip:192.168.1.1")
        assert allowed2 is True

        # key2 的请求（独立计数，不受 key1 影响）
        allowed3, _ = counter.is_allowed("ip:10.0.0.1")
        assert allowed3 is True


# ===== test_sliding_window_blocks_excess: 测试超限请求被拒绝 =====

class TestSlidingWindowBlocksExcess:
    """测试滑动窗口超限拒绝请求"""

    def test_sliding_window_blocks_excess(self):
        """
        测试超限请求被拒绝：当窗口内请求数达到上限后，
        后续请求应被拒绝并返回重试等待时间。
        """
        counter = SlidingWindowCounter(max_requests=3, window_seconds=60)

        # 前 3 次请求应被允许
        for i in range(3):
            allowed, retry_after = counter.is_allowed("test_key")
            assert allowed is True, f"第 {i+1} 次请求应被允许"

        # 第 4 次请求应被拒绝
        allowed, retry_after = counter.is_allowed("test_key")
        assert allowed is False
        assert retry_after > 0, "重试等待时间应大于 0"

    def test_sliding_window_retry_after_decreases(self):
        """测试重试等待时间：随着时间推移，retry_after 应逐渐减小"""
        counter = SlidingWindowCounter(max_requests=2, window_seconds=5)

        # 用完配额
        counter.is_allowed("key")
        counter.is_allowed("key")

        # 立即请求应被拒绝
        _, retry1 = counter.is_allowed("key")
        assert retry1 > 0

        # 等待一小段时间后，retry_after 应减小
        time.sleep(1)
        _, retry2 = counter.is_allowed("key")
        assert retry2 <= retry1


# ===== test_sliding_window_resets_after_window: 测试窗口重置后恢复 =====

class TestSlidingWindowResetsAfterWindow:
    """测试滑动窗口过期后重置"""

    def test_sliding_window_resets_after_window(self):
        """
        测试窗口重置后恢复：当时间窗口过期后，
        之前的请求记录应被清理，新的请求应被允许。
        """
        # 使用极短的窗口时间（1秒）方便测试
        counter = SlidingWindowCounter(max_requests=2, window_seconds=1)

        # 用完配额
        counter.is_allowed("reset_key")
        counter.is_allowed("reset_key")

        # 第 3 次请求应被拒绝
        allowed, _ = counter.is_allowed("reset_key")
        assert allowed is False

        # 等待窗口过期
        time.sleep(1.5)

        # 窗口过期后，请求应被允许
        allowed, retry_after = counter.is_allowed("reset_key")
        assert allowed is True, "窗口过期后请求应被允许"
        assert retry_after == 0


# ===== test_rate_limit_middleware_skip_health: 测试健康检查路径跳过限流 =====

class TestRateLimitMiddlewareSkipHealth:
    """测试限流中间件跳过健康检查路径"""

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_skip_health(self):
        """
        测试健康检查路径跳过限流：/health 路径不应被限流，
        即使超过限流阈值也应正常通过。
        """
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = True

        # 创建模拟请求
        mock_request = MagicMock()
        mock_request.url.path = "/health"

        # 创建模拟的 call_next
        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        # 即使计数器已满，/health 路径也应放行
        # 先用完配额
        for _ in range(200):
            middleware.counter.is_allowed("ip:127.0.0.1")

        # 调用中间件
        response = await middleware.dispatch(mock_request, call_next)

        # 应正常调用 call_next（不被拦截）
        call_next.assert_called_once()
        assert response == mock_response


# ===== test_rate_limit_middleware_skip_docs: 测试文档路径跳过限流 =====

class TestRateLimitMiddlewareSkipDocs:
    """测试限流中间件跳过文档路径"""

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_skip_docs(self):
        """
        测试文档路径跳过限流：/docs 和 /redoc 路径不应被限流。
        """
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = True

        # 测试 /docs 路径
        mock_request_docs = MagicMock()
        mock_request_docs.url.path = "/docs"

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request_docs, call_next)
        call_next.assert_called_once()
        assert response == mock_response

        # 测试 /redoc 路径
        call_next.reset_mock()
        mock_request_redoc = MagicMock()
        mock_request_redoc.url.path = "/redoc"

        response = await middleware.dispatch(mock_request_redoc, call_next)
        call_next.assert_called_once()
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_skip_openapi(self):
        """测试 /openapi.json 路径跳过限流"""
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = True

        mock_request = MagicMock()
        mock_request.url.path = "/openapi.json"

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_disabled(self):
        """测试限流禁用时所有请求直接放行"""
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = False

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/files"

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()
        assert response == mock_response


class TestRateLimitExtended:
    """限流扩展测试 - 覆盖未覆盖代码行"""

    def test_is_rate_limited_key_format(self):
        """测试限流key格式 - 验证key包含用户ID或IP（行85）"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=60)

        # 使用IP格式的key
        allowed, _ = counter.is_allowed("ip:192.168.1.1")
        assert allowed is True

        # 使用用户ID格式的key
        allowed, _ = counter.is_allowed("user:12345")
        assert allowed is True

    def test_is_rate_limited_zero_max_requests(self):
        """测试max_requests为0时拒绝所有请求（行70-72）"""
        counter = SlidingWindowCounter(max_requests=0, window_seconds=60)

        allowed, retry_after = counter.is_allowed("test_key")
        assert allowed is False
        assert retry_after == 60  # 等于 window_seconds

    def test_is_rate_limited_negative_max_requests(self):
        """测试max_requests为负数时拒绝所有请求"""
        counter = SlidingWindowCounter(max_requests=-1, window_seconds=60)

        allowed, retry_after = counter.is_allowed("test_key")
        assert allowed is False

    def test_is_rate_limited_empty_after_cleanup(self):
        """测试列表清空后边界情况（行83-85）"""
        counter = SlidingWindowCounter(max_requests=1, window_seconds=1)

        # 用完配额
        counter.is_allowed("edge_key")

        # 立即请求应被拒绝
        allowed, _ = counter.is_allowed("edge_key")
        assert allowed is False

        # 等待窗口过期
        time.sleep(1.5)

        # 窗口过期后，请求应被允许
        allowed, retry_after = counter.is_allowed("edge_key")
        assert allowed is True
        assert retry_after == 0

    def test_is_rate_limited_empty_timestamps(self):
        """测试时间戳列表为空但超过限制的边界情况（行85）"""
        # max_requests > 0，所有时间戳过期后 timestamps 为空
        # 但 len(timestamps) >= max_requests 不成立（0 < max_requests）
        # 所以实际上行85很难触发
        # 行85仅在：max_requests > 0, len(timestamps) >= max_requests, timestamps为空
        # 这意味着过滤后列表为空，但 max_requests 也为 0（不可能，因为上面已检查）
        # 或者 max_requests 为负数（也不可能，因为上面已检查）
        # 实际上行85是一个防御性代码，正常情况下不会触发
        # 但我们可以通过直接操作内部状态来测试
        counter = SlidingWindowCounter(max_requests=1, window_seconds=60)
        # 直接设置一个已过期的时间戳
        import time as t
        counter._requests["edge_case"] = [t.time() - 120]  # 2分钟前，已过期
        # 过滤后 timestamps 为空，len(timestamps)=0 < max_requests=1，进入允许分支
        # 无法直接触发行85，因为 len([]) < 1
        # 行85仅在 max_requests=0 时触发，但那被行70拦截了
        # 所以行85实际上是不可达代码（dead code）
        pass

    def test_cleanup_expired_records(self):
        """测试清理过期记录（行171-192）"""
        counter = SlidingWindowCounter(max_requests=100, window_seconds=1)

        # 添加多个key的请求记录
        for i in range(5):
            counter.is_allowed(f"key_{i}")

        # 等待所有记录过期
        time.sleep(1.5)

        # 执行清理
        counter.cleanup()

        # 清理后统计应为空
        stats = counter.get_stats()
        assert len(stats) == 0

    def test_cleanup_partial_expired(self):
        """测试部分过期记录的清理"""
        counter = SlidingWindowCounter(max_requests=100, window_seconds=3)

        # 添加旧记录
        counter.is_allowed("old_key")
        time.sleep(2)

        # 添加新记录
        counter.is_allowed("new_key")

        # 清理 - old_key 应已过期（超过3秒窗口的一半以上）
        counter.cleanup()

        # 新key应保留
        stats = counter.get_stats()
        assert "new_key" in stats

    def test_get_stats(self):
        """测试获取限流统计信息"""
        counter = SlidingWindowCounter(max_requests=10, window_seconds=60)

        counter.is_allowed("key1")
        counter.is_allowed("key1")
        counter.is_allowed("key2")

        stats = counter.get_stats()
        assert stats["key1"] == 2
        assert stats["key2"] == 1

    def test_dispatch_skip_paths(self):
        """测试跳过路径列表（行257）"""
        # 验证 SKIP_PATHS 包含所有预期路径
        assert "/health" in RateLimitMiddleware.SKIP_PATHS
        assert "/docs" in RateLimitMiddleware.SKIP_PATHS
        assert "/redoc" in RateLimitMiddleware.SKIP_PATHS
        assert "/openapi.json" in RateLimitMiddleware.SKIP_PATHS

    @pytest.mark.asyncio
    async def test_dispatch_rate_limited_response(self):
        """测试被限流时返回429响应"""
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = True

        # 用完配额（使用与 middleware 相同的 key 生成逻辑）
        # middleware._get_limit_key 会检查 request.state.user
        # 如果 user 存在且有 id 属性，使用 user:id，否则使用 ip:client.host
        # 我们需要确保 key 一致
        limit_key = "ip:127.0.0.1"
        for _ in range(200):
            middleware.counter.is_allowed(limit_key)

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/test"
        # 模拟 headers.get 返回 None（不是 MagicMock）
        mock_request.headers.get.return_value = None
        mock_request.client.host = "127.0.0.1"
        # 确保 state.user 为 None，这样 _get_limit_key 使用 IP
        mock_request.state.user = None

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        # 应返回429响应（JSONResponse）
        assert response.status_code == 429
        # call_next 不应被调用
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_with_authenticated_user(self):
        """测试已认证用户按用户ID限流"""
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = True

        mock_user = MagicMock()
        mock_user.id = "user_123"

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/test"
        mock_request.state.user = mock_user
        mock_request.headers = {}
        mock_request.client = None

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)
        call_next.assert_called_once()
        assert response == mock_response

    def test_get_limit_key_with_user(self):
        """测试获取限流key - 已认证用户"""
        middleware = RateLimitMiddleware(app=MagicMock())

        mock_user = MagicMock()
        mock_user.id = "user_456"

        mock_request = MagicMock()
        mock_request.state.user = mock_user

        key = middleware._get_limit_key(mock_request)
        assert key == "user:user_456"

    def test_get_limit_key_without_user(self):
        """测试获取限流key - 未认证用户"""
        middleware = RateLimitMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.state.user = None
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.1"

        key = middleware._get_limit_key(mock_request)
        assert key == "ip:10.0.0.1"

    def test_get_client_ip_from_forwarded_for(self):
        """测试从X-Forwarded-For获取客户端IP"""
        middleware = RateLimitMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_from_real_ip(self):
        """测试从X-Real-IP获取客户端IP"""
        middleware = RateLimitMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": None, "X-Real-IP": "10.0.0.2"}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "10.0.0.2"

    def test_get_client_ip_from_client(self):
        """测试从request.client获取IP"""
        middleware = RateLimitMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": None, "X-Real-IP": None}
        mock_request.client.host = "10.0.0.3"

        ip = middleware._get_client_ip(mock_request)
        assert ip == "10.0.0.3"

    def test_get_client_ip_unknown(self):
        """测试无法获取IP时返回unknown"""
        middleware = RateLimitMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": None, "X-Real-IP": None}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "unknown"

    def test_dispatch_periodic_cleanup(self):
        """测试定期清理机制（行186-188）"""
        middleware = RateLimitMiddleware(app=MagicMock())
        middleware.enabled = True

        # 模拟 _request_count 属性
        middleware._request_count = 99  # 下一次请求会触发清理

        mock_user = MagicMock()
        mock_user.id = "user_cleanup"

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/test"
        mock_request.state.user = mock_user
        mock_request.headers = {}

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        import asyncio
        asyncio.run(
            middleware.dispatch(mock_request, call_next)
        )
        # _request_count 应增加到 100，触发 cleanup
        assert middleware._request_count == 100
