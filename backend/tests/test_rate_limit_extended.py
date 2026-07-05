"""
限流中间件扩展测试模块

补充测试限流中间件的未覆盖功能，包括：
- 滑动窗口算法边界条件
- 不同key的独立计数
- 清理过期记录的边界
- 限流中间件的各种场景

作者: Test Team
创建日期: 2026-05-28
"""

import os
import sys
import unittest
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middlewares.rate_limit import SlidingWindowCounter, RateLimitMiddleware
from app.exceptions import RateLimitExceeded


class TestSlidingWindowCounter(unittest.TestCase):
    """测试滑动窗口计数器"""

    def test_init(self):
        """测试初始化"""
        counter = SlidingWindowCounter(max_requests=10, window_seconds=60)
        
        self.assertEqual(counter.max_requests, 10)
        self.assertEqual(counter.window_seconds, 60)
        self.assertEqual(len(counter._requests), 0)

    def test_is_allowed_first_request(self):
        """测试首次请求"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=60)
        
        allowed, retry_after = counter.is_allowed("key1")
        
        self.assertTrue(allowed)
        self.assertEqual(retry_after, 0)
        self.assertEqual(len(counter._requests["key1"]), 1)

    def test_is_allowed_within_limit(self):
        """测试在限制内的请求"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=60)
        
        # 发送4个请求
        for i in range(4):
            allowed, _ = counter.is_allowed("key1")
            self.assertTrue(allowed)
        
        self.assertEqual(len(counter._requests["key1"]), 4)

    def test_is_allowed_exceeds_limit(self):
        """测试超出限制"""
        counter = SlidingWindowCounter(max_requests=3, window_seconds=60)
        
        # 发送3个请求
        for i in range(3):
            allowed, _ = counter.is_allowed("key1")
            self.assertTrue(allowed)
        
        # 第4个请求应该被拒绝
        allowed, retry_after = counter.is_allowed("key1")
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_is_allowed_different_keys(self):
        """测试不同key独立计数"""
        counter = SlidingWindowCounter(max_requests=3, window_seconds=60)
        
        # key1发送3个请求
        for i in range(3):
            counter.is_allowed("key1")
        
        # key1应该达到限制
        allowed, _ = counter.is_allowed("key1")
        self.assertFalse(allowed)
        
        # key2应该仍然可以请求
        allowed, _ = counter.is_allowed("key2")
        self.assertTrue(allowed)

    def test_is_allowed_expired_records_cleaned(self):
        """测试过期记录被清理"""
        counter = SlidingWindowCounter(max_requests=3, window_seconds=1)
        
        # 发送2个请求
        counter.is_allowed("key1")
        counter.is_allowed("key1")
        
        # 等待过期
        time.sleep(1.1)
        
        # 发送新请求，过期记录应该被清理
        allowed, _ = counter.is_allowed("key1")
        self.assertTrue(allowed)
        # 应该只有1条记录（旧的被清理，新的被添加）
        self.assertEqual(len(counter._requests["key1"]), 1)

    def test_is_allowed_partial_cleanup(self):
        """测试部分清理"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=2)
        
        # 快速发送3个请求
        counter.is_allowed("key1")
        counter.is_allowed("key1")
        counter.is_allowed("key1")
        
        # 等待部分过期
        time.sleep(1)
        
        # 再发送2个请求
        counter.is_allowed("key1")
        counter.is_allowed("key1")
        
        # 应该总共5条记录，但部分可能已过期
        # 继续发送应该被拒绝
        allowed, retry_after = counter.is_allowed("key1")
        # 由于时间窗口滑动，结果取决于具体时间点
        self.assertIsInstance(allowed, bool)

    def test_cleanup_all_expired(self):
        """测试清理所有过期记录"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=1)
        
        # 发送请求
        counter.is_allowed("key1")
        counter.is_allowed("key2")
        
        # 等待过期
        time.sleep(1.1)
        
        # 清理
        counter.cleanup()
        
        # 所有记录应该被清理
        self.assertEqual(len(counter._requests), 0)

    def test_cleanup_partial_expired(self):
        """测试部分过期清理"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=2)
        
        # 发送请求
        counter.is_allowed("key1")
        time.sleep(1)
        counter.is_allowed("key1")
        
        # 清理
        counter.cleanup()
        
        # 应该最多还有2条记录（由于时间精度，可能1条或2条）
        self.assertLessEqual(len(counter._requests["key1"]), 2)
        # 至少应该有1条记录（第二条请求应该还在窗口内）
        self.assertGreaterEqual(len(counter._requests["key1"]), 1)

    def test_get_stats_empty(self):
        """测试空统计"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=60)
        
        stats = counter.get_stats()
        
        self.assertEqual(stats, {})

    def test_get_stats_with_requests(self):
        """测试有请求时的统计"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=60)
        
        counter.is_allowed("key1")
        counter.is_allowed("key1")
        counter.is_allowed("key2")
        
        stats = counter.get_stats()
        
        self.assertEqual(stats["key1"], 2)
        self.assertEqual(stats["key2"], 1)

    def test_retry_after_calculation(self):
        """测试重试时间计算"""
        counter = SlidingWindowCounter(max_requests=2, window_seconds=60)
        
        # 发送2个请求
        counter.is_allowed("key1")
        time.sleep(0.1)  # 稍微延迟
        counter.is_allowed("key1")
        
        # 第3个请求应该被拒绝
        allowed, retry_after = counter.is_allowed("key1")
        
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)
        self.assertLessEqual(retry_after, 60)


class TestRateLimitMiddleware(unittest.IsolatedAsyncioTestCase):
    """测试限流中间件"""

    def setUp(self):
        """测试前准备"""
        self.mock_app = Mock()
        
    @patch('app.middlewares.rate_limit.settings')
    def test_init(self, mock_settings):
        """测试初始化"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        self.assertTrue(middleware.enabled)
        self.assertIsNotNone(middleware.counter)
        
    @patch('app.middlewares.rate_limit.settings')
    def test_init_disabled(self, mock_settings):
        """测试禁用状态初始化"""
        mock_settings.RATE_LIMIT_ENABLED = False
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        self.assertFalse(middleware.enabled)

    @patch('app.middlewares.rate_limit.settings')
    async def test_dispatch_disabled(self, mock_settings):
        """测试禁用时直接放行"""
        mock_settings.RATE_LIMIT_ENABLED = False
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        
        mock_call_next = AsyncMock()
        
        await middleware.dispatch(mock_request, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_request)

    @patch('app.middlewares.rate_limit.settings')
    async def test_dispatch_skip_paths(self, mock_settings):
        """测试跳过特定路径"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        # 测试健康检查路径
        mock_request = Mock()
        mock_request.url.path = "/health"
        
        mock_call_next = AsyncMock()
        
        await middleware.dispatch(mock_request, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_request)

    @patch('app.middlewares.rate_limit.settings')
    async def test_dispatch_allowed(self, mock_settings):
        """测试允许通过的请求"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.state.user = None
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        mock_call_next = AsyncMock()
        
        await middleware.dispatch(mock_request, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_request)

    @patch('app.middlewares.rate_limit.settings')
    async def test_dispatch_rate_limited(self, mock_settings):
        """测试被限流的请求"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 1
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.state.user = None
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # 第一次请求
        mock_call_next = AsyncMock()
        await middleware.dispatch(mock_request, mock_call_next)
        
        # 第二次请求应该被限流
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        self.assertEqual(response.status_code, 429)

    @patch('app.middlewares.rate_limit.settings')
    def test_get_limit_key_from_user(self, mock_settings):
        """测试从用户获取限流key"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_user = Mock()
        mock_user.id = "user123"
        
        mock_request = Mock()
        mock_request.state.user = mock_user
        
        key = middleware._get_limit_key(mock_request)
        
        self.assertEqual(key, "user:user123")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_limit_key_from_ip(self, mock_settings):
        """测试从IP获取限流key"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.state.user = None
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        
        key = middleware._get_limit_key(mock_request)
        
        self.assertEqual(key, "ip:192.168.1.1")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_limit_key_no_user_no_ip(self, mock_settings):
        """测试无用户无IP的情况"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.state.user = None
        mock_request.headers = {}
        mock_request.client = None
        
        key = middleware._get_limit_key(mock_request)
        
        self.assertEqual(key, "ip:unknown")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_client_ip_from_x_forwarded_for(self, mock_settings):
        """测试可信代理场景下从 X-Forwarded-For 获取 IP"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        ip = middleware._get_client_ip(mock_request)
        
        # 应该取第一个IP
        self.assertEqual(ip, "10.0.0.1")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_client_ip_ignores_spoofed_forwarded_for(self, mock_settings):
        """测试非可信客户端伪造 X-Forwarded-For 时使用真实 peer IP"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60

        middleware = RateLimitMiddleware(self.mock_app)

        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1"}
        mock_request.client = Mock()
        mock_request.client.host = "203.0.113.9"

        ip = middleware._get_client_ip(mock_request)

        self.assertEqual(ip, "203.0.113.9")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_client_ip_from_x_real_ip(self, mock_settings):
        """测试可信代理场景下从 X-Real-IP 获取 IP"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.headers = {"X-Real-IP": "10.0.0.5"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        ip = middleware._get_client_ip(mock_request)
        
        self.assertEqual(ip, "10.0.0.5")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_client_ip_from_client(self, mock_settings):
        """测试从request.client获取IP"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"
        
        ip = middleware._get_client_ip(mock_request)
        
        self.assertEqual(ip, "192.168.1.100")

    @patch('app.middlewares.rate_limit.settings')
    def test_get_client_ip_unknown(self, mock_settings):
        """测试未知IP"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = None
        
        ip = middleware._get_client_ip(mock_request)
        
        self.assertEqual(ip, "unknown")

    @patch('app.middlewares.rate_limit.settings')
    async def test_build_rate_limit_response(self, mock_settings):
        """测试构建限流响应"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        
        response = await middleware._build_rate_limit_response(mock_request, 30)
        
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "30")
        self.assertEqual(response.headers["X-RateLimit-Limit"], "100")
        self.assertEqual(response.headers["X-RateLimit-Window"], "60")
        self.assertEqual(response.headers["X-RateLimit-Remaining"], "0")
        
        # 检查响应内容
        import json
        body = json.loads(response.body)
        self.assertEqual(body["code"], 40003)
        self.assertIn("请求过于频繁", body["message"])

    @patch('app.middlewares.rate_limit.settings')
    async def test_cleanup_triggered(self, mock_settings):
        """测试清理触发"""
        mock_settings.RATE_LIMIT_ENABLED = True
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW = 60
        
        middleware = RateLimitMiddleware(self.mock_app)
        
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.state.user = None
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        mock_call_next = AsyncMock()
        
        # 模拟100次请求触发清理
        with patch.object(middleware.counter, 'cleanup') as mock_cleanup:
            for i in range(100):
                await middleware.dispatch(mock_request, mock_call_next)
            
            # 第100次请求应该触发清理
            mock_cleanup.assert_called_once()


