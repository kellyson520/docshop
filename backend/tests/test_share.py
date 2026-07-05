"""
分享路由测试

测试覆盖率目标：100%
- get_shared_project 分享项目访问
- get_shared_file 分享文件访问
- get_shared_versions 分享版本列表
- get_shared_diffs 分享差异列表
- download_shared_version 分享文件下载
- _get_project_by_token 辅助函数
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status

from app.deps.auth import get_password_hash
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project
from app.models.resource_access_policy import ResourceAccessGroup, ResourceAccessPolicy
from app.models.share_token import ShareToken
from app.models.user import User
from app.models.user_group import UserGroup, UserGroupMember
from app.routers.share import (
    router,
    _get_project_by_token,
    get_shared_project,
    get_shared_file,
    get_shared_versions,
    get_shared_diffs,
    download_shared_version,
)


def _make_resolved(mock_project):
    return {"share_token": None, "project": mock_project, "file": None, "version": None, "legacy": True}


def _make_request(headers=None):
    request = MagicMock()
    request.headers = headers or {}
    return request


def _make_user(db_session, username: str, password: str = "test123", role: str = "user") -> User:
    user = User(username=username, password_hash=get_password_hash(password), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login_headers(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_policy(
    db_session,
    *,
    resource_type: str,
    resource_id: str,
    visibility: str,
    password: str | None = None,
    password_hint: str | None = None,
    group_codes: list[str] | None = None,
) -> ResourceAccessPolicy:
    policy = ResourceAccessPolicy(
        resource_type=resource_type,
        resource_id=resource_id,
        visibility=visibility,
        password_hash=get_password_hash(password) if password else None,
        password_hint=password_hint,
        allow_preview=1,
        allow_download_original=1,
        allow_download_converted=1,
        allow_diff=1,
        allow_versions=1,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    if group_codes:
        groups = db_session.query(UserGroup).filter(UserGroup.code.in_(group_codes)).all()
        for group in groups:
            db_session.add(ResourceAccessGroup(policy_id=policy.id, group_id=group.id))
        db_session.commit()

    return policy


def _make_legacy_public_project(
    db_session,
    tmp_path,
    monkeypatch,
    *,
    share_token: str,
    filename: str = "public.pdf",
    file_type: str = "pdf",
) -> tuple[Project, DocumentFile, FileVersion]:
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    owner = _make_user(db_session, f"owner-{share_token}")
    project = Project(
        name=f"Project {share_token}",
        description="legacy public browse project",
        owner_id=owner.id,
        is_public=1,
        share_token=share_token,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename=filename,
        display_name=f"Display {filename}",
        file_type=file_type,
        current_version=1,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    stored_file = upload_dir / filename
    stored_file.write_bytes(b"%PDF-1.4 legacy public preview")

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1,
        storage_path=str(stored_file),
        file_hash=f"hash-{share_token}",
        file_size=stored_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return project, doc_file, version


def _create_managed_share_token(
    db_session,
    *,
    created_by: str,
    resource_type: str,
    resource_id: str,
    token: str,
    name: str = "managed share",
    **overrides,
) -> ShareToken:
    defaults = {
        "allow_download": 1,
        "allow_preview": 1,
        "allow_diff": 1,
        "allow_versions": 1,
        "require_login": 0,
        "policy_mode": "override_with_token_policy",
    }
    defaults.update(overrides)
    share_token = ShareToken(
        token=token,
        name=name,
        resource_type=resource_type,
        resource_id=resource_id,
        created_by=created_by,
        **defaults,
    )
    db_session.add(share_token)
    db_session.commit()
    db_session.refresh(share_token)
    return share_token


class TestPublicProjectsSearch:
    """????????????????????"""

    def test_public_projects_keyword_matches_file_name(self, client, db_session):
        from app.models.project import Project
        from app.models.user import User
        from app.models.document_file import DocumentFile
        from app.deps.auth import get_password_hash

        owner = User(
            username="public-search-owner",
            password_hash=get_password_hash("test123"),
            role="user",
        )
        db_session.add(owner)
        db_session.commit()
        db_session.refresh(owner)

        project = Project(
            name="??????",
            description="??????",
            owner_id=owner.id,
            is_public=1,
            share_token="public-file-search-token",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        doc = DocumentFile(
            project_id=project.id,
            filename="????????.pdf",
            display_name="????????",
            file_type="pdf",
            current_version=1,
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get("/api/v1/share/public-projects?keyword=????")

        assert response.status_code == 200
        payload = response.json()
        names = [item["name"] for item in payload["data"]["items"]]
        assert "??????" in names
        matched = next(item for item in payload["data"]["items"] if item["name"] == "??????")
        assert matched["matched_file"]["filename"] == "????????.pdf"


class TestPublicExamDetail:
    def test_public_exams_list_refreshes_status_and_hides_expired_items(self, client, db_session, test_user):
        from datetime import timedelta

        from app.models.exam_schedule import ExamSchedule, ExamStatus
        from app.models.project import Project
        from app.utils.time import utc_now

        project = Project(
            name="Public Exam List Project",
            description="Project used by public exam list",
            owner_id=test_user.id,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        expired_exam = ExamSchedule(
            name="Expired Public Exam",
            description="Should not be listed on homepage",
            start_time=(utc_now() - timedelta(days=2)).isoformat() + "Z",
            end_time=(utc_now() - timedelta(days=1)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id,
        )
        ongoing_exam = ExamSchedule(
            name="Ongoing Public Exam",
            description="Should show as ongoing",
            start_time=(utc_now() - timedelta(minutes=30)).isoformat() + "Z",
            end_time=(utc_now() + timedelta(hours=1)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id,
        )
        future_exam = ExamSchedule(
            name="Future Public Exam",
            description="Should show as upcoming",
            start_time=(utc_now() + timedelta(days=1)).isoformat() + "Z",
            end_time=(utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.upcoming.value,
            created_by=test_user.id,
        )
        db_session.add_all([expired_exam, ongoing_exam, future_exam])
        db_session.commit()

        response = client.get("/api/v1/share/public-exams")

        assert response.status_code == 200
        items = response.json()["data"]
        by_id = {item["id"]: item for item in items}
        assert expired_exam.id not in by_id
        assert by_id[ongoing_exam.id]["status"] == ExamStatus.ongoing.value
        assert by_id[future_exam.id]["status"] == ExamStatus.upcoming.value

    def test_public_exam_detail_loads_from_homepage_card(self, client, db_session, test_user):
        from datetime import timedelta

        from app.models.exam_schedule import ExamSchedule
        from app.models.project import Project
        from app.utils.time import utc_now

        project = Project(
            name="Public Exam Project",
            description="Project used by public exam detail",
            owner_id=test_user.id,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="Homepage Card Exam",
            description="Clicking the public exam card should load detail",
            start_time=(utc_now() + timedelta(days=1)).isoformat() + "Z",
            end_time=(utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            created_by=test_user.id,
        )
        db_session.add(exam)
        db_session.commit()

        response = client.get(f"/api/v1/share/public-exams/{exam.id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 0
        assert payload["data"]["id"] == exam.id
        assert payload["data"]["name"] == "Homepage Card Exam"
        assert payload["data"]["status"] == "upcoming"

    def test_public_exam_detail_refreshes_future_stale_status(self, client, db_session, test_user):
        from datetime import timedelta

        from app.models.exam_schedule import ExamSchedule, ExamStatus
        from app.models.project import Project
        from app.utils.time import utc_now

        project = Project(
            name="Public Exam Detail Status Project",
            description="Project used by public exam detail status refresh",
            owner_id=test_user.id,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        exam = ExamSchedule(
            name="Future Exam With Stale Status",
            description="Future exam should not keep stale ongoing status",
            start_time=(utc_now() + timedelta(days=1)).isoformat() + "Z",
            end_time=(utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z",
            project_id=project.id,
            status=ExamStatus.ongoing.value,
            created_by=test_user.id,
        )
        db_session.add(exam)
        db_session.commit()

        response = client.get(f"/api/v1/share/public-exams/{exam.id}")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == ExamStatus.upcoming.value


class TestLegacyPublicAccessGrant:
    def test_legacy_project_share_root_is_rejected(self, client, db_session, tmp_path, monkeypatch):
        project, _doc_file, _version = _make_legacy_public_project(
            db_session,
            tmp_path,
            monkeypatch,
            share_token="legacy-public-project-password",
        )

        response = client.get(f"/api/v1/share/{project.share_token}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Share link not found"

    def test_legacy_project_share_file_routes_are_rejected(self, client, db_session, tmp_path, monkeypatch):
        project, doc_file, _version = _make_legacy_public_project(
            db_session,
            tmp_path,
            monkeypatch,
            share_token="legacy-public-file-password",
        )

        response = client.get(f"/api/v1/share/{project.share_token}/files/{doc_file.id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Share link not found"

    def test_legacy_project_public_access_unlock_is_rejected(self, client, db_session, tmp_path, monkeypatch):
        project, doc_file, _version = _make_legacy_public_project(
            db_session,
            tmp_path,
            monkeypatch,
            share_token="legacy-public-resource-ticket",
        )

        response = client.post(
            f"/api/v1/share/{project.share_token}/public-access/unlock",
            headers={"X-Access-Tab-Id": "tab-a"},
            json={
                "resource_type": "file",
                "resource_id": doc_file.id,
                "password": "FileSecret!1",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Share link not found"

    def test_legacy_project_resource_ticket_is_rejected(self, client, db_session, tmp_path, monkeypatch):
        project, doc_file, _version = _make_legacy_public_project(
            db_session,
            tmp_path,
            monkeypatch,
            share_token="legacy-public-groups",
        )

        response = client.post(
            f"/api/v1/share/{project.share_token}/resource-ticket",
            headers={"X-Access-Tab-Id": "tab-a", "X-Access-Grant": "grant-token"},
            json={
                "kind": "preview",
                "file_id": doc_file.id,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Share link not found"


class TestManagedSharePermissionDecoupling:
    def test_managed_share_token_ignores_public_file_password_policy(self, client, db_session, tmp_path, monkeypatch):
        project, doc_file, _version = _make_legacy_public_project(
            db_session,
            tmp_path,
            monkeypatch,
            share_token="decoupled-public-host-project",
        )
        _create_policy(
            db_session,
            resource_type="file",
            resource_id=doc_file.id,
            visibility="private",
        )
        share_token = _create_managed_share_token(
            db_session,
            created_by=project.owner_id,
            resource_type="file",
            resource_id=doc_file.id,
            token="managed-decoupled-file-token",
            name="managed decoupled file share",
            policy_mode="inherit_resource_policy",
        )

        response = client.get(f"/api/v1/share/{share_token.token}/files/{doc_file.id}")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["id"] == doc_file.id
        assert payload["share"]["type"] == "share_token"

    def test_managed_share_preview_ticket_ignores_public_private_file_policy(self, client, db_session, tmp_path, monkeypatch):
        project, doc_file, _version = _make_legacy_public_project(
            db_session,
            tmp_path,
            monkeypatch,
            share_token="decoupled-preview-host-project",
        )
        _create_policy(
            db_session,
            resource_type="file",
            resource_id=doc_file.id,
            visibility="private",
        )
        share_token = _create_managed_share_token(
            db_session,
            created_by=project.owner_id,
            resource_type="file",
            resource_id=doc_file.id,
            token="managed-decoupled-preview-token",
            name="managed decoupled preview share",
            password_hash=get_password_hash("ShareSecret!9"),
            password_hint="share-only",
            policy_mode="inherit_resource_policy",
        )

        unlock_response = client.post(
            f"/api/v1/share/{share_token.token}/unlock",
            headers={"X-Share-Tab-Id": "share-tab-a"},
            json={"password": "ShareSecret!9"},
        )

        assert unlock_response.status_code == 200
        share_grant = unlock_response.json()["data"]["grant_token"]

        ticket_response = client.post(
            f"/api/v1/share/{share_token.token}/resource-ticket",
            headers={
                "X-Share-Tab-Id": "share-tab-a",
                "X-Share-Grant": share_grant,
            },
            json={
                "kind": "preview",
                "file_id": doc_file.id,
            },
        )

        assert ticket_response.status_code == 200
        payload = ticket_response.json()["data"]
        assert isinstance(payload["ticket"], str) and payload["ticket"]


class TestGetProjectByToken:
    """_get_project_by_token 辅助函数测试"""

    def test_get_project_success(self):
        """测试成功获取项目"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Test Project"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            result = _get_project_by_token("valid-token", mock_db)

        assert result == mock_project

    def test_get_project_not_found(self):
        """测试项目不存在"""
        mock_db = MagicMock()

        with patch("app.routers.share.resolve_share_token", side_effect=HTTPException(status_code=404, detail="Share link not found")):
            with pytest.raises(HTTPException) as exc_info:
                _get_project_by_token("invalid-token", mock_db)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Share link not found"


