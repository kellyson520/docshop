"""
API性能测试
测试文件上传下载性能、Diff计算性能、列表查询性能和并发请求性能
使用pytest进行测试
"""

import pytest
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import io

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 导入应用和模型
from app.main import app
from app.database import Base, get_db
from app.models import User, Project, DocumentFile
from app.utils.security import get_password_hash, create_access_token


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
        id="test-user-id",
        username="testuser",
        email="test@example.com",
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


class TestFileUploadPerformance:
    """测试文件上传性能"""

    def test_small_file_upload_performance(self, auth_headers):
        """
        测试小文件上传性能
        验证上传小于1MB文件的速度
        """
        # 创建项目
        project_data = {"name": "性能测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 准备小文件（100KB）
        file_content = b"%PDF-1.4 " + b"x" * (100 * 1024)

        # 测试多次上传性能
        upload_times = []
        for i in range(10):
            files = {
                "file": (f"small_test_{i}.pdf", io.BytesIO(file_content), "application/pdf")
            }

            start_time = time.time()
            response = client.post(
                f"/api/v1/projects/{project_id}/files",
                files=files,
                headers=auth_headers
            )
            end_time = time.time()

            assert response.status_code == 201
            upload_times.append(end_time - start_time)

        # 计算平均上传时间
        avg_time = statistics.mean(upload_times)
        max_time = max(upload_times)

        # 断言性能指标
        assert avg_time < 2.0, f"平均上传时间 {avg_time:.2f}s 超过2秒阈值"
        assert max_time < 5.0, f"最大上传时间 {max_time:.2f}s 超过5秒阈值"

    def test_medium_file_upload_performance(self, auth_headers):
        """
        测试中等文件上传性能
        验证上传1-10MB文件的速度
        """
        # 创建项目
        project_data = {"name": "性能测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 准备中等文件（5MB）
        file_content = b"%PDF-1.4 " + b"x" * (5 * 1024 * 1024)

        files = {
            "file": ("medium_test.pdf", io.BytesIO(file_content), "application/pdf")
        }

        start_time = time.time()
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        end_time = time.time()

        assert response.status_code == 201
        upload_time = end_time - start_time

        # 断言性能指标
        assert upload_time < 10.0, f"5MB文件上传时间 {upload_time:.2f}s 超过10秒阈值"

    def test_concurrent_upload_performance(self, auth_headers):
        """
        测试并发上传性能
        验证多个文件同时上传的性能
        """
        # 创建项目
        project_data = {"name": "并发测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 准备文件
        file_content = b"%PDF-1.4 " + b"x" * (50 * 1024)  # 50KB

        def upload_file(index):
            files = {
                "file": (f"concurrent_{index}.pdf", io.BytesIO(file_content), "application/pdf")
            }
            start_time = time.time()
            response = client.post(
                f"/api/v1/projects/{project_id}/files",
                files=files,
                headers=auth_headers
            )
            end_time = time.time()
            return response.status_code == 201, end_time - start_time

        # 并发上传5个文件
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(upload_file, range(5)))
        total_time = time.time() - start_time

        # 验证所有上传成功
        assert all(success for success, _ in results)

        # 验证总时间（并发应该比串行快）
        assert total_time < 15.0, f"5个文件并发上传总时间 {total_time:.2f}s 超过15秒阈值"


class TestFileDownloadPerformance:
    """测试文件下载性能"""

    def test_small_file_download_performance(self, auth_headers):
        """
        测试小文件下载性能
        验证下载小于1MB文件的速度
        """
        # 创建项目并上传文件
        project_data = {"name": "下载测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        file_content = b"%PDF-1.4 " + b"x" * (100 * 1024)  # 100KB
        files = {
            "file": ("download_test.pdf", io.BytesIO(file_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        file_id = response.json()["id"]

        # 测试多次下载性能
        download_times = []
        for _ in range(10):
            start_time = time.time()
            response = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers)
            end_time = time.time()

            assert response.status_code == 200
            download_times.append(end_time - start_time)

        avg_time = statistics.mean(download_times)
        assert avg_time < 1.0, f"平均下载时间 {avg_time:.2f}s 超过1秒阈值"

    def test_large_file_download_performance(self, auth_headers):
        """
        测试大文件下载性能
        验证下载大文件的速度
        """
        # 创建项目并上传文件
        project_data = {"name": "大文件下载测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        file_content = b"%PDF-1.4 " + b"x" * (1024 * 1024)  # 1MB
        files = {
            "file": ("large_download_test.pdf", io.BytesIO(file_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        file_id = response.json()["id"]

        # 测试下载
        start_time = time.time()
        response = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers)
        download_time = time.time() - start_time

        assert response.status_code == 200
        assert download_time < 5.0, f"1MB文件下载时间 {download_time:.2f}s 超过5秒阈值"


class TestDiffCalculationPerformance:
    """测试Diff计算性能"""

    def test_small_file_diff_performance(self, auth_headers):
        """
        测试小文件Diff计算性能
        验证小文件版本对比的速度
        """
        # 创建项目并上传两个版本的文件
        project_data = {"name": "Diff测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 上传第一个版本
        content_v1 = b"%PDF-1.4 version 1 content"
        files = {
            "file": ("diff_test.pdf", io.BytesIO(content_v1), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        file_id = response.json()["id"]

        # 上传第二个版本
        content_v2 = b"%PDF-1.4 version 2 updated content"
        files = {
            "file": ("diff_test.pdf", io.BytesIO(content_v2), "application/pdf")
        }
        response = client.post(
            f"/api/v1/files/{file_id}/versions",
            files=files,
            headers=auth_headers
        )

        # 获取版本列表
        response = client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
        versions = response.json()

        if len(versions) >= 2:
            # 测试Diff计算性能
            start_time = time.time()
            response = client.post(
                "/api/v1/diffs",
                json={
                    "file_id": file_id,
                    "version1_id": versions[0]["id"],
                    "version2_id": versions[1]["id"]
                },
                headers=auth_headers
            )
            diff_time = time.time() - start_time

            # Diff计算应该在合理时间内完成
            assert diff_time < 10.0, f"Diff计算时间 {diff_time:.2f}s 超过10秒阈值"

    def test_diff_calculation_with_large_files(self, auth_headers):
        """
        测试大文件Diff计算性能
        验证大文件版本对比的性能表现
        """
        # 创建项目
        project_data = {"name": "大文件Diff测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 上传大文件版本
        content_v1 = b"%PDF-1.4 " + b"x" * (500 * 1024)  # 500KB
        files = {
            "file": ("large_diff_test.pdf", io.BytesIO(content_v1), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        file_id = response.json()["id"]

        content_v2 = b"%PDF-1.4 " + b"y" * (500 * 1024)  # 500KB
        files = {
            "file": ("large_diff_test.pdf", io.BytesIO(content_v2), "application/pdf")
        }
        response = client.post(
            f"/api/v1/files/{file_id}/versions",
            files=files,
            headers=auth_headers
        )

        # 获取版本列表
        response = client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
        versions = response.json()

        if len(versions) >= 2:
            start_time = time.time()
            response = client.post(
                "/api/v1/diffs",
                json={
                    "file_id": file_id,
                    "version1_id": versions[0]["id"],
                    "version2_id": versions[1]["id"]
                },
                headers=auth_headers
            )
            diff_time = time.time() - start_time

            # 大文件Diff计算可能需要更长时间，但应该合理
            assert diff_time < 30.0, f"大文件Diff计算时间 {diff_time:.2f}s 超过30秒阈值"


class TestListQueryPerformance:
    """测试列表查询性能"""

    def test_project_list_query_performance(self, auth_headers, db, test_user):
        """
        测试项目列表查询性能
        验证大量项目列表查询的速度
        """
        # 创建大量项目
        for i in range(100):
            project = Project(
                id=f"perf-project-{i}",
                name=f"性能测试项目{i}",
                description=f"描述{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()

        # 测试查询性能
        query_times = []
        for _ in range(10):
            start_time = time.time()
            response = client.get("/api/v1/projects", headers=auth_headers)
            end_time = time.time()

            assert response.status_code == 200
            query_times.append(end_time - start_time)

        avg_time = statistics.mean(query_times)
        assert avg_time < 1.0, f"项目列表查询平均时间 {avg_time:.2f}s 超过1秒阈值"

    def test_project_list_with_pagination_performance(self, auth_headers, db, test_user):
        """
        测试分页查询性能
        验证分页查询的速度
        """
        # 创建大量项目
        for i in range(200):
            project = Project(
                id=f"pag-project-{i}",
                name=f"分页测试项目{i}",
                description=f"描述{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()

        # 测试分页查询
        start_time = time.time()
        response = client.get("/api/v1/projects?skip=0&limit=20", headers=auth_headers)
        query_time = time.time() - start_time

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 20
        assert query_time < 0.5, f"分页查询时间 {query_time:.2f}s 超过0.5秒阈值"

    def test_search_query_performance(self, auth_headers, db, test_user):
        """
        测试搜索查询性能
        验证搜索功能的速度
        """
        # 创建大量项目
        for i in range(100):
            project = Project(
                id=f"search-project-{i}",
                name=f"搜索测试项目{i}",
                description=f"搜索描述{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()

        # 测试搜索性能
        start_time = time.time()
        response = client.get("/api/v1/projects?search=搜索", headers=auth_headers)
        search_time = time.time() - start_time

        assert response.status_code == 200
        assert search_time < 2.0, f"搜索查询时间 {search_time:.2f}s 超过2秒阈值"


class TestConcurrentRequestPerformance:
    """测试并发请求性能"""

    def test_concurrent_project_list_requests(self, auth_headers, db, test_user):
        """
        测试并发项目列表请求性能
        验证多个并发请求的处理能力
        """
        # 创建测试数据
        for i in range(50):
            project = Project(
                id=f"concurrent-project-{i}",
                name=f"并发测试项目{i}",
                description=f"描述{i}",
                owner_id=test_user.id,
                created_at=datetime.utcnow()
            )
            db.add(project)
        db.commit()

        def make_request(_):
            start_time = time.time()
            response = client.get("/api/v1/projects", headers=auth_headers)
            end_time = time.time()
            return response.status_code == 200, end_time - start_time

        # 并发发起20个请求
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, range(20)))
        total_time = time.time() - start_time

        # 验证所有请求成功
        assert all(success for success, _ in results)

        # 验证平均响应时间
        avg_response_time = statistics.mean([time for _, time in results])
        assert avg_response_time < 2.0, f"并发请求平均响应时间 {avg_response_time:.2f}s 超过2秒阈值"

        # 验证总处理时间
        assert total_time < 10.0, f"20个并发请求总处理时间 {total_time:.2f}s 超过10秒阈值"

    def test_concurrent_file_operations(self, auth_headers):
        """
        测试并发文件操作性能
        验证多个并发文件操作的处理能力
        """
        # 创建项目
        project_data = {"name": "并发文件测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 准备文件
        file_content = b"%PDF-1.4 " + b"x" * (10 * 1024)  # 10KB

        def upload_and_download(index):
            # 上传
            files = {
                "file": (f"concurrent_file_{index}.pdf", io.BytesIO(file_content), "application/pdf")
            }
            start_time = time.time()
            response = client.post(
                f"/api/v1/projects/{project_id}/files",
                files=files,
                headers=auth_headers
            )
            if response.status_code != 201:
                return False, 0
            file_id = response.json()["id"]

            # 下载
            response = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers)
            end_time = time.time()

            return response.status_code == 200, end_time - start_time

        # 并发执行5个上传下载操作
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(upload_and_download, range(5)))

        # 验证所有操作成功
        assert all(success for success, _ in results)

        # 验证平均时间
        avg_time = statistics.mean([time for _, time in results])
        assert avg_time < 5.0, f"并发文件操作平均时间 {avg_time:.2f}s 超过5秒阈值"

    def test_api_rate_limiting_performance(self, auth_headers):
        """
        测试API限流性能
        验证限流机制在高并发下的表现
        """
        def make_request(_):
            response = client.get("/api/v1/projects", headers=auth_headers)
            return response.status_code

        # 快速发起30个请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            status_codes = list(executor.map(make_request, range(30)))

        # 统计结果
        success_count = status_codes.count(200)
        rate_limited_count = status_codes.count(429)  # Too Many Requests

        # 大部分请求应该成功，部分可能被限流
        assert success_count > 20, f"成功请求数 {success_count} 过少"


class TestOverallSystemPerformance:
    """测试整体系统性能"""

    def test_end_to_end_workflow_performance(self, auth_headers):
        """
        测试端到端工作流性能
        验证完整业务流程的性能
        """
        start_time = time.time()

        # 1. 创建项目
        project_data = {"name": "端到端性能测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        assert response.status_code == 201
        project_id = response.json()["id"]

        # 2. 上传文件
        file_content = b"%PDF-1.4 " + b"x" * (100 * 1024)
        files = {
            "file": ("e2e_test.pdf", io.BytesIO(file_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 201
        file_id = response.json()["id"]

        # 3. 获取项目列表
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200

        # 4. 获取文件列表
        response = client.get(f"/api/v1/projects/{project_id}/files", headers=auth_headers)
        assert response.status_code == 200

        # 5. 下载文件
        response = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers)
        assert response.status_code == 200

        total_time = time.time() - start_time

        # 端到端流程应该在合理时间内完成
        assert total_time < 15.0, f"端到端工作流时间 {total_time:.2f}s 超过15秒阈值"

    def test_memory_usage_under_load(self, auth_headers):
        """
        测试负载下的内存使用
        验证系统在高负载下的内存表现
        """
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 执行大量操作
        project_data = {"name": "内存测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        for i in range(20):
            file_content = b"%PDF-1.4 " + b"x" * (100 * 1024)  # 100KB
            files = {
                "file": (f"memory_test_{i}.pdf", io.BytesIO(file_content), "application/pdf")
            }
            client.post(
                f"/api/v1/projects/{project_id}/files",
                files=files,
                headers=auth_headers
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 内存增长应该在合理范围内（小于100MB）
        assert memory_increase < 100, f"内存增长 {memory_increase:.2f}MB 超过100MB阈值"
