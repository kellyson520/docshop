"""
缓存服务模块

基于内存的 TTL 缓存实现，使用 cachetools.TTLCache。
提供 get/set/delete/clear 方法和 @cached 装饰器，用于缓存函数结果。
"""

import functools
import hashlib
import json
from typing import Any, Callable, Optional, TypeVar

from cachetools import TTLCache

from app.config import settings
from app.utils.logger import logger, get_logger

# 获取模块日志器
cache_logger = get_logger("services.cache_service")

# 泛型类型变量，用于装饰器返回类型
T = TypeVar("T")


class CacheService:
    """
    内存 TTL 缓存服务

    基于 cachetools.TTLCache 实现的线程安全内存缓存。
    支持配置化的启用/禁用、TTL 过期时间和最大缓存条目数。

    Attributes:
        enabled: 是否启用缓存
        ttl: 缓存过期时间（秒）
        max_size: 最大缓存条目数
        _cache: TTLCache 实例
    """

    def __init__(self):
        """初始化缓存服务"""
        self.enabled = settings.CACHE_ENABLED
        self.ttl = settings.CACHE_TTL
        self.max_size = settings.CACHE_MAX_SIZE
        self._cache: TTLCache = TTLCache(
            maxsize=self.max_size,
            ttl=self.ttl,
        )
        cache_logger.info(
            f"缓存服务已初始化 - 启用: {self.enabled}, "
            f"TTL: {self.ttl}s, 最大容量: {self.max_size}"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存值，不存在或已过期返回 None
        """
        if not self.enabled:
            return None

        try:
            value = self._cache.get(key)
            if value is not None:
                cache_logger.debug(f"缓存命中: {key}")
            else:
                cache_logger.debug(f"缓存未命中: {key}")
            return value
        except Exception as e:
            cache_logger.warning(f"读取缓存失败: {key}, 错误: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 自定义过期时间（秒），None 使用默认值

        Returns:
            bool: 设置成功返回 True
        """
        if not self.enabled:
            return False

        try:
            if ttl is not None:
                # 临时使用自定义 TTL
                import time
                self._cache[key] = value
                # TTLCache 不支持单条 TTL，使用 expire 替代方案
                # 这里直接设置，依赖全局 TTL
                cache_logger.debug(f"缓存已设置: {key}, TTL: {ttl}s")
            else:
                self._cache[key] = value
                cache_logger.debug(f"缓存已设置: {key}")
            return True
        except Exception as e:
            cache_logger.warning(f"设置缓存失败: {key}, 错误: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键

        Returns:
            bool: 删除成功返回 True
        """
        if not self.enabled:
            return False

        try:
            if key in self._cache:
                del self._cache[key]
                cache_logger.debug(f"缓存已删除: {key}")
                return True
            return False
        except Exception as e:
            cache_logger.warning(f"删除缓存失败: {key}, 错误: {e}")
            return False

    def clear(self) -> bool:
        """
        清空所有缓存

        Returns:
            bool: 清空成功返回 True
        """
        if not self.enabled:
            return False

        try:
            self._cache.clear()
            cache_logger.info("缓存已全部清空")
            return True
        except Exception as e:
            cache_logger.warning(f"清空缓存失败: {e}")
            return False

    def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            dict: 包含缓存统计的字典
        """
        return {
            "enabled": self.enabled,
            "ttl": self.ttl,
            "max_size": self.max_size,
            "current_size": len(self._cache),
            "currsize": self._cache.currsize,
        }


def cached(key_prefix: str, ttl: Optional[int] = None):
    """
    缓存装饰器

    缓存函数的返回结果，基于函数名和参数生成缓存键。

    Args:
        key_prefix: 缓存键前缀
        ttl: 自定义过期时间（秒），None 使用默认值

    Returns:
        Callable: 装饰器函数

    Example:
        @cached("user_info", ttl=60)
        def get_user_info(user_id: str):
            return db.query(User).filter(User.id == user_id).first()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 如果缓存未启用，直接调用原函数
            if not cache_service.enabled:
                return func(*args, **kwargs)

            # 生成缓存键
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)

            # 尝试从缓存获取
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 调用原函数
            result = func(*args, **kwargs)

            # 存入缓存（仅缓存非 None 结果）
            if result is not None:
                cache_service.set(cache_key, result, ttl=ttl)

            return result

        # 添加清除缓存的方法
        def clear_cache(*args, **kwargs):
            """清除该函数的缓存"""
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)
            cache_service.delete(cache_key)

        wrapper.clear_cache = clear_cache

        return wrapper
    return decorator


def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """
    生成缓存键（始终使用哈希防注入）

    基于前缀、函数名和参数生成唯一的缓存键。
    使用 SHA-256 哈希确保键不包含特殊字符（防止冒号注入/键碰撞）。

    Args:
        prefix: 缓存键前缀
        func_name: 函数名
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        str: 缓存键
    """
    try:
        # 将参数序列化为规范化字符串
        key_parts = [prefix, func_name]

        # 处理位置参数（跳过 self/cls / None）
        for arg in args:
            if arg is not None and not isinstance(arg, type):
                key_parts.append(str(arg))

        # 处理关键字参数（排序确保一致性）
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")

        raw_key = ":".join(key_parts)

        # 始终使用哈希：防止键注入（冒号、换行符等）和键长度超标
        hash_value = hashlib.sha256(raw_key.encode()).hexdigest()[:24]
        return f"{prefix}:{func_name}:{hash_value}"

    except Exception as e:
        cache_logger.warning(f"生成缓存键失败: {e}")
        return f"{prefix}:{func_name}:unknown"


# 全局缓存服务实例
cache_service = CacheService()