class TestGetSharedProject:
    """get_shared_project 端点测试"""

    def test_get_shared_project_success(self):
        """测试成功获取分享项目"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        mock_project.description = "Test Description"
        mock_project.share_token = "token-123"
        mock_project.is_public = 1
        mock_project.created_at = "2024-01-01T00:00:00Z"
        mock_project.updated_at = "2024-01-02T00:00:00Z"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.project_id = "project-123"
        mock_file.filename = "test.pdf"
        mock_file.display_name = "Renamed Test File.pdf"
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"
        mock_file.updated_at = "2024-01-01T00:00:00Z"
        mock_file.folder_id = "folder-123"

        mock_folder = MagicMock()
        mock_folder.id = "folder-123"
        mock_folder.project_id = "project-123"
        mock_folder.parent_id = None
        mock_folder.name = "合同"
        mock_folder.sort_order = 0
        mock_folder.created_at = "2024-01-01T00:00:00Z"
        mock_folder.updated_at = "2024-01-01T00:00:00Z"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)), \
             patch("app.routers.share.consume_share_token"):
            mock_db.query.return_value.filter.return_value.first.return_value = mock_project
            mock_db.query.return_value.filter.return_value.count.return_value = 1
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_file]
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_folder]
            mock_db.query.return_value.join.return_value.all.return_value = []

            result = get_shared_project("token-123", request=_make_request(), db=mock_db)

        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["project"]["name"] == "Test Project"
        assert len(result["data"]["files"]) == 1
        assert result["data"]["files"][0]["display_name"] == "Renamed Test File.pdf"
        assert result["data"]["files"][0]["folder_id"] == "folder-123"
        assert result["data"]["folders"][0]["id"] == "folder-123"
        assert result["data"]["folders"][0]["name"] == "合同"


class TestGetSharedFile:
    """get_shared_file 端点测试"""

    def test_get_shared_file_success(self):
        """测试成功获取分享文件"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.project_id = "project-123"
        mock_file.filename = "test.pdf"
        mock_file.display_name = "Renamed Test File.pdf"
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.return_value = mock_file

            result = get_shared_file("token-123", "file-123", request=_make_request(), db=mock_db)

        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["filename"] == "test.pdf"
        assert result["data"]["display_name"] == "Renamed Test File.pdf"

    def test_get_shared_file_not_found(self):
        """测试文件不存在"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                get_shared_file("token-123", "nonexistent-file", request=_make_request(), db=mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "File not found"


class TestGetSharedVersions:
    """get_shared_versions 端点测试"""

    def test_get_shared_versions_success(self):
        """测试成功获取版本列表"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.filename = "test.pdf"
        mock_file.current_version = 2

        mock_version = MagicMock()
        mock_version.id = "version-123"
        mock_version.version = 1
        mock_version.file_size = 1024
        mock_version.changelog = "Initial version"
        mock_version.created_at = "2024-01-01T00:00:00Z"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                None,
            ]
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_version]

            result = get_shared_versions("token-123", "file-123", request=_make_request(), db=mock_db)

        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["file_id"] == "file-123"
        assert len(result["data"]["versions"]) == 1

    def test_get_shared_versions_file_not_found(self):
        """测试文件不存在"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                get_shared_versions("token-123", "nonexistent-file", request=_make_request(), db=mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestGetSharedDiffs:
    """get_shared_diffs 端点测试"""

    def test_get_shared_diffs_success(self):
        """测试成功获取差异列表"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"

        mock_diff = MagicMock()
        mock_diff.id = "diff-123"
        mock_diff.old_version_id = "version-1"
        mock_diff.new_version_id = "version-2"
        mock_diff.diff_type = "text"
        mock_diff.diff_data = "{}"
        mock_diff.summary = "Changed content"
        mock_diff.created_at = "2024-01-01T00:00:00Z"

        mock_old_version = MagicMock()
        mock_old_version.version = 1
        mock_new_version = MagicMock()
        mock_new_version.version = 2

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_old_version,
                mock_new_version,
            ]
            mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_diff]

            result = get_shared_diffs(
                "token-123",
                "file-123",
                request=_make_request(),
                old_version=None,
                new_version=None,
                db=mock_db,
            )

        assert result["code"] == 0
        assert "data" in result
        assert len(result["data"]["diffs"]) == 1

    def test_get_shared_diffs_with_version_filter(self):
        """测试带版本筛选的差异列表"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = []

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.return_value = mock_file
            mock_db.query.return_value.join.return_value.filter.return_value = mock_query

            result = get_shared_diffs(
                "token-123",
                "file-123",
                request=_make_request(),
                old_version=None,
                new_version=None,
                db=mock_db,
                old_version_id="version-1",
                new_version_id="version-2",
            )

        assert result["code"] == 0
        assert "data" in result


class TestGetSharedDiffsSnapshot:
    """?? diff ??????"""

    def test_get_shared_diffs_prefers_snapshot_version_numbers(self):
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"

        mock_diff = MagicMock()
        mock_diff.id = "diff-123"
        mock_diff.old_version_id = "version-1"
        mock_diff.new_version_id = "version-3"
        mock_diff.diff_type = "text"
        mock_diff.diff_data = (
            '{"metadata": {"old_version_id": "version-1", "new_version_id": "version-3", '
            '"old_version_number": 1, "new_version_number": 3}}'
        )
        mock_diff.summary = "v1->v3"
        mock_diff.created_at = "2024-01-01T00:00:00Z"

        diff_query = MagicMock()
        diff_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_diff]

        version_query = MagicMock()
        version_query.filter.return_value.all.return_value = [
            MagicMock(id="version-1", version=2),
            MagicMock(id="version-3", version=1),
        ]

        def _query_side_effect(model):
            model_name = getattr(model, "__name__", "")
            if model_name == "DiffRecord":
                return diff_query
            if model_name == "FileVersion":
                return version_query
            raise AssertionError(f"unexpected query model: {model_name}")

        mock_db.query.side_effect = _query_side_effect

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)),              patch("app.routers.share.share_scope_file_filter", return_value=mock_file):
            result = get_shared_diffs("token-123", "file-123", request=_make_request(), db=mock_db)

        payload = result["data"]["diffs"]
        assert len(payload) == 1
        assert payload[0]["old_version"] == 1
        assert payload[0]["new_version"] == 3


class TestDownloadSharedVersion:
    """download_shared_version 端点测试"""

    @patch("app.routers.share.os.path.realpath", side_effect=lambda p: p)
    @patch("app.routers.share.os.path.exists")
    @patch("app.routers.share.FileResponse")
    def test_download_shared_version_success(self, mock_file_response, mock_exists, mock_realpath):
        """测试成功下载版本"""
        import os
        from app.config import settings

        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.project_id = "project-123"
        mock_file.filename = "test.pdf"
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"

        mock_version = MagicMock()
        mock_version.id = "version-123"
        mock_version.file_id = "file-123"
        mock_version.storage_path = os.path.join(settings.UPLOAD_DIR, "test.pdf")

        mock_exists.return_value = True
        mock_response = MagicMock()
        mock_response.path = os.path.join(settings.UPLOAD_DIR, "test.pdf")
        mock_response.filename = "test.pdf"
        mock_file_response.return_value = mock_response

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_version,
            ]

            result = download_shared_version("token-123", "file-123", "version-123", request=_make_request(), db=mock_db)

        assert result.path == os.path.join(settings.UPLOAD_DIR, "test.pdf")
        assert result.filename == "test.pdf"

    @patch("app.routers.share.os.path.realpath", side_effect=lambda p: p)
    @patch("app.routers.share.os.path.exists")
    def test_download_shared_version_file_not_on_disk(self, mock_exists, mock_realpath):
        """测试文件不在磁盘上"""
        from app.config import settings

        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.project_id = "project-123"
        mock_file.filename = "test.pdf"
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"

        mock_version = MagicMock()
        mock_version.id = "version-123"
        mock_version.file_id = "file-123"
        mock_version.storage_path = settings.UPLOAD_DIR + "/test.pdf"

        mock_exists.return_value = False

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_version,
            ]

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version("token-123", "file-123", "version-123", request=_make_request(), db=mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "File not found on disk"

    def test_download_shared_version_version_not_found(self):
        """测试版本不存在"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.project_id = "project-123"
        mock_file.filename = "test.pdf"
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                None,
            ]

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version(
                    "token-123",
                    "file-123",
                    "nonexistent-version",
                    request=_make_request(),
                    db=mock_db,
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Version not found"

    def test_download_shared_version_version_wrong_file(self):
        """测试版本不属于该文件"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        mock_file = MagicMock()
        mock_file.id = "file-123"
        mock_file.project_id = "project-123"
        mock_file.filename = "test.pdf"
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"

        mock_version = MagicMock()
        mock_version.id = "version-123"
        mock_version.file_id = "different-file-id"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_version,
            ]

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version("token-123", "file-123", "version-123", request=_make_request(), db=mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Version not found"

    def test_get_shared_file_not_found_in_project(self):
        """测试分享文件不属于该项目（行159附近: 文件不存在或不属于该项目）"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                get_shared_file("token-123", "nonexistent-file", request=_make_request(), db=mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "File not found"

    def test_download_shared_version_file_not_found(self):
        """测试下载时文件不存在（行208附近: 文件不存在）"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        with patch("app.routers.share.resolve_share_token", return_value=_make_resolved(mock_project)):
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version(
                    "token-123",
                    "nonexistent-file",
                    "version-123",
                    request=_make_request(),
                    db=mock_db,
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "File not found"
