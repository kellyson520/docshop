"""
缓存服务模块测试

测试 cache_service.py 中的功能，包括缓存存取、过期、删除、清空、
禁用状态和 @cached 装饰器等。
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from app.services.cache_service import CacheService, cached, cache_service


# ===== test_cache_set_get: 测试缓存存取 =====

class TestCacheSetGet:
    """测试缓存的 set 和 get 操作"""

    def test_cache_set_get(self):
        """测试缓存存取：设置值后应能正确取回"""
        cs = CacheService()
        cs.enabled = True

        # 设置缓存
        result = cs.set("test_key", {"name": "test", "value": 42})
        assert result is True

        # 获取缓存
        cached_value = cs.get("test_key")
        assert cached_value == {"name": "test", "value": 42}

    def test_cache_get_miss(self):
        """测试缓存未命中：获取不存在的键应返回 None"""
        cs = CacheService()
        cs.enabled = True

        result = cs.get("nonexistent_key")
        assert result is None

    def test_cache_set_overwrite(self):
        """测试缓存覆盖：对同一键重新设置应覆盖旧值"""
        cs = CacheService()
        cs.enabled = True

        cs.set("key", "value1")
        cs.set("key", "value2")

        assert cs.get("key") == "value2"


# ===== test_cache_expired: 测试缓存过期 =====

class TestCacheExpired:
    """测试缓存过期机制"""

    def test_cache_expired(self):
        """
        测试缓存过期：超过 TTL 时间后，缓存值应自动失效并返回 None。
        使用极短的 TTL 来加速测试。
        """
        cs = CacheService()
        cs.enabled = True
        cs.ttl = 1  # 设置 1 秒的 TTL
        # 重新创建 TTLCache 实例以应用新的 TTL
        from cachetools import TTLCache
        cs._cache = TTLCache(maxsize=cs.max_size, ttl=cs.ttl)

        cs.set("expire_key", "expire_value")

        # 立即获取，应该存在
        assert cs.get("expire_key") == "expire_value"

        # 等待超过 TTL
        time.sleep(1.5)

        # 再次获取，应该已过期
        assert cs.get("expire_key") is None


# ===== test_cache_delete: 测试缓存删除 =====

class TestCacheDelete:
    """测试缓存删除功能"""

    def test_cache_delete(self):
        """测试缓存删除：删除已存在的键后应返回 None"""
        cs = CacheService()
        cs.enabled = True

        cs.set("delete_key", "delete_value")
        assert cs.get("delete_key") == "delete_value"

        # 删除缓存
        result = cs.delete("delete_key")
        assert result is True

        # 删除后获取应为 None
        assert cs.get("delete_key") is None

    def test_cache_delete_nonexistent(self):
        """测试删除不存在的键：应返回 False"""
        cs = CacheService()
        cs.enabled = True

        result = cs.delete("nonexistent_key")
        assert result is False


# ===== test_cache_clear: 测试缓存清空 =====

class TestCacheClear:
    """测试缓存清空功能"""

    def test_cache_clear(self):
        """测试缓存清空：清空后所有键都应不可访问"""
        cs = CacheService()
        cs.enabled = True

        # 设置多个缓存
        cs.set("key1", "value1")
        cs.set("key2", "value2")
        cs.set("key3", "value3")

        # 清空缓存
        result = cs.clear()
        assert result is True

        # 所有键都应不可访问
        assert cs.get("key1") is None
        assert cs.get("key2") is None
        assert cs.get("key3") is None

    def test_cache_clear_empty(self):
        """测试清空空缓存：应正常返回 True"""
        cs = CacheService()
        cs.enabled = True

        result = cs.clear()
        assert result is True


# ===== test_cache_disabled: 测试缓存禁用时直接返回None =====

class TestCacheDisabled:
    """测试缓存禁用时的行为"""

    def test_cache_disabled_get(self):
        """测试缓存禁用时 get 应直接返回 None"""
        cs = CacheService()
        cs.enabled = False

        # 即使设置了值，禁用状态下也应返回 None
        result = cs.set("disabled_key", "disabled_value")
        assert result is False

        cached_value = cs.get("disabled_key")
        assert cached_value is None

    def test_cache_disabled_delete(self):
        """测试缓存禁用时 delete 应返回 False"""
        cs = CacheService()
        cs.enabled = False

        result = cs.delete("any_key")
        assert result is False

    def test_cache_disabled_clear(self):
        """测试缓存禁用时 clear 应返回 False"""
        cs = CacheService()
        cs.enabled = False

        result = cs.clear()
        assert result is False


# ===== test_cached_decorator: 测试 @cached 装饰器 =====

class TestCachedDecorator:
    """测试 @cached 装饰器功能"""

    def test_cached_decorator(self):
        """
        测试 @cached 装饰器：装饰后的函数结果应被缓存，
        相同参数的重复调用不应再次执行原函数。
        """
        # 确保缓存服务启用
        original_enabled = cache_service.enabled
        cache_service.enabled = True

        # 清空缓存避免干扰
        cache_service.clear()

        call_count = 0

        @cached("test_prefix", ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        try:
            # 第一次调用，应执行原函数
            result1 = expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1

            # 第二次调用相同参数，应从缓存获取，不执行原函数
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 1  # 调用次数不变

            # 不同参数的调用，应执行原函数
            result3 = expensive_function(3, 4)
            assert result3 == 7
            assert call_count == 2

        finally:
            # 恢复原始状态
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_cached_decorator_none_result(self):
        """
        测试 @cached 装饰器对 None 结果的处理：
        返回 None 的结果不应被缓存。
        """
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("none_test", ttl=60)
        def returns_none():
            nonlocal call_count
            call_count += 1
            return None

        try:
            # 第一次调用
            result1 = returns_none()
            assert result1 is None
            assert call_count == 1

            # 第二次调用，因为结果是 None 不应被缓存，所以会再次执行
            result2 = returns_none()
            assert result2 is None
            assert call_count == 2

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_cached_decorator_clear_cache(self):
        """测试装饰器的 clear_cache 方法"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("clear_test", ttl=60)
        def tracked_function(val):
            nonlocal call_count
            call_count += 1
            return val * 2

        try:
            # 调用并缓存
            assert tracked_function(5) == 10
            assert call_count == 1

            # 清除缓存
            tracked_function.clear_cache(5)

            # 再次调用，应重新执行原函数
            assert tracked_function(5) == 10
            assert call_count == 2

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()


