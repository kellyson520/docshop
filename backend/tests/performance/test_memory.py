"""
内存使用测试 - 监控系统在各种负载下的内存表现

测试场景：
1. 大文件上传下载时的内存使用
2. 大量并发请求时的内存使用
3. 数据库查询时的内存使用
4. 长时间运行时的内存泄漏检测

运行方式：
    pytest tests/performance/test_memory.py -v
"""

import pytest
import time
import gc
import io
import os
import random
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

import psutil
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.utils.time import utc_now, utc_now_iso
from app.main import app
from app.database import Base, get_db
from app.models import User, Project, DocumentFile, FileVersion
from app.deps.auth import get_password_hash, create_access_token


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_memory_performance.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
engine = engine.execution_options(legacy_bare_lists=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def db():
    """创建测试数据库会话"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    """创建测试用户"""
    user = User(
        id=f"test-user-{random.randint(1000, 9999)}",
        username=f"testuser_{random.randint(1000, 9999)}",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        created_at=utc_now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """创建认证请求头"""
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_project(db, test_user):
    """创建测试项目"""
    project = Project(
        id=f"test-project-{random.randint(1000, 9999)}",
        name=f"测试项目_{random.randint(1000, 9999)}",
        owner_id=test_user.id,
        created_at=utc_now()
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.initial_memory = None
        self.measurements: List[float] = []
    
    def start(self):
        """开始监控"""
        gc.collect()  # 强制垃圾回收
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.measurements = [self.initial_memory]
    
    def measure(self) -> float:
        """测量当前内存使用"""
        current = self.process.memory_info().rss / 1024 / 1024  # MB
        self.measurements.append(current)
        return current
    
    def get_peak_memory(self) -> float:
        """获取峰值内存"""
        return max(self.measurements) if self.measurements else 0
    
    def get_memory_increase(self) -> float:
        """获取内存增长"""
        if not self.initial_memory or not self.measurements:
            return 0
        return self.get_peak_memory() - self.initial_memory
    
    def get_stats(self) -> Dict:
        """获取内存统计信息"""
        if not self.measurements:
            return {}
        return {
            "initial_mb": self.initial_memory,
            "peak_mb": self.get_peak_memory(),
            "increase_mb": self.get_memory_increase(),
            "measurements": len(self.measurements)
        }


# ========== 大文件操作内存测试 ==========

class TestLargeFileMemory:
    """大文件操作内存测试"""
    
    def test_small_file_upload_memory(self, auth_headers, test_project):
        """测试小文件上传时的内存使用（100KB）"""
        monitor = MemoryMonitor()
        monitor.start()
        
        file_content = b"%PDF-1.4\n" + b"x" * (100 * 1024)
        
        # 上传10个文件
        for i in range(10):
            response = client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"memory_test_{i}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
            assert response.status_code == 201
            monitor.measure()
        
        stats = monitor.get_stats()
        # 100KB文件上传，内存增长应该小于 50MB
        assert stats["increase_mb"] < 50, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_medium_file_upload_memory(self, auth_headers, test_project):
        """测试中等文件上传时的内存使用（1MB）"""
        monitor = MemoryMonitor()
        monitor.start()
        
        file_content = b"%PDF-1.4\n" + b"x" * (1024 * 1024)
        
        # 上传5个文件
        for i in range(5):
            response = client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"medium_test_{i}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
            assert response.status_code == 201
            monitor.measure()
        
        stats = monitor.get_stats()
        # 1MB文件上传，内存增长应该小于 100MB
        assert stats["increase_mb"] < 100, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_large_file_upload_memory(self, auth_headers, test_project):
        """测试大文件上传时的内存使用（5MB）"""
        monitor = MemoryMonitor()
        monitor.start()
        
        file_content = b"%PDF-1.4\n" + b"x" * (5 * 1024 * 1024)
        
        response = client.post(
            f"/api/v1/projects/{test_project.id}/files",
            files={"file": ("large_test.pdf", io.BytesIO(file_content), "application/pdf")},
            headers=auth_headers
        )
        
        final_memory = monitor.measure()
        stats = monitor.get_stats()
        
        assert response.status_code == 201
        # 5MB文件上传，内存增长应该小于 200MB
        assert stats["increase_mb"] < 200, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_multiple_files_upload_memory(self, auth_headers, test_project):
        """测试多文件并发上传时的内存使用"""
        monitor = MemoryMonitor()
        monitor.start()
        
        file_contents = [
            (f"multi_test_{i}.pdf", b"%PDF-1.4\n" + b"x" * (200 * 1024))
            for i in range(10)
        ]
        
        def upload_file(file_info):
            filename, content = file_info
            return client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (filename, io.BytesIO(content), "application/pdf")},
                headers=auth_headers
            )
        
        # 并发上传
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(upload_file, file_contents))
        
        monitor.measure()
        stats = monitor.get_stats()
        
        # 所有上传应该成功
        assert all(r.status_code == 201 for r in results)
        # 并发上传，内存增长应该小于 150MB
        assert stats["increase_mb"] < 150, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"


# ========== 数据库操作内存测试 ==========

class TestDatabaseMemory:
    """数据库操作内存测试"""
    
    def test_bulk_insert_memory(self, db, test_user):
        """测试批量插入时的内存使用"""
        monitor = MemoryMonitor()
        monitor.start()
        
        # 批量插入1000个项目
        projects = []
        for i in range(1000):
            project = Project(
                id=f"bulk-project-{i}",
                name=f"批量测试项目{i}",
                owner_id=test_user.id,
                created_at=utc_now()
            )
            projects.append(project)
        
        db.add_all(projects)
        db.commit()
        
        monitor.measure()
        stats = monitor.get_stats()
        
        # 批量插入1000条记录，内存增长应该小于 50MB
        assert stats["increase_mb"] < 50, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_large_query_memory(self, db, test_user):
        """测试大量数据查询时的内存使用"""
        # 先插入测试数据
        for i in range(500):
            project = Project(
                id=f"query-project-{i}",
                name=f"查询测试项目{i}" * 10,  # 增大记录大小
                description=f"描述{i}" * 50,
                owner_id=test_user.id,
                created_at=utc_now()
            )
            db.add(project)
        db.commit()
        
        monitor = MemoryMonitor()
        monitor.start()
        
        # 查询所有数据
        results = db.query(Project).filter(Project.owner_id == test_user.id).all()
        
        monitor.measure()
        stats = monitor.get_stats()
        
        assert len(results) == 500
        # 查询500条大记录，内存增长应该小于 100MB
        assert stats["increase_mb"] < 100, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_pagination_memory_efficiency(self, db, test_user):
        """测试分页查询的内存效率"""
        # 插入大量数据
        for i in range(1000):
            project = Project(
                id=f"page-mem-project-{i}",
                name=f"分页内存测试项目{i}",
                owner_id=test_user.id,
                created_at=utc_now()
            )
            db.add(project)
        db.commit()
        
        monitor = MemoryMonitor()
        monitor.start()
        
        # 分页查询，每次100条
        all_results = []
        for offset in range(0, 1000, 100):
            page = db.query(Project).filter(
                Project.owner_id == test_user.id
            ).offset(offset).limit(100).all()
            all_results.extend(page)
            monitor.measure()
        
        stats = monitor.get_stats()
        
        assert len(all_results) == 1000
        # 分页查询应该比一次性查询内存效率高
        assert stats["increase_mb"] < 200, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"


# ========== 并发请求内存测试 ==========

class TestConcurrentMemory:
    """并发请求内存测试"""
    
    def test_concurrent_api_calls_memory(self, auth_headers, db, test_user):
        """测试并发API调用时的内存使用"""
        # 创建测试数据
        for i in range(100):
            project = Project(
                id=f"concurrent-mem-project-{i}",
                name=f"并发内存测试项目{i}",
                owner_id=test_user.id,
                created_at=utc_now()
            )
            db.add(project)
        db.commit()
        
        monitor = MemoryMonitor()
        monitor.start()
        
        def make_request(_):
            return client.get("/api/v1/projects", headers=auth_headers)
        
        # 并发发起20个请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, range(20)))
        
        monitor.measure()
        stats = monitor.get_stats()
        
        # 所有请求应该成功
        assert all(r.status_code == 200 for r in results)
        # 20个并发请求，内存增长应该小于 100MB
        assert stats["increase_mb"] < 100, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_rapid_requests_memory(self, auth_headers):
        """测试快速连续请求时的内存使用"""
        monitor = MemoryMonitor()
        monitor.start()
        
        # 快速发起50个请求
        for i in range(50):
            response = client.get("/api/v1/auth/me", headers=auth_headers)
            if i % 10 == 0:
                monitor.measure()
        
        stats = monitor.get_stats()
        
        # 快速请求，内存增长应该小于 50MB
        assert stats["increase_mb"] < 50, f"内存增长 {stats['increase_mb']:.2f}MB 超过阈值"


# ========== 内存泄漏检测测试 ==========

class TestMemoryLeak:
    """内存泄漏检测测试"""
    
    def test_repeated_operations_memory_leak(self, auth_headers, test_project):
        """测试重复操作是否存在内存泄漏"""
        file_content = b"%PDF-1.4\n" + b"x" * (50 * 1024)
        
        memory_readings = []
        
        # 重复执行操作10次
        for iteration in range(10):
            # 上传文件
            response = client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"leak_test_{iteration}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
            assert response.status_code == 201
            
            # 强制垃圾回收并记录内存
            gc.collect()
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_readings.append(memory_mb)
        
        # 分析内存趋势
        # 如果内存持续增长，可能存在泄漏
        first_half_avg = sum(memory_readings[:5]) / 5
        second_half_avg = sum(memory_readings[5:]) / 5
        
        # 后半段平均内存不应该比前半段高出太多（允许30%增长）
        memory_growth_ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1
        assert memory_growth_ratio < 1.3, f"可能存在内存泄漏，内存增长比例: {memory_growth_ratio:.2f}"
    
    def test_database_session_memory_leak(self, db, test_user):
        """测试数据库会话是否存在内存泄漏"""
        memory_readings = []
        
        for iteration in range(20):
            # 创建和查询数据
            project = Project(
                id=f"leak-check-project-{iteration}",
                name=f"泄漏检测项目{iteration}",
                owner_id=test_user.id,
                created_at=utc_now()
            )
            db.add(project)
            db.commit()
            
            # 查询数据
            result = db.query(Project).filter(Project.id == project.id).first()
            assert result is not None
            
            # 记录内存
            if iteration % 5 == 0:
                gc.collect()
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_readings.append(memory_mb)
        
        # 检查内存趋势
        if len(memory_readings) >= 2:
            memory_increase = memory_readings[-1] - memory_readings[0]
            # 20次操作，内存增长应该小于 30MB
            assert memory_increase < 30, f"可能存在内存泄漏，内存增长: {memory_increase:.2f}MB"


# ========== 长时间运行内存测试 ==========

class TestLongRunningMemory:
    """长时间运行内存测试"""
    
    def test_sustained_operations_memory(self, auth_headers, test_project):
        """测试持续操作时的内存稳定性"""
        file_content = b"%PDF-1.4\n" + b"x" * (30 * 1024)
        
        monitor = MemoryMonitor()
        monitor.start()
        
        # 模拟持续操作（30次文件上传）
        for i in range(30):
            response = client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"sustained_{i}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
            assert response.status_code == 201
            
            # 每10次记录一次内存
            if i % 10 == 0:
                monitor.measure()
        
        # 最后测量
        gc.collect()
        monitor.measure()
        stats = monitor.get_stats()
        
        # 30次操作，内存增长应该小于 80MB
        assert stats["increase_mb"] < 80, f"持续操作内存增长 {stats['increase_mb']:.2f}MB 超过阈值"
    
    def test_memory_after_cleanup(self, auth_headers, test_project):
        """测试清理后的内存释放情况"""
        file_content = b"%PDF-1.4\n" + b"x" * (100 * 1024)
        
        monitor = MemoryMonitor()
        monitor.start()
        
        file_ids = []
        
        # 上传文件
        for i in range(10):
            response = client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"cleanup_{i}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
            assert response.status_code == 201
            file_id = response.json().get("data", {}).get("id")
            if file_id:
                file_ids.append(file_id)
        
        peak_memory = monitor.measure()
        
        # 删除文件
        for file_id in file_ids:
            client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)
        
        # 强制垃圾回收
        gc.collect()
        time.sleep(0.5)  # 给系统时间释放资源
        
        final_memory = monitor.measure()
        
        # 删除后内存应该有所下降（允许保留80%）
        memory_released = peak_memory - final_memory
        assert memory_released > 0 or final_memory < peak_memory * 1.1, "内存可能未正确释放"


# ========== 内存报告生成 ==========

@pytest.fixture(scope="session", autouse=True)
def memory_report():
    """生成内存测试报告"""
    yield
    
    # 测试结束后输出内存使用摘要
    print("\n" + "="*60)
    print("内存测试报告")
    print("="*60)
    
    process = psutil.Process(os.getpid())
    final_memory = process.memory_info().rss / 1024 / 1024
    
    print(f"最终内存使用: {final_memory:.2f} MB")
    print(f"内存信息:")
    print(f"  - RSS: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"  - VMS: {process.memory_info().vms / 1024 / 1024:.2f} MB")
    print("="*60)
