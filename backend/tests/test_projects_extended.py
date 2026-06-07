"""
项目路由扩展测试

测试覆盖率目标：100%
- update_project 更新项目
- delete_project 删除项目
- regenerate_share_token 重新生成分享令牌
- 各种筛选和排序组合
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status


class TestProjectRouterExtended:
    """项目路由扩展测试 - 使用Mock测试路由行为"""

    @patch("app.routers.projects._get_project_or_404")
    @patch("app.routers.projects._check_project_ownership")
    @patch("app.routers.projects._get_project_file_count")
    @patch("app.routers.projects._project_to_response")
    def test_update_project_success(self, mock_to_response, mock_file_count, mock_check_owner, mock_get_project):
        """测试成功更新项目"""
        from app.routers.projects import update_project, ProjectUpdateEnhanced

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "admin"
        mock_user.role = "admin"

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Old Name"
        mock_project.description = "Old Description"
        mock_project.is_public = 0
        mock_project.share_token = "old-token"
        mock_project.owner_id = "user-123"

        mock_get_project.return_value = mock_project
        mock_check_owner.return_value = None
        mock_file_count.return_value = 5
        mock_to_response.return_value = {
            "id": "project-123",
            "name": "New Name",
            "description": "New Description",
            "is_public": 1,
            "file_count": 5
        }

        # Mock the query for checking name conflict - return None to indicate no conflict
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Create project_data
        project_data = ProjectUpdateEnhanced(
            name="New Name",
            description="New Description",
            is_public=1
        )

        result = update_project(
            request=MagicMock(),
            project_id="project-123",
            project_data=project_data,
            db=mock_db,
            current_user=mock_user
        )

        assert result["code"] == 0
        assert "success" in result["message"].lower() or "更新" in result["message"]
        mock_db.commit.assert_called_once()

    @patch("app.routers.projects._get_project_or_404")
    @patch("app.routers.projects._check_project_ownership")
    @patch("app.routers.projects._get_project_file_count")
    @patch("app.routers.projects._project_to_response")
    def test_update_project_partial(self, mock_to_response, mock_file_count, mock_check_owner, mock_get_project):
        """测试部分更新项目"""
        from app.routers.projects import update_project, ProjectUpdateEnhanced

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "admin"

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Name"
        mock_project.description = "Description"
        mock_project.is_public = 0
        mock_project.share_token = "token"
        mock_project.owner_id = "user-123"

        mock_get_project.return_value = mock_project
        mock_check_owner.return_value = None
        mock_file_count.return_value = 3
        mock_to_response.return_value = {
            "id": "project-123",
            "name": "Name",
            "description": "New Description",
            "is_public": 0,
            "file_count": 3
        }

        project_data = ProjectUpdateEnhanced(
            name=None,
            description="New Description",
            is_public=None
        )

        result = update_project(
            request=MagicMock(),
            project_id="project-123",
            project_data=project_data,
            db=mock_db,
            current_user=mock_user
        )

        assert result["code"] == 0
        assert result["data"]["name"] == "Name"  # 未改变
        assert result["data"]["description"] == "New Description"  # 已改变
        assert result["data"]["is_public"] == 0  # 未改变

    @patch("app.routers.projects._get_project_or_404")
    def test_update_project_not_found(self, mock_get_project):
        """测试项目不存在"""
        from app.routers.projects import update_project, ProjectUpdateEnhanced
        from app.exceptions import ResourceNotFound

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "admin"

        mock_get_project.side_effect = ResourceNotFound(resource="项目", resource_id="nonexistent-project")

        project_data = ProjectUpdateEnhanced(name="New Name")

        with pytest.raises(ResourceNotFound) as exc_info:
            update_project(
                request=MagicMock(),
                project_id="nonexistent-project",
                project_data=project_data,
                db=mock_db,
                current_user=mock_user
            )

        assert "项目" in str(exc_info.value.message)

    @patch("app.routers.projects._get_project_or_404")
    @patch("app.routers.projects._check_project_ownership")
    def test_update_project_no_permission(self, mock_check_owner, mock_get_project):
        """测试无权限更新项目"""
        from app.routers.projects import update_project, ProjectUpdateEnhanced
        from app.exceptions import PermissionDenied

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "user"
        mock_user.role = "user"

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.owner_id = "other-user"

        mock_get_project.return_value = mock_project
        mock_check_owner.side_effect = PermissionDenied(message="您没有权限操作此项目")

        project_data = ProjectUpdateEnhanced(name="New Name")

        with pytest.raises(PermissionDenied) as exc_info:
            update_project(
                request=MagicMock(),
                project_id="project-123",
                project_data=project_data,
                db=mock_db,
                current_user=mock_user
            )

        assert "权限" in str(exc_info.value.message)

    @patch("app.routers.projects._get_project_or_404")
    @patch("app.routers.projects._check_project_ownership")
    def test_delete_project_success(self, mock_check_owner, mock_get_project):
        """测试成功删除项目"""
        from app.routers.projects import delete_project

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "admin"
        mock_user.role = "admin"

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        mock_project.owner_id = "user-123"

        mock_get_project.return_value = mock_project
        mock_check_owner.return_value = None

        result = delete_project(
            request=MagicMock(),
            project_id="project-123",
            db=mock_db,
            current_user=mock_user
        )

        assert result is None  # 204 No Content
        mock_db.delete.assert_called_once_with(mock_project)
        mock_db.commit.assert_called_once()

    @patch("app.routers.projects._get_project_or_404")
    def test_delete_project_not_found(self, mock_get_project):
        """测试项目不存在"""
        from app.routers.projects import delete_project
        from app.exceptions import ResourceNotFound

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "admin"

        mock_get_project.side_effect = ResourceNotFound(resource="项目", resource_id="nonexistent-project")

        with pytest.raises(ResourceNotFound) as exc_info:
            delete_project(
                request=MagicMock(),
                project_id="nonexistent-project",
                db=mock_db,
                current_user=mock_user
            )

        assert "项目" in str(exc_info.value.message)

    @patch("app.routers.projects._get_project_or_404")
    @patch("app.routers.projects._check_project_ownership")
    def test_delete_project_no_permission(self, mock_check_owner, mock_get_project):
        """测试无权限删除项目"""
        from app.routers.projects import delete_project
        from app.exceptions import PermissionDenied

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "user"
        mock_user.role = "user"

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.owner_id = "other-user"

        mock_get_project.return_value = mock_project
        mock_check_owner.side_effect = PermissionDenied(message="您没有权限操作此项目")

        with pytest.raises(PermissionDenied) as exc_info:
            delete_project(
                request=MagicMock(),
                project_id="project-123",
                db=mock_db,
                current_user=mock_user
            )

        assert "权限" in str(exc_info.value.message)


class TestRegenerateToken:
    """regenerate_token 端点测试"""

    @patch("app.routers.projects._get_project_or_404")
    @patch("app.routers.projects._check_project_ownership")
    def test_regenerate_token_success(self, mock_check_owner, mock_get_project):
        """测试成功重新生成分享令牌"""
        from app.routers.projects import regenerate_token

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        mock_project.share_token = "old-token"
        mock_project.owner_id = "user-123"

        mock_get_project.return_value = mock_project
        mock_check_owner.return_value = None

        result = regenerate_token(
            request=MagicMock(),
            project_id="project-123",
            db=mock_db,
            current_user=mock_user
        )

        assert result["code"] == 0
        assert "share_token" in result["data"]
        mock_db.commit.assert_called_once()

    @patch("app.routers.projects._get_project_or_404")
    def test_regenerate_token_not_found(self, mock_get_project):
        """测试项目不存在"""
        from app.routers.projects import regenerate_token
        from app.exceptions import ResourceNotFound

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"

        mock_get_project.side_effect = ResourceNotFound(resource="项目", resource_id="nonexistent-project")

        with pytest.raises(ResourceNotFound):
            regenerate_token(
                request=MagicMock(),
                project_id="nonexistent-project",
                db=mock_db,
                current_user=mock_user
            )
