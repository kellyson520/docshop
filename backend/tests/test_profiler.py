"""
性能分析器模块测试

测试覆盖率目标：100%
- DiffProfiler 类初始化
- record_metric 记录指标
- get_metrics 获取指标
- get_statistics 获取统计
- enable/disable 启用禁用
- clear_metrics 清空指标
- @profile_diff 装饰器功能
- get_profiler 获取实例
- print_statistics 打印统计
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.diff_engine.profiler import (
    DiffProfiler,
    PerformanceMetrics,
    profile_diff,
    get_profiler,
    print_statistics,
)


class TestPerformanceMetrics:
    """PerformanceMetrics 数据类测试"""

    def test_metrics_creation(self):
        """测试指标创建"""
        metric = PerformanceMetrics(
            function_name="test_func",
            execution_time=1.234,
            timestamp=1234567890.0,
            success=True,
            error_message=None
        )
        assert metric.function_name == "test_func"
        assert metric.execution_time == 1.234
        assert metric.timestamp == 1234567890.0
        assert metric.success is True
        assert metric.error_message is None

    def test_metrics_to_dict(self):
        """测试指标转换为字典"""
        metric = PerformanceMetrics(
            function_name="test_func",
            execution_time=1.234567,
            timestamp=1234567890.0,
            success=True,
            error_message=None
        )
        result = metric.to_dict()
        assert result["function_name"] == "test_func"
        assert result["execution_time"] == 1.235  # 四舍五入到3位小数
        assert result["timestamp"] == 1234567890.0
        assert result["success"] is True
        assert result["error_message"] is None

    def test_metrics_to_dict_with_error(self):
        """测试带错误信息的指标转换"""
        metric = PerformanceMetrics(
            function_name="test_func",
            execution_time=2.0,
            timestamp=1234567890.0,
            success=False,
            error_message="Test error"
        )
        result = metric.to_dict()
        assert result["success"] is False
        assert result["error_message"] == "Test error"


class TestDiffProfiler:
    """DiffProfiler 类测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        # 重置单例状态
        DiffProfiler._instance = None
        DiffProfiler._lock = threading.Lock()

    def teardown_method(self):
        """每个测试后清理"""
        DiffProfiler._instance = None

    def test_singleton_pattern(self):
        """测试单例模式"""
        profiler1 = DiffProfiler()
        profiler2 = DiffProfiler()
        assert profiler1 is profiler2

    def test_thread_safe_singleton(self):
        """测试线程安全的单例模式"""
        profilers = []
        
        def create_profiler():
            profilers.append(DiffProfiler())
        
        threads = [threading.Thread(target=create_profiler) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有实例应该是同一个
        assert all(p is profilers[0] for p in profilers)

    def test_initialization(self):
        """测试初始化"""
        profiler = DiffProfiler()
        assert profiler._initialized is True
        assert profiler._metrics == []
        assert profiler._enabled is True
        assert profiler._max_metrics == 1000

    def test_initialization_only_once(self):
        """测试初始化只执行一次"""
        profiler = DiffProfiler()
        profiler._metrics.append("test")  # 修改状态
        
        # 再次获取实例，状态应该保持不变
        profiler2 = DiffProfiler()
        assert profiler2._metrics == ["test"]

    def test_record_metric(self):
        """测试记录指标"""
        profiler = DiffProfiler()
        metric = PerformanceMetrics(
            function_name="test_func",
            execution_time=1.0,
            timestamp=1234567890.0,
            success=True
        )
        profiler.record_metric(metric)
        assert len(profiler._metrics) == 1
        assert profiler._metrics[0] == metric

    def test_record_metric_when_disabled(self):
        """测试禁用时记录指标"""
        profiler = DiffProfiler()
        profiler.disable()
        metric = PerformanceMetrics(
            function_name="test_func",
            execution_time=1.0,
            timestamp=1234567890.0,
            success=True
        )
        profiler.record_metric(metric)
        assert len(profiler._metrics) == 0

    def test_record_metric_max_limit(self):
        """测试记录指标最大限制"""
        profiler = DiffProfiler()
        profiler._max_metrics = 5
        
        for i in range(10):
            metric = PerformanceMetrics(
                function_name=f"test_func_{i}",
                execution_time=float(i),
                timestamp=1234567890.0 + i,
                success=True
            )
            profiler.record_metric(metric)
        
        assert len(profiler._metrics) == 5
        # 应该保留最后的5个
        assert profiler._metrics[0].function_name == "test_func_5"
        assert profiler._metrics[4].function_name == "test_func_9"

    def test_get_metrics_all(self):
        """测试获取所有指标"""
        profiler = DiffProfiler()
        metric1 = PerformanceMetrics("func1", 1.0, 1234567890.0, True)
        metric2 = PerformanceMetrics("func2", 2.0, 1234567891.0, True)
        profiler.record_metric(metric1)
        profiler.record_metric(metric2)
        
        result = profiler.get_metrics()
        assert len(result) == 2
        assert result[0].function_name == "func1"
        assert result[1].function_name == "func2"

    def test_get_metrics_filtered(self):
        """测试按函数名过滤指标"""
        profiler = DiffProfiler()
        metric1 = PerformanceMetrics("func1", 1.0, 1234567890.0, True)
        metric2 = PerformanceMetrics("func2", 2.0, 1234567891.0, True)
        metric3 = PerformanceMetrics("func1", 3.0, 1234567892.0, True)
        profiler.record_metric(metric1)
        profiler.record_metric(metric2)
        profiler.record_metric(metric3)
        
        result = profiler.get_metrics("func1")
        assert len(result) == 2
        assert all(m.function_name == "func1" for m in result)

    def test_get_statistics_empty(self):
        """测试空指标的统计信息"""
        profiler = DiffProfiler()
        result = profiler.get_statistics()
        assert result == {"message": "No metrics recorded"}

    def test_get_statistics_with_data(self):
        """测试有数据时的统计信息"""
        profiler = DiffProfiler()
        
        # 添加成功和失败的指标
        profiler.record_metric(PerformanceMetrics("func1", 1.0, 1234567890.0, True))
        profiler.record_metric(PerformanceMetrics("func1", 2.0, 1234567891.0, True))
        profiler.record_metric(PerformanceMetrics("func1", 3.0, 1234567892.0, False))
        profiler.record_metric(PerformanceMetrics("func2", 5.0, 1234567893.0, True))
        
        result = profiler.get_statistics()
        
        assert "func1" in result
        assert "func2" in result
        
        # func1 的统计
        assert result["func1"]["call_count"] == 3
        assert result["func1"]["total_time"] == 6.0
        assert result["func1"]["avg_time"] == 2.0
        assert result["func1"]["success_rate"] == 66.67
        assert result["func1"]["failure_count"] == 1
        
        # func2 的统计
        assert result["func2"]["call_count"] == 1
        assert result["func2"]["total_time"] == 5.0
        assert result["func2"]["avg_time"] == 5.0
        assert result["func2"]["success_rate"] == 100.0
        assert result["func2"]["failure_count"] == 0

    def test_clear_metrics(self):
        """测试清空指标"""
        profiler = DiffProfiler()
        metric = PerformanceMetrics("func1", 1.0, 1234567890.0, True)
        profiler.record_metric(metric)
        assert len(profiler._metrics) == 1
        
        profiler.clear_metrics()
        assert len(profiler._metrics) == 0

    def test_enable_disable(self):
        """测试启用和禁用"""
        profiler = DiffProfiler()
        
        # 默认启用
        assert profiler._enabled is True
        
        # 禁用
        profiler.disable()
        assert profiler._enabled is False
        
        # 启用
        profiler.enable()
        assert profiler._enabled is True

    def test_thread_safety_record_metric(self):
        """测试记录指标的线程安全"""
        profiler = DiffProfiler()
        
        def record_metrics():
            for i in range(100):
                metric = PerformanceMetrics(
                    function_name="test_func",
                    execution_time=1.0,
                    timestamp=1234567890.0 + i,
                    success=True
                )
                profiler.record_metric(metric)
        
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 5个线程各记录100个指标，但受max_metrics=1000限制
        # 实际应该记录500个（5*100=500），但不超过最大限制
        assert len(profiler._metrics) == 500


class TestProfileDiffDecorator:
    """@profile_diff 装饰器测试"""

    def setup_method(self):
        """每个测试前重置"""
        DiffProfiler._instance = None
        DiffProfiler._lock = threading.Lock()

    def teardown_method(self):
        """每个测试后清理"""
        DiffProfiler._instance = None

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_success(self, mock_logger):
        """测试装饰器成功场景"""
        
        @profile_diff
        def test_function():
            time.sleep(0.01)  # 模拟一些执行时间
            return {"result": "success"}
        
        result = test_function()
        
        assert result["result"] == "success"
        assert "stats" in result
        assert "processing_time" in result["stats"]
        assert result["stats"]["processing_time"] > 0
        
        # 验证日志记录
        assert mock_logger.info.called

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_with_dict_result(self, mock_logger):
        """测试返回字典结果时添加处理时间"""
        
        @profile_diff
        def test_function():
            return {"data": "test"}
        
        result = test_function()
        
        assert "data" in result
        assert "stats" in result
        assert "processing_time" in result["stats"]

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_with_existing_stats(self, mock_logger):
        """测试已有stats字段的情况"""
        
        @profile_diff
        def test_function():
            return {"stats": {"existing": "value"}}
        
        result = test_function()
        
        assert result["stats"]["existing"] == "value"
        assert "processing_time" in result["stats"]

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_non_dict_result(self, mock_logger):
        """测试非字典返回结果"""
        
        @profile_diff
        def test_function():
            return "string result"
        
        result = test_function()
        
        # 非字典结果不应该被修改
        assert result == "string result"

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_exception(self, mock_logger):
        """测试装饰器异常场景"""
        
        @profile_diff
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            test_function()
        
        # 验证错误日志
        assert mock_logger.error.called

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_records_metric(self, mock_logger):
        """测试装饰器记录性能指标"""
        profiler = DiffProfiler()
        
        @profile_diff
        def test_function():
            return {"result": "success"}
        
        test_function()
        
        # 验证指标被记录
        metrics = profiler.get_metrics()
        assert len(metrics) == 1
        assert "test_profile_diff_records_metric.<locals>.test_function" in metrics[0].function_name
        assert metrics[0].success is True

    @patch("app.diff_engine.profiler.logger")
    def test_profile_diff_records_failed_metric(self, mock_logger):
        """测试失败时记录性能指标"""
        profiler = DiffProfiler()
        
        @profile_diff
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function()
        
        # 验证失败指标被记录
        metrics = profiler.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].success is False
        assert metrics[0].error_message == "Test error"

    def test_profile_diff_preserves_function_metadata(self):
        """测试装饰器保留函数元数据"""
        
        @profile_diff
        def my_test_function():
            """This is a test function"""
            return "test"
        
        assert my_test_function.__name__ == "my_test_function"
        assert my_test_function.__doc__ == "This is a test function"


