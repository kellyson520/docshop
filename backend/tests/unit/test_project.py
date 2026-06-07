"""
项目管理模块单元测试

测试项目相关的API功能，包括项目的增删改查、分享令牌管理等。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.exceptions import ResourceNotFound, ValidationError, PermissionDenied, DatabaseError


# ===== Fixtures =====

@pytest.fixture
def mock_project():
    """创建模拟项目"""
    project = Mock()
    project.id = "test-project-id-123"
    project.name = "测试项目"
    project.description = "这是一个测试项目"
    project.owner_id = "test-user-id-123"
    project.share_token = "test_share_token_123"
    project.is_public = 0
    project.created_at = datetime.utcnow().isoformat() + "Z"
    project.updated_at = datetime.utcnow().isoformat() + "Z"
    return project


@pytest.fixture
def mock_public_project():
    """创建模拟公开项目"""
    project = Mock()
    project.id = "public-project-id-456"
    project.name = "公开测试项目"
    project.description = "这是一个公开测试项目"
    project.owner_id = "other-user-id-456"
    project.share_token = "public_share_token_456"
    project.is_public = 1
    project.created_at = datetime.utcnow().isoformat() + "Z"
    project.updated_at = datetime.utcnow().isoformat() + "Z"
    return project


@pytest.fixture
def project_create_data():
    """项目创建数据"""
    return {
        "name": "新项目",
        "description": "项目描述",
        "is_public": 0
    }


@pytest.fixture
def project_update_data():
    """项目更新数据"""
    return {
        "name": "更新的项目名称",
        "description": "更新的项目描述",
        "is_public": 1
    }


# ===== 项目创建测试 =====

class TestCreateProject:
    """测试创建项目功能"""

    def test_create_project_success(self, client, auth_headers, db_session):
        """测试成功创建项目"""
        response = client.post("/api/v1/projects", json={
            "name": "我的新项目",
            "description": "项目描述",
            "is_public": 0
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "我的新项目"
        assert data["data"]["description"] == "项目描述"
        assert data["data"]["is_public"] == 0
        assert "id" in data["data"]
        assert "share_token" in data["data"]
        assert data["data"]["file_count"] == 0

    def test_create_project_without_description(self, client, auth_headers):
        """测试创建项目不提供描述"""
        response = client.post("/api/v1/projects", json={
            "name": "无描述项目",
            "is_public": 0
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["name"] == "无描述项目"
        assert data["data"]["description"] is None

    def test_create_project_public(self, client, auth_headers):
        """测试创建公开项目"""
        response = client.post("/api/v1/projects", json={
            "name": "公开项目",
            "description": "这是一个公开项目",
            "is_public": 1
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["is_public"] == 1

    def test_create_project_with_duplicate_name(self, client, auth_headers, test_user, db_session):
        """测试创建同名项目"""
        # 先创建一个项目
        from app.models.project import Project
        project = Project(
            name="重复项目名称",
            description="第一个项目",
            owner_id=test_user.id,
            share_token="token123"
        )
        db_session.add(project)
        db_session.commit()
        
        # 尝试创建同名项目
        response = client.post("/api/v1/projects", json={
            "name": "重复项目名称",
            "description": "第二个项目"
        }, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "项目名称已存在" in data["message"]

    def test_create_project_with_empty_name(self, client, auth_headers):
        """测试创建项目名称为空"""
        response = client.post("/api/v1/projects", json={
            "name": "",
            "description": "项目描述"
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_project_with_whitespace_only_name(self, client, auth_headers):
        """测试创建项目名称只包含空白字符"""
        response = client.post("/api/v1/projects", json={
            "name": "   ",
            "description": "项目描述"
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_project_with_very_long_name(self, client, auth_headers):
        """测试创建项目名称过长"""
        response = client.post("/api/v1/projects", json={
            "name": "a" * 101,  # 超过100字符限制
            "description": "项目描述"
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_project_with_very_long_description(self, client, auth_headers):
        """测试创建项目描述过长"""
        response = client.post("/api/v1/projects", json={
            "name": "正常名称",
            "description": "a" * 501  # 超过500字符限制
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_project_without_auth(self, client):
        """测试未认证创建项目"""
        response = client.post("/api/v1/projects", json={
            "name": "测试项目",
            "description": "项目描述"
        })
        
        assert response.status_code == 403

    def test_create_project_auto_generates_share_token(self, client, auth_headers):
        """测试创建项目自动生成分享令牌"""
        response = client.post("/api/v1/projects", json={
            "name": "分享测试项目"
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        share_token = data["data"]["share_token"]
        assert share_token is not None
        assert len(share_token) > 20  # 分享令牌应该足够长


# ===== 项目列表测试 =====

class TestListProjects:
    """测试获取项目列表功能"""

    def test_list_projects_success(self, client, auth_headers, test_user, db_session):
        """测试成功获取项目列表"""
        # 创建一些测试项目
        from app.models.project import Project
        for i in range(3):
            project = Project(
                name=f"列表项目{i+1}",
                description=f"描述{i+1}",
                owner_id=test_user.id,
                share_token=f"token{i+1}"
            )
            db_session.add(project)
        db_session.commit()
        
        response = client.get("/api/v1/projects", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "data" in data
        assert data["data"]["total"] >= 3
        assert len(data["data"]["items"]) >= 3

    def test_list_projects_with_pagination(self, client, auth_headers, test_user, db_session):
        """测试项目列表分页"""
        # 创建多个项目
        from app.models.project import Project
        for i in range(10):
            project = Project(
                name=f"分页项目{i+1}",
                owner_id=test_user.id,
                share_token=f"token{i+1}"
            )
            db_session.add(project)
        db_session.commit()
        
        response = client.get("/api/v1/projects?page=1&page_size=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 5
        assert len(data["data"]["items"]) == 5

    def test_list_projects_with_keyword_search(self, client, auth_headers, test_user, db_session):
        """测试项目列表关键词搜索"""
        from app.models.project import Project
        # 创建匹配和不匹配的项目
        project1 = Project(name="搜索目标项目", owner_id=test_user.id, share_token="token1")
        project2 = Project(name="其他项目", owner_id=test_user.id, share_token="token2")
        db_session.add_all([project1, project2])
        db_session.commit()
        
        response = client.get("/api/v1/projects?keyword=搜索", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # 应该只返回匹配的项目
        for item in data["data"]["items"]:
            assert "搜索" in item["name"]

    def test_list_projects_with_sorting(self, client, auth_headers, test_user, db_session):
        """测试项目列表排序"""
        from app.models.project import Project
        # 创建项目
        project1 = Project(name="A项目", owner_id=test_user.id, share_token="token1")
        project2 = Project(name="B项目", owner_id=test_user.id, share_token="token2")
        db_session.add_all([project1, project2])
        db_session.commit()
        
        # 按名称升序排序
        response = client.get("/api/v1/projects?sort_by=name&sort_order=asc", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["data"]["items"]]
        # 验证升序排列
        assert names == sorted(names)

    def test_list_projects_only_returns_own_projects(self, client, auth_headers, test_user, db_session):
        """测试只返回自己的项目"""
        from app.models.project import Project
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        # 创建两个用户的项目
        own_project = Project(name="我的项目", owner_id=test_user.id, share_token="token1")
        other_project = Project(name="他人项目", owner_id=other_user.id, share_token="token2")
        db_session.add_all([own_project, other_project])
        db_session.commit()
        
        response = client.get("/api/v1/projects", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        # 只应该看到"我的项目"
        project_names = [item["name"] for item in data["data"]["items"]]
        assert "我的项目" in project_names
        assert "他人项目" not in project_names

    def test_list_projects_without_auth(self, client):
        """测试未认证获取项目列表"""
        response = client.get("/api/v1/projects")
        
        assert response.status_code == 403

    def test_list_projects_invalid_page_number(self, client, auth_headers):
        """测试无效页码"""
        response = client.get("/api/v1/projects?page=0", headers=auth_headers)
        
        assert response.status_code == 422

    def test_list_projects_invalid_page_size(self, client, auth_headers):
        """测试无效每页数量"""
        response = client.get("/api/v1/projects?page_size=101", headers=auth_headers)
        
        assert response.status_code == 422


# ===== 项目详情测试 =====

class TestGetProject:
    """测试获取项目详情功能"""

    def test_get_project_success(self, client, auth_headers, test_user, db_session):
        """测试成功获取项目详情"""
        from app.models.project import Project
        project = Project(
            name="详情测试项目",
            description="项目详情描述",
            owner_id=test_user.id,
            share_token="detail_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["id"] == project.id
        assert data["data"]["name"] == "详情测试项目"
        assert data["data"]["description"] == "项目详情描述"

    def test_get_project_not_found(self, client, auth_headers):
        """测试获取不存在的项目"""
        response = client.get("/api/v1/projects/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["message"] or "not found" in data["message"].lower()

    def test_get_project_without_permission(self, client, auth_headers, db_session):
        """测试获取无权限的项目"""
        from app.models.project import Project
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户和项目
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser2", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        project = Project(
            name="私有项目",
            owner_id=other_user.id,
            is_public=0,
            share_token="private_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 404  # 或403，取决于实现

    def test_get_public_project_without_ownership(self, client, auth_headers, db_session):
        """测试获取他人的公开项目"""
        from app.models.project import Project
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户和公开项目
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser3", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        project = Project(
            name="公开项目",
            owner_id=other_user.id,
            is_public=1,
            share_token="public_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        # 公开项目应该可以访问
        assert response.status_code == 200

    def test_get_project_includes_file_count(self, client, auth_headers, test_user, db_session):
        """测试项目详情包含文件数量"""
        from app.models.project import Project
        from app.models.document_file import DocumentFile
        
        project = Project(
            name="带文件的项目",
            owner_id=test_user.id,
            share_token="files_token"
        )
        db_session.add(project)
        db_session.commit()
        
        # 添加文件
        for i in range(3):
            doc = DocumentFile(
                project_id=project.id,
                filename=f"file{i}.pdf",
                file_type="pdf",
                current_version=1
            )
            db_session.add(doc)
        db_session.commit()
        
        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["file_count"] == 3


# ===== 项目更新测试 =====

class TestUpdateProject:
    """测试更新项目功能"""

    def test_update_project_success(self, client, auth_headers, test_user, db_session):
        """测试成功更新项目"""
        from app.models.project import Project
        project = Project(
            name="原项目名称",
            description="原描述",
            owner_id=test_user.id,
            share_token="update_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.put(f"/api/v1/projects/{project.id}", json={
            "name": "新项目名称",
            "description": "新描述",
            "is_public": 1
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "新项目名称"
        assert data["data"]["description"] == "新描述"
        assert data["data"]["is_public"] == 1

    def test_update_project_partial(self, client, auth_headers, test_user, db_session):
        """测试部分更新项目"""
        from app.models.project import Project
        project = Project(
            name="原名称",
            description="原描述",
            owner_id=test_user.id,
            share_token="partial_token"
        )
        db_session.add(project)
        db_session.commit()
        
        # 只更新名称
        response = client.put(f"/api/v1/projects/{project.id}", json={
            "name": "仅更新名称"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "仅更新名称"
        assert data["data"]["description"] == "原描述"  # 未改变

    def test_update_project_not_found(self, client, auth_headers):
        """测试更新不存在的项目"""
        response = client.put("/api/v1/projects/non-existent-id", json={
            "name": "新名称"
        }, headers=auth_headers)
        
        assert response.status_code == 404

    def test_update_project_without_permission(self, client, auth_headers, db_session):
        """测试更新无权限的项目"""
        from app.models.project import Project
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户的项目
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser4", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        project = Project(
            name="他人项目",
            owner_id=other_user.id,
            share_token="other_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.put(f"/api/v1/projects/{project.id}", json={
            "name": "试图修改"
        }, headers=auth_headers)
        
        assert response.status_code == 403

    def test_update_project_with_duplicate_name(self, client, auth_headers, test_user, db_session):
        """测试更新为已存在的项目名称"""
        from app.models.project import Project
        
        # 创建两个项目
        project1 = Project(name="项目A", owner_id=test_user.id, share_token="tokenA")
        project2 = Project(name="项目B", owner_id=test_user.id, share_token="tokenB")
        db_session.add_all([project1, project2])
        db_session.commit()
        
        # 尝试将项目B改名为项目A
        response = client.put(f"/api/v1/projects/{project2.id}", json={
            "name": "项目A"
        }, headers=auth_headers)
        
        assert response.status_code == 400
        assert "项目名称已存在" in response.json()["message"]

    def test_update_project_with_empty_name(self, client, auth_headers, test_user, db_session):
        """测试更新项目名称为空"""
        from app.models.project import Project
        project = Project(name="原名称", owner_id=test_user.id, share_token="token")
        db_session.add(project)
        db_session.commit()
        
        response = client.put(f"/api/v1/projects/{project.id}", json={
            "name": ""
        }, headers=auth_headers)
        
        assert response.status_code == 422

    def test_update_project_without_auth(self, client, test_user, db_session):
        """测试未认证更新项目"""
        from app.models.project import Project
        project = Project(name="测试项目", owner_id=test_user.id, share_token="token")
        db_session.add(project)
        db_session.commit()
        
        response = client.put(f"/api/v1/projects/{project.id}", json={
            "name": "新名称"
        })
        
        assert response.status_code == 403


# ===== 项目删除测试 =====

class TestDeleteProject:
    """测试删除项目功能"""

    def test_delete_project_success(self, client, auth_headers, test_user, db_session):
        """测试成功删除项目"""
        from app.models.project import Project
        project = Project(
            name="待删除项目",
            owner_id=test_user.id,
            share_token="delete_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # 验证项目已被删除
        deleted_project = db_session.query(Project).filter(Project.id == project.id).first()
        assert deleted_project is None

    def test_delete_project_not_found(self, client, auth_headers):
        """测试删除不存在的项目"""
        response = client.delete("/api/v1/projects/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404

    def test_delete_project_without_permission(self, client, auth_headers, db_session):
        """测试删除无权限的项目"""
        from app.models.project import Project
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户的项目
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser5", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        project = Project(
            name="他人项目",
            owner_id=other_user.id,
            share_token="other_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 403

    def test_delete_project_cascades_files(self, client, auth_headers, test_user, db_session):
        """测试删除项目级联删除文件"""
        from app.models.project import Project
        from app.models.document_file import DocumentFile
        
        project = Project(
            name="带文件的项目",
            owner_id=test_user.id,
            share_token="cascade_token"
        )
        db_session.add(project)
        db_session.commit()
        
        # 添加文件
        doc = DocumentFile(
            project_id=project.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(doc)
        db_session.commit()
        
        # 删除项目
        response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # 验证文件也被删除
        deleted_doc = db_session.query(DocumentFile).filter(DocumentFile.id == doc.id).first()
        assert deleted_doc is None

    def test_delete_project_without_auth(self, client, test_user, db_session):
        """测试未认证删除项目"""
        from app.models.project import Project
        project = Project(name="测试项目", owner_id=test_user.id, share_token="token")
        db_session.add(project)
        db_session.commit()
        
        response = client.delete(f"/api/v1/projects/{project.id}")
        
        assert response.status_code == 403


# ===== 分享令牌测试 =====

class TestRegenerateToken:
    """测试重新生成分享令牌功能"""

    def test_regenerate_token_success(self, client, auth_headers, test_user, db_session):
        """测试成功重新生成分享令牌"""
        from app.models.project import Project
        project = Project(
            name="分享项目",
            owner_id=test_user.id,
            share_token="old_token_123"
        )
        db_session.add(project)
        db_session.commit()
        
        old_token = project.share_token
        
        response = client.post(f"/api/v1/projects/{project.id}/regenerate-token", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        new_token = data["data"]["share_token"]
        
        assert new_token != old_token
        assert len(new_token) > 20

    def test_regenerate_token_not_found(self, client, auth_headers):
        """测试为不存在的项目重新生成令牌"""
        response = client.post("/api/v1/projects/non-existent-id/regenerate-token", headers=auth_headers)
        
        assert response.status_code == 404

    def test_regenerate_token_without_permission(self, client, auth_headers, db_session):
        """测试为无权限的项目重新生成令牌"""
        from app.models.project import Project
        from app.models.user import User
        import bcrypt
        
        # 创建另一个用户的项目
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser6", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        
        project = Project(
            name="他人项目",
            owner_id=other_user.id,
            share_token="other_token"
        )
        db_session.add(project)
        db_session.commit()
        
        response = client.post(f"/api/v1/projects/{project.id}/regenerate-token", headers=auth_headers)
        
        assert response.status_code == 403

    def test_regenerate_token_without_auth(self, client, test_user, db_session):
        """测试未认证重新生成令牌"""
        from app.models.project import Project
        project = Project(name="测试项目", owner_id=test_user.id, share_token="token")
        db_session.add(project)
        db_session.commit()
        
        response = client.post(f"/api/v1/projects/{project.id}/regenerate-token")
        
        assert response.status_code == 403


# ===== 项目统计测试 =====

class TestProjectStats:
    """测试项目统计功能"""

    def test_get_project_stats_success(self, client, auth_headers, test_user, db_session):
        """测试成功获取项目统计"""
        from app.models.project import Project
        from app.models.document_file import DocumentFile
        from app.models.file_version import FileVersion
        
        project = Project(
            name="统计测试项目",
            owner_id=test_user.id,
            share_token="stats_token"
        )
        db_session.add(project)
        db_session.commit()
        
        # 添加文件和版本
        doc = DocumentFile(
            project_id=project.id,
            filename="test.pdf",
            file_type="pdf",
            current_version=2
        )
        db_session.add(doc)
        db_session.commit()
        
        # 添加版本
        v1 = FileVersion(file_id=doc.id, version=1, storage_path="/path/v1", file_hash="hash1", file_size=1000)
        v2 = FileVersion(file_id=doc.id, version=2, storage_path="/path/v2", file_hash="hash2", file_size=1200)
        db_session.add_all([v1, v2])
        db_session.commit()
        
        response = client.get(f"/api/v1/projects/{project.id}/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["project_id"] == project.id
        assert data["data"]["file_count"] == 1
        assert data["data"]["version_count"] == 2

    def test_get_project_stats_not_found(self, client, auth_headers):
        """测试获取不存在的项目统计"""
        response = client.get("/api/v1/projects/non-existent-id/stats", headers=auth_headers)
        
        assert response.status_code == 404

    def test_get_project_stats_without_auth(self, client, test_user, db_session):
        """测试未认证获取项目统计"""
        from app.models.project import Project
        project = Project(name="测试项目", owner_id=test_user.id, share_token="token")
        db_session.add(project)
        db_session.commit()
        
        response = client.get(f"/api/v1/projects/{project.id}/stats")
        
        assert response.status_code == 403


# ===== 请求模型验证测试 =====

class TestProjectRequestModels:
    """测试项目请求模型"""

    def test_project_create_valid(self):
        """测试有效项目创建"""
        request = ProjectCreate(name="测试项目", description="描述", is_public=0)
        assert request.name == "测试项目"
        assert request.description == "描述"
        assert request.is_public == 0

    def test_project_create_without_optional_fields(self):
        """测试项目创建不带可选字段"""
        request = ProjectCreate(name="测试项目")
        assert request.name == "测试项目"
        assert request.description is None
        assert request.is_public == 0  # 默认值

    def test_project_update_valid(self):
        """测试有效项目更新"""
        request = ProjectUpdate(name="新名称", description="新描述", is_public=1)
        assert request.name == "新名称"
        assert request.description == "新描述"
        assert request.is_public == 1

    def test_project_update_partial(self):
        """测试部分项目更新"""
        request = ProjectUpdate(name="仅名称")
        assert request.name == "仅名称"
        assert request.description is None
        assert request.is_public is None

    def test_project_response_model(self):
        """测试项目响应模型"""
        response = ProjectResponse(
            id="project-id-123",
            name="测试项目",
            description="项目描述",
            share_token="token123",
            is_public=0,
            file_count=5,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        assert response.id == "project-id-123"
        assert response.name == "测试项目"
        assert response.file_count == 5


# ===== 边界情况测试 =====

class TestProjectEdgeCases:
    """项目边界情况测试"""

    def test_create_project_with_unicode_name(self, client, auth_headers):
        """测试使用Unicode名称创建项目"""
        response = client.post("/api/v1/projects", json={
            "name": "测试项目🚀",
            "description": "Unicode描述"
        }, headers=auth_headers)
        
        assert response.status_code == 201
        assert response.json()["data"]["name"] == "测试项目🚀"

    def test_create_project_with_special_characters_in_name(self, client, auth_headers):
        """测试项目名称包含特殊字符"""
        response = client.post("/api/v1/projects", json={
            "name": "项目-测试_2024.v1",
            "description": "特殊字符"
        }, headers=auth_headers)
        
        assert response.status_code == 201

    def test_update_project_with_same_name(self, client, auth_headers, test_user, db_session):
        """测试更新项目为相同名称"""
        from app.models.project import Project
        project = Project(name="相同名称", owner_id=test_user.id, share_token="token")
        db_session.add(project)
        db_session.commit()
        
        # 更新为相同名称应该成功
        response = client.put(f"/api/v1/projects/{project.id}", json={
            "name": "相同名称"
        }, headers=auth_headers)
        
        assert response.status_code == 200

    def test_list_projects_empty_result(self, client, auth_headers):
        """测试获取空项目列表"""
        response = client.get("/api/v1/projects", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] >= 0
        assert isinstance(data["data"]["items"], list)

    def test_project_name_stripping(self, client, auth_headers):
        """测试项目名称去除首尾空格"""
        response = client.post("/api/v1/projects", json={
            "name": "  带空格的项目  ",
            "description": "描述"
        }, headers=auth_headers)
        
        assert response.status_code == 201
        # 名称应该被去除首尾空格
        name = response.json()["data"]["name"]
        assert not name.startswith(" ")
        assert not name.endswith(" ")


# ===== 集成测试 =====

class TestProjectIntegration:
    """项目集成测试"""

    def test_create_list_get_update_delete_flow(self, client, auth_headers):
        """测试完整的项目CRUD流程"""
        # 创建项目
        create_response = client.post("/api/v1/projects", json={
            "name": "完整流程项目",
            "description": "完整流程描述"
        }, headers=auth_headers)
        
        assert create_response.status_code == 201
        project_id = create_response.json()["data"]["id"]
        
        # 获取项目列表，应该包含新项目
        list_response = client.get("/api/v1/projects", headers=auth_headers)
        assert list_response.status_code == 200
        project_ids = [p["id"] for p in list_response.json()["data"]["items"]]
        assert project_id in project_ids
        
        # 获取项目详情
        get_response = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"]["name"] == "完整流程项目"
        
        # 更新项目
        update_response = client.put(f"/api/v1/projects/{project_id}", json={
            "name": "更新后的项目"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "更新后的项目"
        
        # 重新生成令牌
        token_response = client.post(f"/api/v1/projects/{project_id}/regenerate-token", headers=auth_headers)
        assert token_response.status_code == 200
        new_token = token_response.json()["data"]["share_token"]
        
        # 删除项目
        delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert delete_response.status_code == 204
        
        # 验证项目已删除
        get_deleted_response = client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
        assert get_deleted_response.status_code == 404

    def test_multiple_projects_pagination(self, client, auth_headers, test_user, db_session):
        """测试多个项目的分页"""
        from app.models.project import Project
        
        # 创建15个项目
        for i in range(15):
            project = Project(
                name=f"分页项目{i+1:02d}",
                owner_id=test_user.id,
                share_token=f"token{i+1}"
            )
            db_session.add(project)
        db_session.commit()
        
        # 获取第一页
        page1 = client.get("/api/v1/projects?page=1&page_size=10", headers=auth_headers)
        assert page1.status_code == 200
        assert len(page1.json()["data"]["items"]) == 10
        
        # 获取第二页
        page2 = client.get("/api/v1/projects?page=2&page_size=10", headers=auth_headers)
        assert page2.status_code == 200
        assert len(page2.json()["data"]["items"]) >= 5

    def test_project_search_across_multiple_projects(self, client, auth_headers, test_user, db_session):
        """测试在多个项目中搜索"""
        from app.models.project import Project
        
        # 创建匹配和不匹配的项目
        names = ["苹果项目", "香蕉项目", "苹果香蕉", "其他项目"]
        for name in names:
            project = Project(name=name, owner_id=test_user.id, share_token=f"token_{name}")
            db_session.add(project)
        db_session.commit()
        
        # 搜索"苹果"
        response = client.get("/api/v1/projects?keyword=苹果", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        for item in items:
            assert "苹果" in item["name"]
