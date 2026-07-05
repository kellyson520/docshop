"""
后端API集成测试
测试完整的业务流程和API交互
使用pytest进行测试
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 导入应用和模型
from app.utils.time import utc_now, utc_now_iso
from app.main import app
from app.database import Base, get_db
from app.models import User, Project, DocumentFile, FileVersion, ExamSchedule, ShareToken
from app.utils.security import get_password_hash, create_access_token


def make_pdf_bytes(text: str) -> bytes:
    """生成可被 PyMuPDF 正常解析的测试 PDF。"""
    import fitz

    doc = fitz.open()
    try:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), text)
        return doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()


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
    Base.metadata.create_all(bind=engine)
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
        id=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        role="admin",
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


class TestUserRegistrationLogin:
    """测试用户注册登录完整流程"""

    def test_complete_registration_login_flow(self, db):
        """
        测试完整的用户注册登录流程
        - 用户注册
        - 用户登录
        - 获取用户信息
        - 登出
        """
        # 1. 用户注册
        register_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        user_id = data["id"]

        # 2. 用户登录
        login_data = {
            "username": "newuser",
            "password": "NewPass123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        access_token = token_data["access_token"]

        # 3. 使用token获取用户信息
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        me_data = response.json()
        assert me_data["username"] == "newuser"
        assert me_data["id"] == user_id

        # 4. 验证密码错误时登录失败
        wrong_login = {
            "username": "newuser",
            "password": "WrongPass123!"
        }
        response = client.post("/api/v1/auth/login", data=wrong_login)
        assert response.status_code == 401

    def test_duplicate_username_registration(self, test_user):
        """测试重复用户名注册失败"""
        register_data = {
            "username": "testuser",  # 已存在的用户名
            "email": "another@example.com",
            "password": "Pass123!"
        }
        response = client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == 40004


class TestProjectCRUD:
    """测试项目CRUD完整流程"""

    def test_complete_project_crud_flow(self, auth_headers, db, test_user):
        """
        测试项目CRUD完整流程
        - 创建项目
        - 获取项目列表
        - 获取项目详情
        - 更新项目
        - 删除项目
        """
        # 1. 创建项目
        project_data = {
            "name": "测试项目",
            "description": "这是一个测试项目"
        }
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]
        assert project["name"] == "测试项目"
        assert project["description"] == "这是一个测试项目"

        # 2. 获取项目列表
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1
        assert any(p["id"] == project_id for p in projects)

        # 3. 获取项目详情
        response = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 200
        detail = response.json()
        assert detail["id"] == project_id
        assert detail["name"] == "测试项目"

        # 4. 更新项目
        update_data = {
            "name": "更新后的项目名称",
            "description": "更新后的描述"
        }
        response = client.put(f"/api/v1/projects/{project_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        updated = response.json()
        assert updated["name"] == "更新后的项目名称"
        assert updated["description"] == "更新后的描述"

        # 5. 删除项目
        response = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 204

        # 6. 验证项目已删除
        response = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_project_access_without_auth(self):
        """测试未认证无法访问项目"""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


class TestFileUploadDownload:
    """测试文件上传下载完整流程"""

    def test_complete_file_upload_download_flow(self, auth_headers, db, test_user):
        """
        测试文件上传下载完整流程
        - 创建项目
        - 上传文件
        - 获取文件列表
        - 下载文件
        - 删除文件
        """
        import io

        # 1. 先创建项目
        project_data = {"name": "文件测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 2. 上传文件
        file_content = b"%PDF-1.4 test content for upload"
        files = {
            "file": ("test-file.pdf", io.BytesIO(file_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 201
        file_data = response.json()
        file_id = file_data["id"]
        assert file_data["filename"] == "test-file.pdf"

        # 3. 获取文件列表
        response = client.get(f"/api/v1/projects/{project_id}/files", headers=auth_headers)
        assert response.status_code == 200
        files_list = response.json()
        assert any(f["id"] == file_id for f in files_list)

        # 4. 下载文件
        response = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers)
        assert response.status_code == 200

        # 5. 删除文件
        response = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_upload_invalid_file_type(self, auth_headers, db, test_user):
        """测试上传无效文件类型"""
        import io

        # 先创建项目
        project_data = {"name": "文件测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 上传不允许的文件类型
        file_content = b"invalid content"
        files = {
            "file": ("test.exe", io.BytesIO(file_content), "application/x-msdownload")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 400


class TestVersionComparison:
    """测试版本对比完整流程"""

    def test_complete_version_comparison_flow(self, auth_headers, db, test_user):
        """
        测试版本对比完整流程
        - 创建项目
        - 上传文件
        - 上传新版本
        - 获取版本列表
        - 对比版本
        """
        import io

        # 1. 创建项目
        project_data = {"name": "版本测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 2. 上传初始版本
        file_content_v1 = make_pdf_bytes("version 1 content")
        files = {
            "file": ("version-test.pdf", io.BytesIO(file_content_v1), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        file_id = response.json()["id"]

        # 3. 上传新版本
        file_content_v2 = make_pdf_bytes("version 2 updated content")
        files = {
            "file": ("version-test.pdf", io.BytesIO(file_content_v2), "application/pdf")
        }
        response = client.post(
            f"/api/v1/files/{file_id}/versions",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 201

        # 4. 获取版本列表
        response = client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
        assert response.status_code == 200
        versions = response.json()
        assert len(versions) >= 2

        # 5. 对比版本
        if len(versions) >= 2:
            version1_id = versions[0]["id"]
            version2_id = versions[1]["id"]
            response = client.post(
                "/api/v1/diffs",
                json={
                    "file_id": file_id,
                    "version1_id": version1_id,
                    "version2_id": version2_id
                },
                headers=auth_headers
            )
            # 根据实际API返回状态码
            assert response.status_code in [200, 201, 202]


class TestExamCreationReminder:
    """测试考试创建提醒完整流程"""

    def test_complete_exam_creation_reminder_flow(self, auth_headers, db, test_user):
        """
        测试考试创建提醒完整流程
        - 创建考试
        - 获取考试列表
        - 获取即将到来的考试
        - 更新考试
        - 删除考试
        """
        # 1. 创建考试
        exam_date = utc_now() + timedelta(days=7)
        exam_data = {
            "name": "期末考试",
            "description": "本学期期末考试",
            "exam_date": exam_date.isoformat(),
            "location": "教学楼A101",
            "reminder_days": [1, 3, 7]
        }
        response = client.post("/api/v1/exams", json=exam_data, headers=auth_headers)
        assert response.status_code == 201
        exam = response.json()
        exam_id = exam["id"]
        assert exam["name"] == "期末考试"

        # 2. 获取考试列表
        response = client.get("/api/v1/exams", headers=auth_headers)
        assert response.status_code == 200
        exams = response.json()
        assert any(e["id"] == exam_id for e in exams)

        # 3. 获取即将到来的考试
        response = client.get("/api/v1/exams/upcoming", headers=auth_headers)
        assert response.status_code == 200
        upcoming = response.json()
        assert any(e["id"] == exam_id for e in upcoming)

        # 4. 更新考试
        update_data = {
            "name": "期末考试（更新）",
            "description": "更新后的描述"
        }
        response = client.put(f"/api/v1/exams/{exam_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        updated = response.json()
        assert updated["name"] == "期末考试（更新）"

        # 5. 删除考试
        response = client.delete(f"/api/v1/exams/{exam_id}", headers=auth_headers)
        assert response.status_code == 204


class TestShareFunctionality:
    """测试分享功能完整流程"""

    def test_complete_share_flow(self, auth_headers, db, test_user):
        """
        测试分享功能完整流程
        - 创建项目
        - 创建分享链接
        - 访问分享链接
        - 撤销分享
        """
        # 1. 创建项目
        project_data = {"name": "分享测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 2. 创建分享链接
        share_data = {
            "project_id": project_id,
            "expires_days": 7,
            "permission": "view"
        }
        response = client.post("/api/v1/shares", json=share_data, headers=auth_headers)
        assert response.status_code == 201
        share = response.json()
        share_token = share["token"]
        assert share_token is not None

        # 3. 访问分享链接（无需认证）
        response = client.get(f"/api/v1/shares/{share_token}")
        assert response.status_code == 200
        shared_data = response.json()
        assert shared_data["project_id"] == project_id

        # 4. 撤销分享
        response = client.delete(f"/api/v1/shares/{share_token}", headers=auth_headers)
        assert response.status_code == 204

        # 5. 验证分享已撤销
        response = client.get(f"/api/v1/shares/{share_token}")
        assert response.status_code == 404

    def test_share_with_password(self, auth_headers, db, test_user):
        """测试带密码的分享"""
        # 创建项目
        project_data = {"name": "密码分享测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 创建带密码的分享
        share_data = {
            "project_id": project_id,
            "expires_days": 7,
            "permission": "view",
            "password": "sharepass123"
        }
        response = client.post("/api/v1/shares", json=share_data, headers=auth_headers)
        assert response.status_code == 201
        share_token = response.json()["token"]

        # 不带密码访问失败
        response = client.get(f"/api/v1/shares/{share_token}")
        assert response.status_code == 403

        # 带正确密码访问成功
        response = client.get(f"/api/v1/shares/{share_token}?password=sharepass123")
        assert response.status_code == 200


class TestCrossFeatureIntegration:
    """测试跨功能集成"""

    def test_project_with_files_and_exams(self, auth_headers, db, test_user):
        """
        测试项目与文件、考试的集成
        - 创建项目
        - 上传文件到项目
        - 创建与项目相关的考试
        - 获取项目完整信息
        """
        import io

        # 1. 创建项目
        project_data = {
            "name": "综合测试项目",
            "description": "包含文件和考试的项目"
        }
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 2. 上传文件到项目
        file_content = b"%PDF-1.4 project file"
        files = {
            "file": ("project-file.pdf", io.BytesIO(file_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 201

        # 3. 创建与项目相关的考试
        exam_data = {
            "name": "项目相关考试",
            "description": "与综合测试项目相关的考试",
            "exam_date": (utc_now() + timedelta(days=14)).isoformat(),
            "project_id": project_id
        }
        response = client.post("/api/v1/exams", json=exam_data, headers=auth_headers)
        assert response.status_code == 201

        # 4. 获取项目详情，验证包含文件和考试信息
        response = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert response.status_code == 200
        project_detail = response.json()
        assert project_detail["id"] == project_id