class TestGetProfiler:
    """get_profiler 函数测试"""

    def setup_method(self):
        """每个测试前重置"""
        DiffProfiler._instance = None
        DiffProfiler._lock = threading.Lock()

    def teardown_method(self):
        """每个测试后清理"""
        DiffProfiler._instance = None

    def test_get_profiler_returns_instance(self):
        """测试获取分析器实例"""
        profiler = get_profiler()
        assert isinstance(profiler, DiffProfiler)

    def test_get_profiler_returns_same_instance(self):
        """测试获取相同的实例"""
        profiler1 = get_profiler()
        profiler2 = get_profiler()
        assert profiler1 is profiler2


class TestPrintStatistics:
    """print_statistics 函数测试"""

    def setup_method(self):
        """每个测试前重置"""
        DiffProfiler._instance = None
        DiffProfiler._lock = threading.Lock()

    def teardown_method(self):
        """每个测试后清理"""
        DiffProfiler._instance = None

    @patch("app.diff_engine.profiler.logger")
    def test_print_statistics(self, mock_logger):
        """测试打印统计信息"""
        profiler = get_profiler()
        
        # 添加一些指标
        profiler.record_metric(PerformanceMetrics("func1", 1.0, 1234567890.0, True))
        profiler.record_metric(PerformanceMetrics("func1", 2.0, 1234567891.0, True))
        
        print_statistics()
        
        # 验证日志被记录
        assert mock_logger.info.called
        # 应该记录统计信息
        calls = [call for call in mock_logger.info.call_args_list]
        assert len(calls) > 0

    @patch("app.diff_engine.profiler.logger")
    def test_print_statistics_empty(self, mock_logger):
        """测试空统计信息"""
        print_statistics()
        
        # 当统计为空时，get_statistics 返回 {"message": "No metrics recorded"}
        # 这是一个字典，但 print_statistics 会尝试遍历它
        # 验证至少调用了日志记录
        assert mock_logger.info.called