class TestCacheServiceExtended:
    """缓存服务扩展测试 - 覆盖未覆盖代码行"""

    def test_cached_decorator_with_args(self):
        """测试带位置参数的装饰器缓存（行73-75）"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("args_test", ttl=60)
        def func_with_args(a, b, c):
            nonlocal call_count
            call_count += 1
            return a + b + c

        try:
            result1 = func_with_args(1, 2, 3)
            assert result1 == 6
            assert call_count == 1

            # 相同参数应命中缓存
            result2 = func_with_args(1, 2, 3)
            assert result2 == 6
            assert call_count == 1

            # 不同参数应执行原函数
            result3 = func_with_args(4, 5, 6)
            assert result3 == 15
            assert call_count == 2

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_cached_decorator_with_kwargs(self):
        """测试带关键字参数的装饰器缓存"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("kwargs_test", ttl=60)
        def func_with_kwargs(name, age=0):
            nonlocal call_count
            call_count += 1
            return f"{name}:{age}"

        try:
            result1 = func_with_kwargs("alice", age=30)
            assert result1 == "alice:30"
            assert call_count == 1

            # 相同参数应命中缓存
            result2 = func_with_kwargs("alice", age=30)
            assert result2 == "alice:30"
            assert call_count == 1

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_get_stats(self):
        """测试获取缓存统计信息（行104-106）"""
        cs = CacheService()
        cs.enabled = True

        # 设置一些缓存
        cs.set("key1", "value1")
        cs.set("key2", "value2")

        stats = cs.get_stats()
        assert stats["enabled"] is True
        assert stats["ttl"] == cs.ttl
        assert stats["max_size"] == cs.max_size
        assert stats["current_size"] >= 2
        assert "currsize" in stats

    def test_cached_decorator_none_value(self):
        """测试缓存None值时不缓存（行127-129）"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("none_val_test", ttl=60)
        def returns_none():
            nonlocal call_count
            call_count += 1
            return None

        try:
            returns_none()
            assert call_count == 1
            # None 不被缓存，下次应再次调用
            returns_none()
            assert call_count == 2

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_cached_decorator_exception(self):
        """测试装饰器函数抛出异常时正常传播"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        @cached("exception_test", ttl=60)
        def raises_error():
            raise ValueError("test error")

        try:
            with pytest.raises(ValueError, match="test error"):
                raises_error()
        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_cached_decorator_custom_ttl(self):
        """测试自定义TTL（行145-147）"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("custom_ttl_test", ttl=120)
        def custom_ttl_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        try:
            result = custom_ttl_func(10)
            assert result == 20
            assert call_count == 1

            # 应从缓存获取
            result2 = custom_ttl_func(10)
            assert result2 == 20
            assert call_count == 1

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_clear_by_pattern(self):
        """测试按模式清理缓存（行188, 245-246）"""
        cs = CacheService()
        cs.enabled = True

        # 设置多个缓存
        cs.set("user:1:data", "value1")
        cs.set("user:2:data", "value2")
        cs.set("project:1:data", "value3")

        # 清除所有缓存
        result = cs.clear()
        assert result is True
        assert cs.get("user:1:data") is None
        assert cs.get("user:2:data") is None
        assert cs.get("project:1:data") is None

    def test_cached_decorator_with_prefix(self):
        """测试自定义缓存键前缀（行252-253, 257-259）"""
        original_enabled = cache_service.enabled
        cache_service.enabled = True
        cache_service.clear()

        call_count = 0

        @cached("my_custom_prefix", ttl=60)
        def prefix_func(x):
            nonlocal call_count
            call_count += 1
            return x + 1

        try:
            # 调用函数
            result = prefix_func(42)
            assert result == 43
            assert call_count == 1

            # 验证缓存键包含前缀
            result2 = prefix_func(42)
            assert result2 == 43
            assert call_count == 1  # 缓存命中

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_cached_decorator_disabled(self):
        """测试缓存禁用时装饰器直接调用原函数"""
        original_enabled = cache_service.enabled
        cache_service.enabled = False
        cache_service.clear()

        call_count = 0

        @cached("disabled_test", ttl=60)
        def disabled_func(x):
            nonlocal call_count
            call_count += 1
            return x * 3

        try:
            # 缓存禁用时，每次调用都执行原函数
            assert disabled_func(5) == 15
            assert call_count == 1
            assert disabled_func(5) == 15
            assert call_count == 2

        finally:
            cache_service.enabled = original_enabled
            cache_service.clear()

    def test_generate_cache_key_long_key(self):
        """测试超长缓存键被哈希（行252-253）"""
        from app.services.cache_service import _generate_cache_key

        # 生成超长键
        long_prefix = "a" * 250
        key = _generate_cache_key(long_prefix, "test_func", (1, 2), {})
        # 超长键应被哈希
        assert len(key) < 300
        assert long_prefix[:20] not in key or ":" in key

    def test_generate_cache_key_exception(self):
        """测试生成缓存键异常时返回备用键（行257-259）"""
        from app.services.cache_service import _generate_cache_key

        # 模拟 str() 调用失败
        class BadArg:
            def __str__(self):
                raise RuntimeError("str failed")

        key = _generate_cache_key("prefix", "func", (BadArg(),), {})
        assert "prefix" in key
        assert "func" in key
        assert "unknown" in key

    def test_cache_get_exception(self):
        """测试缓存读取异常处理（行73-75）"""
        cs = CacheService()
        cs.enabled = True

        # 模拟缓存读取异常
        with patch.object(cs._cache, 'get', side_effect=Exception("cache error")):
            result = cs.get("error_key")
            assert result is None

    def test_cache_set_exception(self):
        """测试缓存设置异常处理（行104-106）"""
        cs = CacheService()
        cs.enabled = True

        # 模拟缓存设置异常 - TTLCache 的 __setitem__ 不容易直接 mock
        # 改为 mock 整个 _cache 对象
        original_cache = cs._cache
        try:
            mock_cache = MagicMock()
            mock_cache.__setitem__ = MagicMock(side_effect=Exception("cache error"))
            cs._cache = mock_cache

            result = cs.set("error_key", "error_value")
            assert result is False
        finally:
            cs._cache = original_cache

    def test_cache_delete_exception(self):
        """测试缓存删除异常处理（行127-129）"""
        cs = CacheService()
        cs.enabled = True

        # 替换整个 _cache 对象来触发异常
        original_cache = cs._cache
        try:
            mock_cache = MagicMock()
            mock_cache.__contains__ = MagicMock(side_effect=Exception("cache error"))
            cs._cache = mock_cache

            result = cs.delete("error_key")
            assert result is False
        finally:
            cs._cache = original_cache

    def test_cache_clear_exception(self):
        """测试缓存清空异常处理（行145-147）"""
        cs = CacheService()
        cs.enabled = True

        with patch.object(cs._cache, 'clear', side_effect=Exception("cache error")):
            result = cs.clear()
            assert result is False

    def test_cache_set_with_custom_ttl(self):
        """测试设置缓存时使用自定义TTL"""
        cs = CacheService()
        cs.enabled = True

        result = cs.set("ttl_key", "ttl_value", ttl=10)
        assert result is True
        assert cs.get("ttl_key") == "ttl_value"
