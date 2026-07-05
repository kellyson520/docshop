"""
Diff 引擎性能分析器

提供性能监控、统计收集和分析功能
"""

import time
import functools
import threading
from typing import Callable, Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from app.utils.logger import logger


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    function_name: str
    execution_time: float
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "function_name": self.function_name,
            "execution_time": round(self.execution_time, 3),
            "timestamp": self.timestamp,
            "success": self.success,
            "error_message": self.error_message
        }


class DiffProfiler:
    """Diff 引擎性能分析器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._metrics: List[PerformanceMetrics] = []
        self._metrics_lock = threading.Lock()
        self._enabled = True
        self._max_metrics = 1000  # 最大保存指标数
    
    def record_metric(self, metric: PerformanceMetrics) -> None:
        """
        记录性能指标
        
        Args:
            metric: 性能指标对象
        """
        if not self._enabled:
            return
        
        with self._metrics_lock:
            self._metrics.append(metric)
            # 限制列表大小
            if len(self._metrics) > self._max_metrics:
                self._metrics = self._metrics[-self._max_metrics:]
    
    def get_metrics(self, function_name: Optional[str] = None) -> List[PerformanceMetrics]:
        """
        获取性能指标
        
        Args:
            function_name: 函数名称过滤，为 None 则返回所有
            
        Returns:
            性能指标列表
        """
        with self._metrics_lock:
            if function_name:
                return [m for m in self._metrics if m.function_name == function_name]
            return self._metrics.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        with self._metrics_lock:
            if not self._metrics:
                return {"message": "No metrics recorded"}
            
            stats = defaultdict(lambda: {"count": 0, "total_time": 0.0, "success": 0, "failures": 0})
            
            for metric in self._metrics:
                func_stats = stats[metric.function_name]
                func_stats["count"] += 1
                func_stats["total_time"] += metric.execution_time
                if metric.success:
                    func_stats["success"] += 1
                else:
                    func_stats["failures"] += 1
            
            # 计算平均值
            result = {}
            for func_name, func_stats in stats.items():
                result[func_name] = {
                    "call_count": func_stats["count"],
                    "total_time": round(func_stats["total_time"], 3),
                    "avg_time": round(func_stats["total_time"] / func_stats["count"], 3) if func_stats["count"] > 0 else 0,
                    "success_rate": round(func_stats["success"] / func_stats["count"] * 100, 2) if func_stats["count"] > 0 else 0,
                    "failure_count": func_stats["failures"]
                }
            
            return result
    
    def clear_metrics(self) -> None:
        """清空所有指标"""
        with self._metrics_lock:
            self._metrics.clear()
    
    def enable(self) -> None:
        """启用性能监控"""
        self._enabled = True
    
    def disable(self) -> None:
        """禁用性能监控"""
        self._enabled = False


def profile_diff(func: Callable) -> Callable:
    """
    Diff 函数性能分析装饰器
    
    用于装饰 Diff 引擎的 compare 方法，自动记录执行时间和成功率
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        profiler = DiffProfiler()
        function_name = func.__qualname__
        
        logger.info(f"[DiffProfiler] Starting {function_name}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 记录性能指标
            metric = PerformanceMetrics(
                function_name=function_name,
                execution_time=execution_time,
                timestamp=time.time(),
                success=True
            )
            profiler.record_metric(metric)
            
            logger.info(f"[DiffProfiler] {function_name} completed in {execution_time:.3f}s")
            
            # 将处理时间添加到结果中
            if isinstance(result, dict):
                if 'stats' not in result:
                    result['stats'] = {}
                result['stats']['processing_time'] = round(execution_time, 3)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 记录失败指标
            metric = PerformanceMetrics(
                function_name=function_name,
                execution_time=execution_time,
                timestamp=time.time(),
                success=False,
                error_message=str(e)
            )
            profiler.record_metric(metric)
            
            logger.error(f"[DiffProfiler] {function_name} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


def get_profiler() -> DiffProfiler:
    """
    获取性能分析器实例
    
    Returns:
        DiffProfiler 单例实例
    """
    return DiffProfiler()


def print_statistics() -> None:
    """打印性能统计信息到日志"""
    profiler = get_profiler()
    stats = profiler.get_statistics()
    
    # 检查是否为空统计
    if "message" in stats:
        logger.info(f"[DiffProfiler] {stats['message']}")
        return
    
    logger.info("[DiffProfiler] Performance Statistics:")
    for func_name, func_stats in stats.items():
        logger.info(f"  {func_name}:")
        logger.info(f"    Calls: {func_stats['call_count']}")
        logger.info(f"    Total Time: {func_stats['total_time']}s")
        logger.info(f"    Avg Time: {func_stats['avg_time']}s")
        logger.info(f"    Success Rate: {func_stats['success_rate']}%")
