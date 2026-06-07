"""
文件管理模块单元测试

测试文件相关的API功能，包括文件上传、版本管理、下载、删除等。
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import BytesIO

from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project
from app.schemas.file import FileResponse, VersionResponse, VersionListResponse
from app.exceptions import ResourceNotFound, FileValidationError


# ===== Fixtures =====

@pytest.fixture
def mock_document_file():
    """创建模拟文档文件"""
    doc_file = Mock()
    doc_file.id = "test-file-id-123"
    doc_file.project_id = "test-project-id-123"
    doc_file.filename = "test.pdf"
    doc_file.file_type = "pdf"
    doc_file.current_version = 1
    doc_file.created_at = datetime.utcnow().isoformat() + "Z"
    return doc_file


@pytest.fixture
def mock_file_version():
    """创建模拟文件版本"""
    version = Mock()
    version.id = "test-version-id-123"
    version.file_id = "test-file-id-123"
    version.version = 1
    version.storage_path = "/data/uploads/project/file/v1_test.pdf"
    version.file_hash = "sha256_hash_value"
    version.file_size = 1024
    version.changelog = None
    version.created_at = datetime.utcnow().isoformat() + "Z"
    return version


@pytest.fixture
def test_project_with_user(client, auth_headers, test_user, db_session):
    """创建测试项目"""
    project = Project(
        name="文件测试项目",
        description="用于文件测试的项目",
        owner_id=test_user.id,
        share_token="test_token_123"
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def pdf_file_content():
    """创建模拟PDF文件内容"""
    # PDF文件头部魔数
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


@pytest.fixture
def docx_file_content():
    """创建模拟DOCX文件内容"""
    # DOCX文件头部 (ZIP格式)
    return b"PK\x03\x04\x14\x00\x06\x00" + b"\x00" * 100


# ===== 文件上传测试 =====

class TestUploadFile:
    """测试文件上传功能"""

    def test_upload_pdf_file_success(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试成功上传PDF文件"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["filename"] == "test.pdf"
        assert data["data"]["file_type"] == "pdf"
        assert data["data"]["current_version"] == 1
        assert "id" in data["data"]

    def test_upload_docx_file_success(self, client, auth_headers, test_project_with_user, docx_file_content, db_session):
        """测试成功上传DOCX文件"""
        file_content = BytesIO(docx_file_content)
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("test.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["file_type"] == "docx"

    def test_upload_file_project_not_found(self, client, auth_headers, pdf_file_content):
        """测试上传到不存在的项目"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            "/api/v1/projects/non-existent-id/files",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code == 404

    def test_upload_file_invalid_type(self, client, auth_headers, test_project_with_user):
        """测试上传无效文件类型"""
        file_content = BytesIO(b"This is a text file content")
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("test.txt", file_content, "text/plain")},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "File type not allowed" in response.json()["message"]

    def test_upload_file_without_auth(self, client, test_project_with_user, pdf_file_content):
        """测试未认证上传文件"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("test.pdf", file_content, "application/pdf")}
        )
        
        assert response.status_code == 403

    def test_upload_file_without_permission(self, client, auth_headers, db_session):
        """测试上传到无权限的项目"""
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户和项目
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otherfileuser", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        other_project = Project(
            name="他人项目",
            owner_id=other_user.id,
            share_token="other_token"
        )
        db_session.add(other_project)
        db_session.commit()
        
        file_content = BytesIO(b"%PDF-1.4 test")
        
        response = client.post(
            f"/api/v1/projects/{other_project.id}/files",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code == 404  # 或403

    def test_upload_empty_file(self, client, auth_headers, test_project_with_user):
        """测试上传空文件"""
        file_content = BytesIO(b"")
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("empty.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        # 空文件应该被接受或根据具体实现返回错误
        assert response.status_code in [201, 400]

    def test_upload_file_with_special_characters_in_name(self, client, auth_headers, test_project_with_user, pdf_file_content):
        """测试上传文件名包含特殊字符"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("test-file_2024.v1.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code == 201

    def test_upload_unicode_filename(self, client, auth_headers, test_project_with_user, pdf_file_content):
        """测试上传Unicode文件名"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("测试文件.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        assert "测试文件.pdf" in response.json()["data"]["filename"]


# ===== 版本上传测试 =====

class TestUploadVersion:
    """测试上传新版本功能"""

    def test_upload_version_success(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试成功上传新版本"""
        # 先创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建第一个版本
        v1 = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=f"/data/uploads/{test_project_with_user.id}/{doc.id}/v1_test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(v1)
        db_session.commit()
        
        # 上传新版本
        file_content = BytesIO(pdf_file_content + b"\n% Updated content")
        
        response = client.post(
            f"/api/v1/files/{doc.id}/versions",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            data={"changelog": "更新版本2"},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["version"] == 2
        assert data["data"]["changelog"] == "更新版本2"

    def test_upload_version_file_not_found(self, client, auth_headers, pdf_file_content):
        """测试为不存在的文件上传版本"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            "/api/v1/files/non-existent-id/versions",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code == 404

    def test_upload_version_wrong_file_type(self, client, auth_headers, test_project_with_user, db_session):
        """测试上传错误文件类型版本"""
        # 创建PDF文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 尝试上传DOCX作为新版本
        file_content = BytesIO(b"PK\x03\x04\x14\x00\x06\x00" + b"\x00" * 100)
        
        response = client.post(
            f"/api/v1/files/{doc.id}/versions",
            files={"file": ("test.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=auth_headers
        )
        
        # 应该拒绝不同类型文件
        assert response.status_code == 400

    def test_upload_version_without_auth(self, client, test_project_with_user, pdf_file_content, db_session):
        """测试未认证上传版本"""
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            f"/api/v1/files/{doc.id}/versions",
            files={"file": ("test.pdf", file_content, "application/pdf")}
        )
        
        assert response.status_code == 403

    def test_upload_multiple_versions(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试上传多个版本"""
        # 创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建第一个版本
        v1 = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=f"/data/uploads/{test_project_with_user.id}/{doc.id}/v1_test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(v1)
        db_session.commit()
        
        # 上传多个版本
        for i in range(2, 5):
            file_content = BytesIO(pdf_file_content + f"\n% Version {i}".encode())
            
            response = client.post(
                f"/api/v1/files/{doc.id}/versions",
                files={"file": ("test.pdf", file_content, "application/pdf")},
                data={"changelog": f"版本{i}"},
                headers=auth_headers
            )
            
            assert response.status_code == 201
            assert response.json()["data"]["version"] == i
        
        # 验证当前版本
        db_session.refresh(doc)
        assert doc.current_version == 4


# ===== 版本列表测试 =====

class TestListVersions:
    """测试获取版本列表功能"""

    def test_list_versions_success(self, client, auth_headers, test_project_with_user, db_session):
        """测试成功获取版本列表"""
        # 创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=3
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建多个版本
        for i in range(1, 4):
            version = FileVersion(
                file_id=doc.id,
                version=i,
                storage_path=f"/path/v{i}_test.pdf",
                file_hash=f"hash{i}",
                file_size=1000 * i,
                changelog=f"版本{i}" if i > 1 else None
            )
            db_session.add(version)
        db_session.commit()
        
        response = client.get(f"/api/v1/files/{doc.id}/versions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["file_id"] == doc.id
        assert data["data"]["filename"] == "test.pdf"
        assert data["data"]["current_version"] == 3
        assert len(data["data"]["versions"]) == 3

    def test_list_versions_file_not_found(self, client, auth_headers):
        """测试获取不存在的文件版本列表"""
        response = client.get("/api/v1/files/non-existent-id/versions", headers=auth_headers)
        
        assert response.status_code == 404

    def test_list_versions_without_auth(self, client, test_project_with_user, db_session):
        """测试未认证获取版本列表"""
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        response = client.get(f"/api/v1/files/{doc.id}/versions")
        
        assert response.status_code == 403

    def test_list_versions_empty(self, client, auth_headers, test_project_with_user, db_session):
        """测试获取空版本列表"""
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建第一个版本
        v1 = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=f"/path/v1_test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(v1)
        db_session.commit()
        
        response = client.get(f"/api/v1/files/{doc.id}/versions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["versions"]) == 1


# ===== 文件下载测试 =====

class TestDownloadVersion:
    """测试下载版本功能"""

    def test_download_version_success(self, client, auth_headers, test_project_with_user, db_session, tmp_path):
        """测试成功下载版本"""
        # 创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建临时文件
        temp_file = tmp_path / "test.pdf"
        temp_file.write_bytes(b"%PDF-1.4 test content")
        
        # 创建版本记录
        version = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=str(temp_file),
            file_hash="hash1",
            file_size=temp_file.stat().st_size
        )
        db_session.add(version)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/files/{doc.id}/versions/{version.id}/download",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_download_version_not_found(self, client, auth_headers):
        """测试下载不存在的版本"""
        response = client.get(
            "/api/v1/files/non-existent-id/versions/non-existent-version/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    def test_download_version_mismatched_file(self, client, auth_headers, test_project_with_user, db_session):
        """测试下载版本与文件不匹配"""
        # 创建两个文件
        doc1 = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test1.pdf",
            file_type="pdf",
            current_version=1
        )
        doc2 = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test2.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add_all([doc1, doc2])
        db_session.commit()
        
        # 为doc1创建版本
        version = FileVersion(
            file_id=doc1.id,
            version=1,
            storage_path="/path/test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(version)
        db_session.commit()
        
        # 尝试用doc2的ID下载doc1的版本
        response = client.get(
            f"/api/v1/files/{doc2.id}/versions/{version.id}/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    def test_download_version_without_auth(self, client, test_project_with_user, db_session):
        """测试未认证下载版本"""
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        version = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path="/path/test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(version)
        db_session.commit()
        
        response = client.get(f"/api/v1/files/{doc.id}/versions/{version.id}/download")
        
        assert response.status_code == 403


# ===== 文件删除测试 =====

class TestDeleteFile:
    """测试删除文件功能"""

    def test_delete_file_success(self, client, auth_headers, test_project_with_user, db_session, tmp_path):
        """测试成功删除文件"""
        # 创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建临时文件
        temp_file = tmp_path / "test.pdf"
        temp_file.write_bytes(b"%PDF-1.4 test content")
        
        # 创建版本
        version = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=str(temp_file),
            file_hash="hash1",
            file_size=temp_file.stat().st_size
        )
        db_session.add(version)
        db_session.commit()
        
        response = client.delete(f"/api/v1/files/{doc.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # 验证文件记录已删除
        deleted_doc = db_session.query(DocumentFile).filter(DocumentFile.id == doc.id).first()
        assert deleted_doc is None

    def test_delete_file_not_found(self, client, auth_headers):
        """测试删除不存在的文件"""
        response = client.delete("/api/v1/files/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404

    def test_delete_file_without_auth(self, client, test_project_with_user, db_session):
        """测试未认证删除文件"""
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        response = client.delete(f"/api/v1/files/{doc.id}")
        
        assert response.status_code == 403

    def test_delete_file_cascades_versions(self, client, auth_headers, test_project_with_user, db_session, tmp_path):
        """测试删除文件级联删除版本"""
        # 创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=2
        )
        db_session.add(doc)
        db_session.commit()
        
        # 创建多个版本
        for i in range(1, 3):
            temp_file = tmp_path / f"v{i}_test.pdf"
            temp_file.write_bytes(f"%PDF-1.4 version {i}".encode())
            
            version = FileVersion(
                file_id=doc.id,
                version=i,
                storage_path=str(temp_file),
                file_hash=f"hash{i}",
                file_size=temp_file.stat().st_size
            )
            db_session.add(version)
        db_session.commit()
        
        # 删除文件
        response = client.delete(f"/api/v1/files/{doc.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # 验证版本记录已删除
        versions = db_session.query(FileVersion).filter(FileVersion.file_id == doc.id).all()
        assert len(versions) == 0


# ===== 请求模型验证测试 =====

class TestFileRequestModels:
    """测试文件请求模型"""

    def test_file_response_model(self):
        """测试文件响应模型"""
        response = FileResponse(
            id="file-id-123",
            project_id="project-id-123",
            filename="test.pdf",
            file_type="pdf",
            current_version=1,
            created_at="2024-01-01T00:00:00Z"
        )
        assert response.id == "file-id-123"
        assert response.filename == "test.pdf"
        assert response.file_type == "pdf"

    def test_version_response_model(self):
        """测试版本响应模型"""
        response = VersionResponse(
            id="version-id-123",
            version=1,
            file_size=1024,
            changelog="初始版本",
            has_diff=False,
            created_at="2024-01-01T00:00:00Z"
        )
        assert response.id == "version-id-123"
        assert response.version == 1
        assert response.file_size == 1024

    def test_version_list_response_model(self):
        """测试版本列表响应模型"""
        versions = [
            VersionResponse(
                id="v1",
                version=1,
                file_size=1000,
                changelog=None,
                has_diff=False,
                created_at="2024-01-01T00:00:00Z"
            ),
            VersionResponse(
                id="v2",
                version=2,
                file_size=1200,
                changelog="更新",
                has_diff=True,
                created_at="2024-01-02T00:00:00Z"
            )
        ]
        response = VersionListResponse(
            file_id="file-id-123",
            filename="test.pdf",
            current_version=2,
            versions=versions
        )
        assert response.file_id == "file-id-123"
        assert len(response.versions) == 2


# ===== 边界情况测试 =====

class TestFileEdgeCases:
    """文件边界情况测试"""

    def test_upload_very_large_filename(self, client, auth_headers, test_project_with_user, pdf_file_content):
        """测试上传超长文件名"""
        file_content = BytesIO(pdf_file_content)
        long_name = "a" * 200 + ".pdf"
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": (long_name, file_content, "application/pdf")},
            headers=auth_headers
        )
        
        # 应该成功或根据具体实现返回错误
        assert response.status_code in [201, 400]

    def test_upload_file_with_only_extension(self, client, auth_headers, test_project_with_user, pdf_file_content):
        """测试只有扩展名的文件名"""
        file_content = BytesIO(pdf_file_content)
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": (".pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert response.status_code in [201, 400]

    def test_upload_file_no_extension(self, client, auth_headers, test_project_with_user):
        """测试没有扩展名的文件"""
        file_content = BytesIO(b"Some content without proper extension")
        
        response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("nofileextension", file_content, "application/octet-stream")},
            headers=auth_headers
        )
        
        # 应该被拒绝
        assert response.status_code == 400

    def test_version_changelog_with_special_characters(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试版本变更日志包含特殊字符"""
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        v1 = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=f"/path/v1_test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(v1)
        db_session.commit()
        
        file_content = BytesIO(pdf_file_content)
        changelog = "更新内容：<script>alert('xss')</script> 和中文测试"
        
        response = client.post(
            f"/api/v1/files/{doc.id}/versions",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            data={"changelog": changelog},
            headers=auth_headers
        )
        
        assert response.status_code == 201

    def test_concurrent_version_uploads(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试并发版本上传"""
        import concurrent.futures
        
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        v1 = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=f"/path/v1_test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(v1)
        db_session.commit()
        
        def upload_version(i):
            file_content = BytesIO(pdf_file_content + f"\n% Version {i}".encode())
            return client.post(
                f"/api/v1/files/{doc.id}/versions",
                files={"file": ("test.pdf", file_content, "application/pdf")},
                headers=auth_headers
            )
        
        # 并发上传
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_version, i) for i in range(3)]
            results = [f.result() for f in futures]
        
        # 所有请求都应该成功
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 3


# ===== 集成测试 =====

class TestFileIntegration:
    """文件集成测试"""

    def test_full_file_lifecycle(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试完整的文件生命周期"""
        # 1. 上传文件
        file_content = BytesIO(pdf_file_content)
        upload_response = client.post(
            f"/api/v1/projects/{test_project_with_user.id}/files",
            files={"file": ("lifecycle.pdf", file_content, "application/pdf")},
            headers=auth_headers
        )
        
        assert upload_response.status_code == 201
        file_id = upload_response.json()["data"]["id"]
        
        # 2. 获取版本列表
        versions_response = client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
        assert versions_response.status_code == 200
        assert len(versions_response.json()["data"]["versions"]) == 1
        
        # 3. 上传新版本
        for i in range(2, 4):
            file_content = BytesIO(pdf_file_content + f"\n% Version {i}".encode())
            version_response = client.post(
                f"/api/v1/files/{file_id}/versions",
                files={"file": ("lifecycle.pdf", file_content, "application/pdf")},
                data={"changelog": f"版本{i}"},
                headers=auth_headers
            )
            assert version_response.status_code == 201
        
        # 4. 验证版本数量
        versions_response = client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
        assert len(versions_response.json()["data"]["versions"]) == 3
        
        # 5. 删除文件
        delete_response = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)
        assert delete_response.status_code == 204
        
        # 6. 验证文件已删除
        get_response = client.get(f"/api/v1/files/{file_id}/versions", headers=auth_headers)
        assert get_response.status_code == 404

    def test_multiple_files_in_project(self, client, auth_headers, test_project_with_user, pdf_file_content, docx_file_content, db_session):
        """测试项目中多个文件"""
        file_ids = []
        
        # 上传多个文件
        files_data = [
            ("doc1.pdf", pdf_file_content, "application/pdf"),
            ("doc2.pdf", pdf_file_content + b"\n% Page 2", "application/pdf"),
            ("doc.docx", docx_file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]
        
        for filename, content, content_type in files_data:
            file_content = BytesIO(content)
            response = client.post(
                f"/api/v1/projects/{test_project_with_user.id}/files",
                files={"file": (filename, file_content, content_type)},
                headers=auth_headers
            )
            assert response.status_code == 201
            file_ids.append(response.json()["data"]["id"])
        
        # 验证所有文件都已创建
        assert len(file_ids) == 3
        
        # 验证项目统计
        from app.models.document_file import DocumentFile
        files = db_session.query(DocumentFile).filter(
            DocumentFile.project_id == test_project_with_user.id
        ).all()
        assert len(files) == 3

    def test_file_version_changelog_persistence(self, client, auth_headers, test_project_with_user, pdf_file_content, db_session):
        """测试版本变更日志持久化"""
        # 创建文件
        doc = DocumentFile(
            project_id=test_project_with_user.id,
            filename="changelog_test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        v1 = FileVersion(
            file_id=doc.id,
            version=1,
            storage_path=f"/path/v1_changelog_test.pdf",
            file_hash="hash1",
            file_size=1000
        )
        db_session.add(v1)
        db_session.commit()
        
        changelogs = ["初始版本", "修复bug", "添加新功能"]
        
        for i, changelog in enumerate(changelogs[1:], start=2):
            file_content = BytesIO(pdf_file_content + f"\n% {changelog}".encode())
            response = client.post(
                f"/api/v1/files/{doc.id}/versions",
                files={"file": ("changelog_test.pdf", file_content, "application/pdf")},
                data={"changelog": changelog},
                headers=auth_headers
            )
            assert response.status_code == 201
        
        # 验证变更日志
        versions_response = client.get(f"/api/v1/files/{doc.id}/versions", headers=auth_headers)
        versions = versions_response.json()["data"]["versions"]
        
        # 版本按降序排列
        for i, version in enumerate(reversed(versions)):
            if i == 0:
                assert version["changelog"] is None or version["changelog"] == ""
            else:
                assert version["changelog"] == changelogs[i]
