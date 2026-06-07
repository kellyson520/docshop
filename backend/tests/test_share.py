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

from app.routers.share import (
    router,
    _get_project_by_token,
    get_shared_project,
    get_shared_file,
    get_shared_versions,
    get_shared_diffs,
    download_shared_version,
)


class TestGetProjectByToken:
    """_get_project_by_token 辅助函数测试"""

    def test_get_project_success(self):
        """测试成功获取项目"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "Test Project"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        
        result = _get_project_by_token("valid-token", mock_db)
        
        assert result == mock_project
        mock_db.query.assert_called_once()

    def test_get_project_not_found(self):
        """测试项目不存在"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
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
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_file]
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            result = get_shared_project("token-123", mock_db)
        
        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["project"]["name"] == "Test Project"
        assert len(result["data"]["files"]) == 1


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
        mock_file.file_type = "pdf"
        mock_file.current_version = 1
        mock_file.created_at = "2024-01-01T00:00:00Z"
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.return_value = mock_file
            
            result = get_shared_file("token-123", "file-123", mock_db)
        
        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["filename"] == "test.pdf"

    def test_get_shared_file_not_found(self):
        """测试文件不存在"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                get_shared_file("token-123", "nonexistent-file", mock_db)
            
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
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,  # First call for file check
                None,       # Check for diff
            ]
            mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_version]
            
            result = get_shared_versions("token-123", "file-123", mock_db)
        
        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["file_id"] == "file-123"
        assert len(result["data"]["versions"]) == 1

    def test_get_shared_versions_file_not_found(self):
        """测试文件不存在"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                get_shared_versions("token-123", "nonexistent-file", mock_db)
            
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
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,      # File check
                mock_old_version,  # Old version
                mock_new_version,  # New version
            ]
            mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_diff]
            
            result = get_shared_diffs("token-123", "file-123", None, None, mock_db)
        
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
        
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.return_value = mock_file
            mock_db.query.return_value.join.return_value.filter.return_value = mock_query
            
            result = get_shared_diffs("token-123", "file-123", "version-1", "version-2", mock_db)
        
        assert result["code"] == 0
        assert "data" in result


class TestDownloadSharedVersion:
    """download_shared_version 端点测试"""

    @patch("app.routers.share.os.path.exists")
    @patch("app.routers.share.FileResponse")
    def test_download_shared_version_success(self, mock_file_response, mock_exists):
        """测试成功下载版本"""
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
        mock_version.storage_path = "/uploads/test.pdf"

        mock_exists.return_value = True
        mock_response = MagicMock()
        mock_response.path = "/uploads/test.pdf"
        mock_response.filename = "test.pdf"
        mock_file_response.return_value = mock_response

        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_version,
            ]

            result = download_shared_version("token-123", "file-123", "version-123", mock_db)

        assert result.path == "/uploads/test.pdf"
        assert result.filename == "test.pdf"

    @patch("app.routers.share.os.path.exists")
    def test_download_shared_version_file_not_on_disk(self, mock_exists):
        """测试文件不在磁盘上"""
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
        mock_version.storage_path = "/uploads/test.pdf"

        mock_exists.return_value = False

        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_version,
            ]

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version("token-123", "file-123", "version-123", mock_db)

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

        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                None,  # Version not found
            ]

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version("token-123", "file-123", "nonexistent-version", mock_db)

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
        mock_version.file_id = "different-file-id"  # Wrong file

        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_file,
                mock_version,
            ]

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version("token-123", "file-123", "version-123", mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Version not found"

    def test_get_shared_file_not_found_in_project(self):
        """测试分享文件不属于该项目（行159附近: 文件不存在或不属于该项目）"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        # 文件查询返回 None（文件不存在或不属于该项目）
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                get_shared_file("token-123", "nonexistent-file", mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "File not found"

    def test_download_shared_version_file_not_found(self):
        """测试下载时文件不存在（行208附近: 文件不存在）"""
        mock_db = MagicMock()
        mock_project = MagicMock()
        mock_project.id = "project-123"

        # 文件查询返回 None
        with patch("app.routers.share._get_project_by_token", return_value=mock_project):
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                download_shared_version("token-123", "nonexistent-file", "version-123", mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "File not found"
