"""
项目管理模块测试
测试项目 CRUD、分页、搜索
"""
import io
import zipfile

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.project import Project
from app.models.project_folder import ProjectFolder
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.share_token import ShareToken
from app.config import settings


class TestProjects:
    """项目相关测试"""

    def test_create_project(self, client, auth_headers, db_session):
        """测试创建项目"""
        response = client.post("/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "测试项目",
                "description": "这是一个测试项目"
            }
        )

        # create_project 路由设置了 status_code=201
        assert response.status_code == 201
        data = response.json()
        # 新格式: {"code": 0, "data": {"name": "测试项目", ...}}
        assert data["code"] == 0
        assert data["data"]["name"] == "测试项目"
        assert data["data"]["description"] == "这是一个测试项目"

    def test_create_project_no_auth(self, client):
        """测试未认证创建项目"""
        response = client.post("/api/v1/projects", json={
            "name": "测试项目",
            "description": "描述"
        })

        # HTTPBearer 返回 403
        assert response.status_code in [401, 403]

    def test_create_project_empty_name(self, client, auth_headers):
        """测试创建项目名称为空"""
        response = client.post("/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "",
                "description": "描述"
            }
        )

        # Pydantic 校验失败返回 422
        assert response.status_code == 422

    def test_create_project_whitespace_only_name(self, client, auth_headers):
        """测试创建项目名称只包含空白字符（行72, 75）"""
        response = client.post("/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "   \t  ",
                "description": "描述"
            }
        )

        # Pydantic 校验失败返回 422
        assert response.status_code == 422

    def test_create_project_duplicate_name(self, client, auth_headers, db_session, test_user):
        """测试创建重复名称项目"""
        project = Project(name="重复名称项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()

        response = client.post("/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "重复名称项目",
                "description": "另一个描述"
            }
        )

        # 应返回 400 ValidationError
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 40001

    def test_create_project_db_error(self, client, auth_headers, db_session):
        """测试创建项目时数据库错误（行344-350）"""
        # 使用 patch.object 直接 mock db_session.commit
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("DB error")):
            response = client.post("/api/v1/projects",
                headers=auth_headers,
                json={
                    "name": "数据库错误项目",
                    "description": "描述"
                }
            )

        # DatabaseError 被中间件捕获为系统异常，返回 500
        assert response.status_code == 500

    def test_create_project_generic_error(self, client, auth_headers, db_session):
        """测试创建项目时通用错误（行351-357）"""
        # Mock secrets.token_urlsafe 来触发通用异常
        with patch("app.routers.projects.secrets") as mock_secrets:
            mock_secrets.token_urlsafe.side_effect = RuntimeError("Token generation failed")

            response = client.post("/api/v1/projects",
                headers=auth_headers,
                json={
                    "name": "通用错误项目",
                    "description": "描述"
                }
            )

        # 异常被中间件捕获，返回 500
        assert response.status_code == 500

    def test_get_project_list(self, client, auth_headers, db_session, test_user):
        """测试获取项目列表"""
        # 创建测试项目
        for i in range(5):
            project = Project(
                name=f"项目{i+1}",
                description=f"描述{i+1}",
                owner_id=test_user.id
            )
            db_session.add(project)
        db_session.commit()

        response = client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) >= 5
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]

    def test_get_project_list_prefers_managed_share_token(self, client, auth_headers, db_session, test_user):
        """项目列表应返回可用的受管分享令牌，而不是遗留 project.share_token。"""
        project = Project(
            name="Managed Token Project",
            description="Uses managed share token",
            owner_id=test_user.id,
            share_token="legacy-project-token",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        share_token = ShareToken(
            token="managed-project-token",
            name="Managed project share",
            resource_type="project",
            resource_id=project.id,
            is_active=1,
            created_by=test_user.id,
        )
        db_session.add(share_token)
        db_session.commit()

        response = client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        target = next((item for item in data["data"]["items"] if item["id"] == project.id), None)
        assert target is not None
        assert target["share_token"] == share_token.token

    def test_get_project_list_pagination(self, client, auth_headers, db_session, test_user):
        """测试项目列表分页"""
        # 创建多个测试项目
        for i in range(10):
            project = Project(
                name=f"分页项目{i+1}",
                description=f"描述{i+1}",
                owner_id=test_user.id
            )
            db_session.add(project)
        db_session.commit()

        # 测试第一页
        response = client.get("/api/v1/projects?page=1&page_size=5", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 5
        assert data["data"]["page"] == 1

        # 测试第二页
        response = client.get("/api/v1/projects?page=2&page_size=5", headers=auth_headers)
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 5
        assert data["data"]["page"] == 2

    def test_get_project_list_search(self, client, auth_headers, db_session, test_user):
        """测试项目搜索"""
        # 创建测试项目
        project1 = Project(name="重要项目", description="描述1", owner_id=test_user.id)
        project2 = Project(name="普通项目", description="描述2", owner_id=test_user.id)
        db_session.add_all([project1, project2])
        db_session.commit()

        response = client.get("/api/v1/projects?keyword=重要", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) >= 1
        assert any(p["name"] == "重要项目" for p in data["data"]["items"])

    def test_get_project_list_with_file_count(self, client, auth_headers, db_session, test_user):
        """测试项目列表包含文件数量（行85, 116, 118）"""
        from app.models.document_file import DocumentFile

        project = Project(name="有文件项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 为项目添加文件
        for i in range(3):
            doc_file = DocumentFile(
                project_id=project.id,
                filename=f"file{i}.pdf",
                file_type="pdf",
                current_version=1
            )
            db_session.add(doc_file)
        db_session.commit()

        response = client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 找到有文件的项目
        target = next((p for p in data["data"]["items"] if p["id"] == project.id), None)
        assert target is not None
        assert target["file_count"] == 3

    def test_get_project_detail(self, client, auth_headers, db_session, test_user):
        """测试获取项目详情"""
        project = Project(name="详情测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "详情测试项目"
        assert data["data"]["id"] == project.id

    def test_get_project_detail_prefers_managed_share_token(self, client, auth_headers, db_session, test_user):
        """项目详情应返回可用的受管分享令牌，供复制链接和公开入口复用。"""
        project = Project(
            name="Managed Detail Token Project",
            description="Managed token detail view",
            owner_id=test_user.id,
            share_token="legacy-detail-token",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        share_token = ShareToken(
            token="managed-detail-project-token",
            name="Managed detail share",
            resource_type="project",
            resource_id=project.id,
            is_active=1,
            created_by=test_user.id,
        )
        db_session.add(share_token)
        db_session.commit()

        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["share_token"] == share_token.token

    def test_download_project_folder_bundle_returns_zip(self, client, auth_headers, db_session, test_user, tmp_path, monkeypatch):
        upload_root = tmp_path / "uploads"
        upload_root.mkdir()
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))

        project = Project(name="合同项目", description="desc", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        folder = ProjectFolder(project_id=project.id, name="合同资料")
        db_session.add(folder)
        db_session.commit()
        db_session.refresh(folder)

        stored_file = upload_root / "contract.pdf"
        stored_file.write_bytes(b"folder bundle pdf")

        doc_file = DocumentFile(
            project_id=project.id,
            filename="contract.pdf",
            display_name="合同.pdf",
            file_type="pdf",
            current_version=1,
            folder_id=folder.id,
        )
        db_session.add(doc_file)
        db_session.commit()
        db_session.refresh(doc_file)

        db_session.add(
            FileVersion(
                file_id=doc_file.id,
                version=1,
                sort_order=1,
                storage_path=str(stored_file),
                file_hash="folder-bundle",
                file_size=stored_file.stat().st_size,
            )
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/projects/{project.id}/folders/{folder.id}/download",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/zip")
        assert "contract.pdf" in response.text or response.content

        archive = zipfile.ZipFile(io.BytesIO(response.content))
        assert archive.namelist() == ["合同资料/contract.pdf"]
        assert archive.read("合同资料/contract.pdf") == b"folder bundle pdf"

    def test_download_project_folder_bundle_allows_document_store_root(self, client, auth_headers, db_session, test_user, tmp_path, monkeypatch):
        from app.services import document_store
        from app.services import storage_path_policy

        documents_root = tmp_path / "documents"
        monkeypatch.setattr(document_store, "ROOT", str(documents_root))
        monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

        project = Project(name="统一存储项目", description="desc", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        folder = ProjectFolder(project_id=project.id, name="统一存储合同")
        db_session.add(folder)
        db_session.commit()
        db_session.refresh(folder)

        stored_file = documents_root / "project-folder-doc" / "original" / "contract.pdf"
        stored_file.parent.mkdir(parents=True, exist_ok=True)
        stored_file.write_bytes(b"project folder document-store pdf")

        doc_file = DocumentFile(
            project_id=project.id,
            filename="contract.pdf",
            display_name="合同.pdf",
            file_type="pdf",
            current_version=1,
            folder_id=folder.id,
        )
        db_session.add(doc_file)
        db_session.commit()
        db_session.refresh(doc_file)

        db_session.add(
            FileVersion(
                file_id=doc_file.id,
                version=1,
                sort_order=1,
                storage_path=str(stored_file),
                file_hash="folder-bundle-docstore",
                file_size=stored_file.stat().st_size,
            )
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/projects/{project.id}/folders/{folder.id}/download",
            headers=auth_headers,
        )

        assert response.status_code == 200
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        assert archive.namelist() == ["统一存储合同/contract.pdf"]
        assert archive.read("统一存储合同/contract.pdf") == b"project folder document-store pdf"

        response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == project.name
        assert data["data"]["id"] == project.id

    def test_get_project_not_found(self, client, auth_headers):
        """测试获取不存在的项目"""
        response = client.get("/api/v1/projects/99999", headers=auth_headers)

        # ResourceNotFound -> HTTP 404, code 30001
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001

    def test_update_project(self, client, auth_headers, db_session, test_user):
        """测试更新项目"""
        project = Project(name="原名称", description="原描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.put(f"/api/v1/projects/{project.id}",
            headers=auth_headers,
            json={
                "name": "新名称",
                "description": "新描述"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "新名称"
        assert data["data"]["description"] == "新描述"

    def test_update_project_not_owner(self, client, auth_headers, db_session):
        """测试非所有者更新项目"""
        import bcrypt
        from app.models.user import User

        # 创建另一个用户
        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # 创建属于其他用户的项目
        project = Project(name="他人项目", description="描述", owner_id=other_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.put(f"/api/v1/projects/{project.id}",
            headers=auth_headers,
            json={"name": "新名称", "description": "新描述"}
        )

        # PermissionDenied -> HTTP 403, code 20004
        assert response.status_code == 403

    def test_update_project_not_found(self, client, auth_headers):
        """测试更新不存在的项目"""
        response = client.put("/api/v1/projects/99999",
            headers=auth_headers,
            json={"name": "新名称", "description": "新描述"}
        )

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001

    def test_update_project_name_conflict(self, client, auth_headers, db_session, test_user):
        """测试更新项目时名称冲突（行419）"""
        project1 = Project(name="项目A", description="描述A", owner_id=test_user.id)
        project2 = Project(name="项目B", description="描述B", owner_id=test_user.id)
        db_session.add_all([project1, project2])
        db_session.commit()
        db_session.refresh(project1)
        db_session.refresh(project2)

        # 将 project2 的名称改为 project1 的名称
        response = client.put(f"/api/v1/projects/{project2.id}",
            headers=auth_headers,
            json={"name": "项目A"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 40001

    def test_update_project_db_error(self, client, auth_headers, db_session, test_user):
        """测试更新项目时数据库错误（行462-473）"""
        project = Project(name="数据库错误更新项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("DB error")):
            response = client.put(f"/api/v1/projects/{project.id}",
                headers=auth_headers,
                json={"name": "新名称"}
            )

        assert response.status_code == 500

    def test_update_project_generic_error(self, client, auth_headers, db_session, test_user):
        """测试更新项目时通用错误（行469-473）"""
        project = Project(name="通用错误更新项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Mock db.refresh 来触发通用异常（在 commit 之后、return 之前）
        with patch.object(db_session, "refresh", side_effect=RuntimeError("Refresh error")):
            response = client.put(f"/api/v1/projects/{project.id}",
                headers=auth_headers,
                json={"name": "新名称"}
            )

        assert response.status_code == 500

    def test_delete_project(self, client, auth_headers, db_session, test_user):
        """测试删除项目"""
        project = Project(name="待删除项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)

        # delete_project 路由设置了 status_code=204
        assert response.status_code == 204

        # 验证已删除
        deleted_project = db_session.query(Project).filter(Project.id == project.id).first()
        assert deleted_project is None

    def test_delete_project_not_found(self, client, auth_headers):
        """测试删除不存在的项目"""
        response = client.delete("/api/v1/projects/99999", headers=auth_headers)

        # ResourceNotFound -> HTTP 404
        assert response.status_code == 404

    def test_delete_project_not_owner(self, client, auth_headers, db_session):
        """测试非所有者删除项目"""
        import bcrypt
        from app.models.user import User

        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser2", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        project = Project(name="他人删除项目", description="描述", owner_id=other_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 403

    def test_delete_project_db_error(self, client, auth_headers, db_session, test_user):
        """测试删除项目时数据库错误（行518-529）"""
        project = Project(name="数据库错误删除项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        with patch.object(db_session, "delete", side_effect=SQLAlchemyError("DB error")):
            response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 500

    def test_delete_project_generic_error(self, client, auth_headers, db_session, test_user):
        """测试删除项目时通用错误（行525-529）"""
        project = Project(name="通用错误删除项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Mock db.delete 来触发非 SQLAlchemyError 异常
        original_delete = db_session.delete
        call_count = [0]

        def side_effect_delete(item):
            call_count[0] += 1
            original_delete(item)
            if call_count[0] == 1:
                raise RuntimeError("Generic error")

        with patch.object(db_session, "delete", side_effect=side_effect_delete):
            response = client.delete(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 500

    def test_regenerate_token_success(self, client, auth_headers, db_session, test_user):
        """测试重新生成令牌成功"""
        project = Project(name="令牌项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        old_token = project.share_token

        response = client.post(f"/api/v1/projects/{project.id}/regenerate-token", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "share_token" in data["data"]
        assert data["data"]["share_token"] != old_token

    def test_regenerate_token_not_found(self, client, auth_headers):
        """测试重新生成不存在的项目的令牌"""
        response = client.post("/api/v1/projects/99999/regenerate-token", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001

    def test_regenerate_token_not_owner(self, client, auth_headers, db_session):
        """测试非所有者重新生成令牌"""
        import bcrypt
        from app.models.user import User

        hashed = bcrypt.hashpw(b"other123", bcrypt.gensalt()).decode('utf-8')
        other_user = User(username="otheruser3", password_hash=hashed, role="user")
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        project = Project(name="他人令牌项目", description="描述", owner_id=other_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.post(f"/api/v1/projects/{project.id}/regenerate-token", headers=auth_headers)

        assert response.status_code == 403

    def test_regenerate_token_db_error(self, client, auth_headers, db_session, test_user):
        """测试重新生成令牌时数据库错误（行579-585）"""
        project = Project(name="令牌数据库错误项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("DB error")):
            response = client.post(f"/api/v1/projects/{project.id}/regenerate-token", headers=auth_headers)

        assert response.status_code == 500

    def test_regenerate_token_generic_error(self, client, auth_headers, db_session, test_user):
        """测试重新生成令牌时通用错误（行586-593）"""
        project = Project(name="令牌通用错误项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Mock db.refresh 来触发通用异常
        with patch.object(db_session, "refresh", side_effect=RuntimeError("Refresh error")):
            response = client.post(f"/api/v1/projects/{project.id}/regenerate-token", headers=auth_headers)

        assert response.status_code == 500

    def test_get_project_stats(self, client, auth_headers, db_session, test_user):
        """测试获取项目统计信息"""
        project = Project(name="统计测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        response = client.get(f"/api/v1/projects/{project.id}/stats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "file_count" in data["data"]
        assert "version_count" in data["data"]

    def test_get_project_stats_with_files(self, client, auth_headers, db_session, test_user):
        """测试获取项目统计信息（含文件和版本）（行641-646）"""
        from app.models.document_file import DocumentFile
        from app.models.file_version import FileVersion

        project = Project(name="统计详细项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # 创建文件
        doc_file = DocumentFile(
            project_id=project.id,
            filename="stats.pdf",
            file_type="pdf",
            current_version=2
        )
        db_session.add(doc_file)
        db_session.commit()
        db_session.refresh(doc_file)

        # 创建版本
        for i in range(1, 3):
            version = FileVersion(
                file_id=doc_file.id,
                version=i,
                storage_path=f"/tmp/stats_v{i}.pdf",
                file_hash=f"hash_{i}",
                file_size=100,
            )
            db_session.add(version)
        db_session.commit()

        response = client.get(f"/api/v1/projects/{project.id}/stats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["file_count"] == 1
        assert data["data"]["version_count"] == 2

    def test_get_project_stats_not_found(self, client, auth_headers):
        """测试获取不存在项目的统计信息"""
        response = client.get("/api/v1/projects/99999/stats", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 30001

    def test_get_project_stats_error(self, client, auth_headers, db_session, test_user):
        """测试获取项目统计信息时错误（行641-646）"""
        project = Project(name="统计错误项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Mock success_response 来触发异常
        with patch("app.routers.projects.success_response", side_effect=RuntimeError("Response error")):
            response = client.get(f"/api/v1/projects/{project.id}/stats", headers=auth_headers)

        assert response.status_code == 500

    def test_get_project_detail_error(self, client, auth_headers, db_session, test_user):
        """测试获取项目详情时错误（行384-386）"""
        project = Project(name="详情错误项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        with patch("app.routers.projects._project_to_response", side_effect=RuntimeError("Response error")):
            response = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers)

        assert response.status_code == 500

    def test_get_project_list_error(self, client, auth_headers, db_session):
        """测试获取项目列表时错误（行278-280）"""
        # Mock success_response 来触发异常
        with patch("app.routers.projects.success_response", side_effect=RuntimeError("Response error")):
            response = client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 500