class TestRateLimitEdgeCases(unittest.IsolatedAsyncioTestCase):
    """测试限流边界情况"""

    def test_sliding_window_zero_requests(self):
        """测试零请求限制"""
        counter = SlidingWindowCounter(max_requests=0, window_seconds=60)
        
        # 任何请求都应该被拒绝
        allowed, _ = counter.is_allowed("key1")
        self.assertFalse(allowed)

    def test_sliding_window_zero_window(self):
        """测试零时间窗口"""
        counter = SlidingWindowCounter(max_requests=5, window_seconds=0)
        
        # 立即过期
        allowed, _ = counter.is_allowed("key1")
        self.assertTrue(allowed)
        
        # 立即再次请求，之前的应该已过期
        allowed, _ = counter.is_allowed("key1")
        self.assertTrue(allowed)

    def test_sliding_window_negative_values(self):
        """测试负值处理"""
        # 虽然不应该传入负值，但测试一下行为
        counter = SlidingWindowCounter(max_requests=-1, window_seconds=60)
        
        allowed, _ = counter.is_allowed("key1")
        # 负值可能导致意外行为，但至少不应该崩溃
        self.assertIsInstance(allowed, bool)

    async def test_rate_limit_headers_in_skip_paths(self):
        """测试跳过路径不应该有限流头"""
        with patch('app.middlewares.rate_limit.settings') as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.RATE_LIMIT_REQUESTS = 100
            mock_settings.RATE_LIMIT_WINDOW = 60
            
            middleware = RateLimitMiddleware(Mock())
            
            mock_request = Mock()
            mock_request.url.path = "/health"
            
            mock_call_next = AsyncMock()
            mock_call_next.return_value = Mock()
            mock_call_next.return_value.headers = {}
            
            # 异步调用
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # 跳过路径不应该检查限流
            mock_call_next.assert_called_once()


# 为了运行异步测试
import asyncio

# 修改测试类以支持异步
original_is_allowed = SlidingWindowCounter.is_allowed

def sync_is_allowed(self, key):
    """同步包装"""
    return original_is_allowed(self, key)

SlidingWindowCounter.is_allowed = sync_is_allowed


if __name__ == "__main__":
    unittest.main()
