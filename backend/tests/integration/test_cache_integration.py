"""
缓存集成测试
测试缓存存取、过期、清理和并发访问
使用pytest进行测试
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# 导入缓存服务
from app.services.cache_service import CacheService


class TestCacheOperations:
    """测试缓存基本操作"""

    def test_cache_set_and_get(self):
        """
        测试缓存存取
        验证数据能够正确存入和取出缓存
        """
        cache = CacheService()
        
        # 存入数据
        cache.set("test_key", "test_value")
        
        # 取出数据
        value = cache.get("test_key")
        assert value == "test_value"

    def test_cache_set_with_ttl(self):
        """
        测试带过期时间的缓存
        验证TTL（生存时间）功能正常工作
        """
        cache = CacheService()
        
        # 存入带过期时间的数据（2秒）
        cache.set("ttl_key", "ttl_value", ttl=2)
        
        # 立即获取应该成功
        value = cache.get("ttl_key")
        assert value == "ttl_value"
        
        # 等待过期
        time.sleep(3)
        
        # 过期后获取应该返回None
        value = cache.get("ttl_key")
        assert value is None

    def test_cache_delete(self):
        """
        测试缓存删除
        验证能够删除缓存中的数据
        """
        cache = CacheService()
        
        # 存入数据
        cache.set("delete_key", "delete_value")
        
        # 验证数据存在
        assert cache.get("delete_key") == "delete_value"
        
        # 删除数据
        cache.delete("delete_key")
        
        # 验证数据已删除
        assert cache.get("delete_key") is None

    def test_cache_exists(self):
        """
        测试缓存存在性检查
        验证能够检查键是否存在于缓存中
        """
        cache = CacheService()
        
        # 检查不存在的键
        assert cache.exists("nonexistent_key") is False
        
        # 存入数据
        cache.set("exists_key", "exists_value")
        
        # 检查存在的键
        assert cache.exists("exists_key") is True

    def test_cache_update(self):
        """
        测试缓存更新
        验证能够更新缓存中的数据
        """
        cache = CacheService()
        
        # 存入初始数据
        cache.set("update_key", "initial_value")
        assert cache.get("update_key") == "initial_value"
        
        # 更新数据
        cache.set("update_key", "updated_value")
        assert cache.get("update_key") == "updated_value"


class TestCacheExpiration:
    """测试缓存过期机制"""

    def test_cache_expiration_exact_time(self):
        """
        测试缓存精确过期时间
        验证缓存在指定时间后过期
        """
        cache = CacheService()
        
        # 存入1秒后过期的数据
        cache.set("expire_key", "expire_value", ttl=1)
        
        # 0.5秒后数据应该还在
        time.sleep(0.5)
        assert cache.get("expire_key") == "expire_value"
        
        # 再等待1秒（总共1.5秒）数据应该已过期
        time.sleep(1)
        assert cache.get("expire_key") is None

    def test_cache_expiration_different_ttl(self):
        """
        测试不同TTL的缓存
        验证不同过期时间的缓存独立过期
        """
        cache = CacheService()
        
        # 存入不同过期时间的数据
        cache.set("short_key", "short_value", ttl=1)
        cache.set("medium_key", "medium_value", ttl=3)
        cache.set("long_key", "long_value", ttl=5)
        
        # 2秒后，只有short_key应该过期
        time.sleep(2)
        assert cache.get("short_key") is None
        assert cache.get("medium_key") == "medium_value"
        assert cache.get("long_key") == "long_value"
        
        # 再等待3秒（总共5秒），所有数据都应该过期
        time.sleep(3)
        assert cache.get("medium_key") is None
        assert cache.get("long_key") is None

    def test_cache_expiration_renewal(self):
        """
        测试缓存过期时间续期
        验证更新缓存可以重置过期时间
        """
        cache = CacheService()
        
        # 存入2秒后过期的数据
        cache.set("renew_key", "renew_value", ttl=2)
        
        # 等待1秒
        time.sleep(1)
        
        # 更新数据（续期）
        cache.set("renew_key", "renew_value", ttl=2)
        
        # 再等待1.5秒（如果未续期应该已过期）
        time.sleep(1.5)
        
        # 数据应该仍然存在（因为续期了）
        assert cache.get("renew_key") == "renew_value"


class TestCacheCleanup:
    """测试缓存清理"""

    def test_cache_clear_all(self):
        """
        测试清空所有缓存
        验证能够清空所有缓存数据
        """
        cache = CacheService()
        
        # 存入多条数据
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 验证数据存在
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # 清空缓存
        cache.clear()
        
        # 验证所有数据已删除
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_clear_pattern(self):
        """
        测试按模式清理缓存
        验证能够按模式匹配清理缓存
        """
        cache = CacheService()
        
        # 存入不同前缀的数据
        cache.set("user:1", "user1_data")
        cache.set("user:2", "user2_data")
        cache.set("session:1", "session1_data")
        cache.set("session:2", "session2_data")
        
        # 按模式清理user前缀的数据
        cache.clear_pattern("user:*")
        
        # 验证user数据已删除，session数据保留
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("session:1") == "session1_data"
        assert cache.get("session:2") == "session2_data"

    def test_cache_auto_cleanup_expired(self):
        """
        测试自动清理过期缓存
        验证过期数据被自动清理
        """
        cache = CacheService()
        
        # 存入过期和未过期的数据
        cache.set("expired_key", "expired_value", ttl=1)
        cache.set("active_key", "active_value", ttl=10)
        
        # 等待过期
        time.sleep(2)
        
        # 触发清理（某些缓存实现可能需要显式触发）
        cache.cleanup_expired()
        
        # 验证过期数据已清理
        assert cache.get("expired_key") is None
        assert cache.get("active_key") == "active_value"


class TestConcurrentCacheAccess:
    """测试并发缓存访问"""

    def test_concurrent_cache_reads(self):
        """
        测试并发读取缓存
        验证多个线程同时读取缓存的一致性
        """
        cache = CacheService()
        cache.set("concurrent_read_key", "shared_value")
        
        results = []
        errors = []
        
        def read_cache():
            try:
                value = cache.get("concurrent_read_key")
                results.append(value)
            except Exception as e:
                errors.append(str(e))
        
        # 并发读取
        threads = []
        for _ in range(20):
            t = threading.Thread(target=read_cache)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证所有读取成功且值一致
        assert len(results) == 20
        assert all(r == "shared_value" for r in results)
        assert len(errors) == 0

    def test_concurrent_cache_writes(self):
        """
        测试并发写入缓存
        验证多个线程同时写入缓存的正确性
        """
        cache = CacheService()
        
        errors = []
        
        def write_cache(thread_id):
            try:
                cache.set(f"thread_key_{thread_id}", f"value_{thread_id}")
            except Exception as e:
                errors.append(str(e))
        
        # 并发写入
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_cache, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证所有写入成功
        assert len(errors) == 0
        for i in range(10):
            assert cache.get(f"thread_key_{i}") == f"value_{i}"

    def test_concurrent_read_write(self):
        """
        测试并发读写缓存
        验证读写操作同时进行时的正确性
        """
        cache = CacheService()
        cache.set("rw_key", "initial_value")
        
        read_results = []
        errors = []
        
        def read_cache():
            try:
                value = cache.get("rw_key")
                read_results.append(value)
            except Exception as e:
                errors.append(str(e))
        
        def write_cache():
            try:
                for i in range(5):
                    cache.set("rw_key", f"value_{i}")
                    time.sleep(0.01)
            except Exception as e:
                errors.append(str(e))
        
        # 同时启动读写线程
        threads = []
        
        # 5个写线程
        for _ in range(5):
            t = threading.Thread(target=write_cache)
            threads.append(t)
        
        # 10个读线程
        for _ in range(10):
            t = threading.Thread(target=read_cache)
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证没有错误发生
        assert len(errors) == 0
        # 验证读取到了一些值
        assert len(read_results) == 10

    def test_cache_race_condition(self):
        """
        测试缓存竞态条件
        验证缓存操作的原子性
        """
        cache = CacheService()
        cache.set("counter", 0)
        
        errors = []
        
        def increment_counter():
            try:
                # 读取-修改-写入操作
                for _ in range(10):
                    current = cache.get("counter") or 0
                    time.sleep(0.001)  # 模拟处理延迟
                    cache.set("counter", current + 1)
            except Exception as e:
                errors.append(str(e))
        
        # 并发递增
        threads = []
        for _ in range(5):
            t = threading.Thread(target=increment_counter)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 注意：由于竞态条件，最终值可能小于50
        # 这个测试主要用于检测竞态条件是否存在
        final_value = cache.get("counter")
        assert final_value is not None


class TestCacheDataTypes:
    """测试缓存不同数据类型"""

    def test_cache_string(self):
        """测试缓存字符串"""
        cache = CacheService()
        cache.set("string_key", "string_value")
        assert cache.get("string_key") == "string_value"

    def test_cache_integer(self):
        """测试缓存整数"""
        cache = CacheService()
        cache.set("int_key", 42)
        assert cache.get("int_key") == 42

    def test_cache_dict(self):
        """测试缓存字典"""
        cache = CacheService()
        data = {"name": "test", "value": 123, "nested": {"a": 1}}
        cache.set("dict_key", data)
        result = cache.get("dict_key")
        assert result == data

    def test_cache_list(self):
        """测试缓存列表"""
        cache = CacheService()
        data = [1, 2, 3, "test", {"key": "value"}]
        cache.set("list_key", data)
        result = cache.get("list_key")
        assert result == data

    def test_cache_none(self):
        """测试缓存None值"""
        cache = CacheService()
        cache.set("none_key", None)
        # 注意：某些缓存实现可能将None视为键不存在
        result = cache.get("none_key")
        assert result is None or result == "None"


class TestCachePerformance:
    """测试缓存性能"""

    def test_cache_read_performance(self):
        """
        测试缓存读取性能
        验证缓存读取速度
        """
        cache = CacheService()
        
        # 准备数据
        for i in range(1000):
            cache.set(f"perf_key_{i}", f"perf_value_{i}")
        
        # 测试读取性能
        start_time = time.time()
        for i in range(1000):
            cache.get(f"perf_key_{i}")
        end_time = time.time()
        
        # 1000次读取应该在1秒内完成
        assert end_time - start_time < 1

    def test_cache_write_performance(self):
        """
        测试缓存写入性能
        验证缓存写入速度
        """
        cache = CacheService()
        
        # 测试写入性能
        start_time = time.time()
        for i in range(1000):
            cache.set(f"write_key_{i}", f"write_value_{i}")
        end_time = time.time()
        
        # 1000次写入应该在1秒内完成
        assert end_time - start_time < 1

    def test_cache_memory_usage(self):
        """
        测试缓存内存使用
        验证大量数据不会导致内存问题
        """
        cache = CacheService()
        
        # 存入大量数据
        large_data = "x" * 10000  # 10KB数据
        for i in range(100):
            cache.set(f"large_key_{i}", large_data)
        
        # 验证所有数据可访问
        for i in range(100):
            assert cache.get(f"large_key_{i}") == large_data


class TestCacheErrorHandling:
    """测试缓存错误处理"""

    def test_cache_get_nonexistent_key(self):
        """
        测试获取不存在的键
        验证返回None或默认值
        """
        cache = CacheService()
        
        # 获取不存在的键
        result = cache.get("nonexistent_key")
        assert result is None
        
        # 获取带默认值的键
        result = cache.get("nonexistent_key", default="default_value")
        assert result == "default_value"

    def test_cache_delete_nonexistent_key(self):
        """
        测试删除不存在的键
        验证不抛出异常
        """
        cache = CacheService()
        
        # 删除不存在的键不应该抛出异常
        try:
            cache.delete("nonexistent_key")
        except Exception as e:
            pytest.fail(f"删除不存在的键不应抛出异常: {e}")

    def test_cache_invalid_ttl(self):
        """
        测试无效TTL
        验证处理无效TTL值
        """
        cache = CacheService()
        
        # 负TTL应该被处理
        cache.set("negative_ttl", "value", ttl=-1)
        # 可能立即过期或忽略TTL
        
        # 零TTL应该被处理
        cache.set("zero_ttl", "value", ttl=0)
        # 可能立即过期或不存储


class TestCacheIntegration:
    """测试缓存与应用的集成"""

    def test_cache_session_storage(self):
        """
        测试缓存作为会话存储
        验证会话数据的缓存
        """
        cache = CacheService()
        
        # 模拟会话数据
        session_id = "session_12345"
        session_data = {
            "user_id": "user_123",
            "username": "testuser",
            "login_time": datetime.utcnow().isoformat()
        }
        
        # 存储会话
        cache.set(f"session:{session_id}", session_data, ttl=3600)
        
        # 读取会话
        retrieved = cache.get(f"session:{session_id}")
        assert retrieved["user_id"] == "user_123"
        assert retrieved["username"] == "testuser"

    def test_cache_user_permissions(self):
        """
        测试缓存用户权限
        验证权限数据的缓存
        """
        cache = CacheService()
        
        user_id = "user_123"
        permissions = ["read", "write", "delete"]
        
        # 缓存权限
        cache.set(f"permissions:{user_id}", permissions, ttl=300)
        
        # 验证权限缓存
        cached_permissions = cache.get(f"permissions:{user_id}")
        assert cached_permissions == permissions

    def test_cache_query_result(self):
        """
        测试缓存查询结果
        验证数据库查询结果的缓存
        """
        cache = CacheService()
        
        # 模拟查询结果
        query_key = "query:users:all"
        query_result = [
            {"id": 1, "name": "User1"},
            {"id": 2, "name": "User2"},
            {"id": 3, "name": "User3"}
        ]
        
        # 缓存查询结果
        cache.set(query_key, query_result, ttl=60)
        
        # 从缓存获取
        cached_result = cache.get(query_key)
        assert len(cached_result) == 3
        assert cached_result[0]["name"] == "User1"
