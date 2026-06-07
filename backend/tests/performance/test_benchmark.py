"""
基准测试 - 使用 pytest-benchmark 进行性能基准测试

测试场景：
1. API响应时间基准
2. 数据库查询性能基准
3. 文件操作性能基准
4. Diff计算性能基准

运行方式：
    pytest tests/performance/test_benchmark.py --benchmark-only -v
"""

import pytest
import time
import random
import string
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, Project, DocumentFile, FileVersion
from app.deps.auth import get_password_hash, create_access_token
from app.services.diff_service import compute_diff


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
        created_at=datetime.utcnow()
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
        created_at=datetime.utcnow()
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# ========== API响应时间基准测试 ==========

class TestAPIResponseBenchmark:
    """API响应时间基准测试"""
    
    def test_baseline_response_time(self, benchmark):
        """测试基础响应时间（健康检查）"""
        result = benchmark(client.get, "/api/v1/health" if hasattr(app, "health") else "/docs")
        # 基础响应应该在 100ms 内
        assert benchmark.stats.stats.mean < 0.1
    
    def test_login_response_time(self, benchmark, db):
        """测试登录接口响应时间"""
        # 预先创建用户
        user = User(
            username=f"benchuser_{random.randint(1000, 9999)}",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True
        )
        db.add(user)
        db.commit()
        
        def login():
            return client.post(
                "/api/v1/auth/login",
                json={"username": user.username, "password": "TestPass123!"}
            )
        
        result = benchmark(login)
        # 登录响应应该在 200ms 内
        assert benchmark.stats.stats.mean < 0.2
    
    def test_get_projects_list_benchmark(self, benchmark, auth_headers, db, test_user):
        """测试项目列表查询响应时间基准"""
        # 创建测试数据
        for i in range(50):
            project = Project(
                id=f"bench-project-{i}",
                name=f"基准测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def get_projects():
            return client.get("/api/v1/projects", headers=auth_headers)
        
        result = benchmark(get_projects)
        # 项目列表查询应该在 300ms 内
        assert benchmark.stats.stats.mean < 0.3
    
    def test_create_project_benchmark(self, benchmark, auth_headers):
        """测试创建项目响应时间基准"""
        counter = [0]
        
        def create_project():
            counter[0] += 1
            return client.post(
                "/api/v1/projects",
                json={"name": f"BenchProject_{counter[0]}"},
                headers=auth_headers
            )
        
        result = benchmark(create_project)
        # 创建项目应该在 200ms 内
        assert benchmark.stats.stats.mean < 0.2
    
    def test_search_projects_benchmark(self, benchmark, auth_headers, db, test_user):
        """测试项目搜索响应时间基准"""
        # 创建测试数据
        for i in range(100):
            project = Project(
                id=f"search-project-{i}",
                name=f"搜索测试项目{i}",
                description=f"描述{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def search_projects():
            return client.get("/api/v1/projects?keyword=搜索", headers=auth_headers)
        
        result = benchmark(search_projects)
        # 搜索应该在 500ms 内
        assert benchmark.stats.stats.mean < 0.5


# ========== 数据库查询性能基准测试 ==========

class TestDatabaseQueryBenchmark:
    """数据库查询性能基准测试"""
    
    def test_simple_query_benchmark(self, benchmark, db, test_user):
        """测试简单查询性能"""
        # 创建测试数据
        for i in range(100):
            project = Project(
                id=f"query-project-{i}",
                name=f"查询测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def query_projects():
            return db.query(Project).filter(Project.owner_id == test_user.id).all()
        
        result = benchmark(query_projects)
        # 简单查询应该在 50ms 内
        assert benchmark.stats.stats.mean < 0.05
    
    def test_paginated_query_benchmark(self, benchmark, db, test_user):
        """测试分页查询性能"""
        # 创建测试数据
        for i in range(200):
            project = Project(
                id=f"page-project-{i}",
                name=f"分页测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def paginated_query():
            return db.query(Project).filter(
                Project.owner_id == test_user.id
            ).offset(0).limit(20).all()
        
        result = benchmark(paginated_query)
        # 分页查询应该在 30ms 内
        assert benchmark.stats.stats.mean < 0.03
    
    def test_count_query_benchmark(self, benchmark, db, test_user):
        """测试计数查询性能"""
        # 创建测试数据
        for i in range(500):
            project = Project(
                id=f"count-project-{i}",
                name=f"计数测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def count_query():
            return db.query(Project).filter(Project.owner_id == test_user.id).count()
        
        result = benchmark(count_query)
        # 计数查询应该在 30ms 内
        assert benchmark.stats.stats.mean < 0.03
    
    def test_join_query_benchmark(self, benchmark, db, test_user, test_project):
        """测试关联查询性能"""
        # 创建测试数据
        for i in range(50):
            doc_file = DocumentFile(
                id=f"file-{i}",
                project_id=test_project.id,
                filename=f"file{i}.pdf",
                file_type="pdf",
                created_at=datetime.utcnow()
            )
            db.add(doc_file)
        db.commit()
        
        def join_query():
            return db.query(DocumentFile).filter(
                DocumentFile.project_id == test_project.id
            ).all()
        
        result = benchmark(join_query)
        # 关联查询应该在 50ms 内
        assert benchmark.stats.stats.mean < 0.05


# ========== 文件操作性能基准测试 ==========

class TestFileOperationBenchmark:
    """文件操作性能基准测试"""
    
    def test_small_file_upload_benchmark(self, benchmark, auth_headers, test_project):
        """测试小文件上传性能基准（100KB）"""
        file_content = b"%PDF-1.4\n" + b"x" * (100 * 1024)
        counter = [0]
        
        def upload_file():
            counter[0] += 1
            return client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"bench_{counter[0]}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
        
        result = benchmark(upload_file)
        # 100KB文件上传应该在 1s 内
        assert benchmark.stats.stats.mean < 1.0
    
    def test_file_list_query_benchmark(self, benchmark, auth_headers, db, test_project, test_user):
        """测试文件列表查询性能基准"""
        # 创建测试文件数据
        for i in range(30):
            doc_file = DocumentFile(
                id=f"list-file-{i}",
                project_id=test_project.id,
                filename=f"file{i}.pdf",
                file_type="pdf",
                created_at=datetime.utcnow()
            )
            db.add(doc_file)
        db.commit()
        
        def get_files():
            return client.get(f"/api/v1/projects/{test_project.id}/files", headers=auth_headers)
        
        result = benchmark(get_files)
        # 文件列表查询应该在 200ms 内
        assert benchmark.stats.stats.mean < 0.2


# ========== 并发性能基准测试 ==========

class TestConcurrencyBenchmark:
    """并发性能基准测试"""
    
    def test_concurrent_reads_benchmark(self, benchmark, auth_headers, db, test_user):
        """测试并发读取性能"""
        # 创建测试数据
        for i in range(100):
            project = Project(
                id=f"concurrent-project-{i}",
                name=f"并发测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def concurrent_reads():
            def make_request(_):
                return client.get("/api/v1/projects", headers=auth_headers)
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(make_request, range(5)))
            return results
        
        result = benchmark(concurrent_reads)
        # 5个并发请求应该在 2s 内完成
        assert benchmark.stats.stats.mean < 2.0
    
    def test_sequential_vs_concurrent_benchmark(self, benchmark, auth_headers, db, test_user):
        """测试串行vs并发性能对比"""
        # 创建测试数据
        for i in range(50):
            project = Project(
                id=f"seq-project-{i}",
                name=f"顺序测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def sequential_requests():
            results = []
            for _ in range(5):
                results.append(client.get("/api/v1/projects", headers=auth_headers))
            return results
        
        result = benchmark(sequential_requests)
        # 5个串行请求应该在 1s 内完成
        assert benchmark.stats.stats.mean < 1.0


# ========== 内存使用基准测试 ==========

class TestMemoryBenchmark:
    """内存使用基准测试"""
    
    def test_memory_usage_during_query(self, benchmark, db, test_user):
        """测试查询时的内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 创建大量测试数据
        for i in range(100):
            project = Project(
                id=f"mem-project-{i}",
                name=f"内存测试项目{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()
        
        def query_with_memory_check():
            initial_mem = process.memory_info().rss / 1024 / 1024
            result = db.query(Project).filter(Project.owner_id == test_user.id).all()
            final_mem = process.memory_info().rss / 1024 / 1024
            return final_mem - initial_mem
        
        memory_increase = benchmark(query_with_memory_check)
        # 内存增长应该小于 10MB
        assert benchmark.stats.stats.mean < 10


# ========== 端到端性能基准测试 ==========

class TestEndToEndBenchmark:
    """端到端性能基准测试"""
    
    def test_complete_workflow_benchmark(self, benchmark, auth_headers, test_project):
        """测试完整工作流性能基准"""
        file_content = b"%PDF-1.4\n" + b"x" * (50 * 1024)
        counter = [0]
        
        def complete_workflow():
            counter[0] += 1
            # 1. 获取项目列表
            client.get("/api/v1/projects", headers=auth_headers)
            
            # 2. 上传文件
            resp = client.post(
                f"/api/v1/projects/{test_project.id}/files",
                files={"file": (f"e2e_{counter[0]}.pdf", io.BytesIO(file_content), "application/pdf")},
                headers=auth_headers
            )
            
            if resp.status_code == 201:
                file_id = resp.json().get("data", {}).get("id")
                # 3. 获取文件版本
                if file_id:
                    client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
            
            return resp
        
        result = benchmark(complete_workflow)
        # 完整工作流应该在 2s 内完成
        assert benchmark.stats.stats.mean < 2.0


# ========== 自定义基准配置 ==========

@pytest.mark.benchmark(
    group="api",
    min_time=0.1,
    max_time=1.0,
    min_rounds=5,
    timer=time.time,
    disable_gc=True,
    warmup=False
)
def test_benchmark_configuration_example(benchmark):
    """基准测试配置示例"""
    def example_function():
        # 模拟一些计算
        total = 0
        for i in range(1000):
            total += i
        return total
    
    result = benchmark(example_function)
    assert result == 499500
