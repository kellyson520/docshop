"""
卡片路由测试

测试覆盖率目标：100%
- get_cards 卡片列表（所有筛选条件）
- get_card_detail 卡片详情
- update_card_info 更新卡片信息
- upload_card_cover 上传封面
- compare_versions 版本对比
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app.utils.time import utc_now, utc_now_iso
from app.routers.cards import (
    get_cards,
    get_card_detail_endpoint,
    upload_card_cover,
    update_card_info_endpoint,
    compare_multiple_versions,
)


def test_delete_card_does_not_remove_storage_outside_allowed_roots(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.config import settings
    from app.services import document_store, storage_path_policy
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    project = Project(name="card outside delete", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename="card-outside.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    outside_file = tmp_path / "outside" / "card-outside.pdf"
    outside_file.parent.mkdir(parents=True, exist_ok=True)
    outside_file.write_bytes(b"card data")

    db_session.add(
        FileVersion(
            file_id=doc.id,
            version=1,
            sort_order=1.0,
            storage_path=str(outside_file),
            file_hash="card-outside-hash",
            file_size=outside_file.stat().st_size,
            storage_mode="full",
        )
    )
    db_session.commit()

    response = client.delete(f"/api/v1/cards/{doc.id}", headers=auth_headers)

    assert response.status_code == 204
    assert db_session.query(DocumentFile).filter(DocumentFile.id == doc.id).first() is None
    assert outside_file.exists() is True


class TestRankEndpoints:
    """排行榜端点回归测试"""

    def test_download_and_visit_rank_use_access_logs_when_file_counters_are_zero(
        self, client, auth_headers, db_session, test_user
    ):
        from datetime import datetime

        from app.models.access_log import AccessLog
        from app.models.document_file import DocumentFile
        from app.models.file_version import FileVersion
        from app.models.project import Project

        project = Project(name="rank project", description="", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        doc = DocumentFile(
            project_id=project.id,
            filename="rank-test.pdf",
            file_type="pdf",
            current_version=1,
            download_count=0,
            visit_count=0,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        db_session.add(
            FileVersion(
                file_id=doc.id,
                version=1,
                sort_order=1.0,
                storage_path="C:/tmp/rank-test.pdf",
                file_hash="a" * 64,
                file_size=1234,
                storage_mode="full",
            )
        )

        now = utc_now_iso()
        db_session.add_all(
            [
                AccessLog(
                    timestamp=now,
                    ip_address="127.0.0.1",
                    request_method="GET",
                    request_path=f"/api/v1/cards/{doc.id}",
                    response_status=200,
                    response_time_ms=12,
                    action_type="view",
                    target_type="file",
                    target_id=doc.id,
                    session_id="session-view",
                    is_deleted=0,
                ),
                AccessLog(
                    timestamp=now,
                    ip_address="127.0.0.1",
                    request_method="GET",
                    request_path=f"/api/v1/cards/{doc.id}/download",
                    response_status=200,
                    response_time_ms=15,
                    action_type="download",
                    target_type="file",
                    target_id=doc.id,
                    session_id="session-download",
                    is_deleted=0,
                ),
            ]
        )
        db_session.commit()

        download_response = client.get("/api/v1/cards/rank/download?limit=10", headers=auth_headers)
        assert download_response.status_code == 200
        download_payload = download_response.json()
        assert download_payload["code"] == 0
        assert download_payload["data"][0]["id"] == doc.id
        assert download_payload["data"][0]["download_count"] == 1

        visit_response = client.get("/api/v1/cards/rank/visit?limit=10", headers=auth_headers)
        assert visit_response.status_code == 200
        visit_payload = visit_response.json()
        assert visit_payload["code"] == 0
        assert visit_payload["data"][0]["id"] == doc.id
        assert visit_payload["data"][0]["visit_count"] == 1


class TestGetCards:
    """get_cards 端点测试"""

    @patch("app.routers.cards.get_cards_list")
    @patch("app.routers.cards.card_router_logger")
    def test_get_cards_success(self, mock_logger, mock_get_cards_list):
        """测试成功获取卡片列表"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_cards = [
            {
                "id": "card-1",
                "display_name": "Card 1",
                "cover_image": None,
                "version_count": 2,
                "updated_at": "2024-01-01T00:00:00Z",
                "description": "Test card",
                "file_type": "pdf"
            }
        ]
        mock_get_cards_list.return_value = (mock_cards, 1)
        
        result = get_cards(
            project_id=None,
            keyword=None,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_user
        )
        
        assert result.code == 0
        assert result.message == "success"
        assert result.data["total"] == 1
        assert len(result.data["items"]) == 1

    @patch("app.routers.cards.get_cards_list")
    @patch("app.routers.cards.card_router_logger")
    def test_get_cards_with_project_filter(self, mock_logger, mock_get_cards_list):
        """测试带项目筛选的卡片列表"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_get_cards_list.return_value = ([], 0)
        
        result = get_cards(
            project_id="project-123",
            keyword=None,
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_user
        )
        
        mock_get_cards_list.assert_called_once_with(
            db=mock_db,
            project_id="project-123",
            keyword=None,
            page=1,
            page_size=20
        )

    @patch("app.routers.cards.get_cards_list")
    @patch("app.routers.cards.card_router_logger")
    def test_get_cards_with_keyword(self, mock_logger, mock_get_cards_list):
        """测试带关键词搜索的卡片列表"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_get_cards_list.return_value = ([], 0)
        
        result = get_cards(
            project_id=None,
            keyword="test",
            page=1,
            page_size=20,
            db=mock_db,
            current_user=mock_user
        )
        
        mock_get_cards_list.assert_called_once_with(
            db=mock_db,
            project_id=None,
            keyword="test",
            page=1,
            page_size=20
        )

    @patch("app.routers.cards.get_cards_list")
    @patch("app.routers.cards.card_router_logger")
    def test_get_cards_http_exception(self, mock_logger, mock_get_cards_list):
        """测试HTTP异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_get_cards_list.side_effect = HTTPException(status_code=400, detail="Bad request")
        
        with pytest.raises(HTTPException) as exc_info:
            get_cards(
                project_id=None,
                keyword=None,
                page=1,
                page_size=20,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 400

    @patch("app.routers.cards.get_cards_list")
    @patch("app.routers.cards.card_router_logger")
    def test_get_cards_general_exception(self, mock_logger, mock_get_cards_list):
        """测试一般异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_get_cards_list.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            get_cards(
                project_id=None,
                keyword=None,
                page=1,
                page_size=20,
                db=mock_db,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 500
        assert "获取卡片列表失败" in exc_info.value.detail


class TestGetCardDetail:
    """get_card_detail_endpoint 端点测试"""

    @patch("app.routers.cards.get_card_detail")
    @patch("app.routers.cards.card_router_logger")
    def test_get_card_detail_success(self, mock_logger, mock_get_detail):
        """测试成功获取卡片详情"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_detail = {
            "id": "card-123",
            "display_name": "Test Card",
            "filename": "test.pdf",
            "versions": []
        }
        mock_get_detail.return_value = mock_detail
        
        result = get_card_detail_endpoint("card-123", mock_db, mock_user)
        
        assert result.code == 0
        assert result.data == mock_detail

    @patch("app.routers.cards.get_card_detail")
    @patch("app.routers.cards.card_router_logger")
    def test_get_card_detail_http_exception(self, mock_logger, mock_get_detail):
        """测试HTTP异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        
        mock_get_detail.side_effect = HTTPException(status_code=404, detail="Card not found")
        
        with pytest.raises(HTTPException) as exc_info:
            get_card_detail_endpoint("nonexistent", mock_db, mock_user)
        
        assert exc_info.value.status_code == 404

    @patch("app.routers.cards.get_card_detail")
    @patch("app.routers.cards.card_router_logger")
    def test_get_card_detail_general_exception(self, mock_logger, mock_get_detail):
        """测试一般异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        
        mock_get_detail.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            get_card_detail_endpoint("card-123", mock_db, mock_user)
        
        assert exc_info.value.status_code == 500


class TestUploadCardCover:
    """upload_card_cover 端点测试"""

    @patch("app.routers.cards.update_card_cover")
    @patch("app.routers.cards.card_router_logger")
    def test_upload_cover_success(self, mock_logger, mock_update_cover):
        """测试成功上传封面"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "admin"
        mock_user.role = "admin"
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "cover.jpg"
        
        mock_update_cover.return_value = {
            "card_id": "card-123",
            "cover_image": "covers/card-123/cover.jpg",
            "original_filename": "cover.jpg",
            "file_size": 1024
        }
        
        result = upload_card_cover("card-123", mock_file, mock_db, mock_user)
        
        assert result.code == 0
        assert result.message == "封面上传成功"
        assert "cover_image" in result.data

    @patch("app.routers.cards.update_card_cover")
    @patch("app.routers.cards.card_router_logger")
    def test_upload_cover_http_exception(self, mock_logger, mock_update_cover):
        """测试HTTP异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "admin"
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        
        mock_update_cover.side_effect = HTTPException(status_code=400, detail="Invalid image")
        
        with pytest.raises(HTTPException) as exc_info:
            upload_card_cover("card-123", mock_file, mock_db, mock_user)
        
        assert exc_info.value.status_code == 400


class TestUpdateCardInfo:
    """update_card_info_endpoint 端点测试"""

    @patch("app.routers.cards.update_card_info")
    @patch("app.routers.cards.card_router_logger")
    def test_update_info_success(self, mock_logger, mock_update_info):
        """测试成功更新卡片信息"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "admin"
        
        mock_update_info.return_value = {
            "id": "card-123",
            "display_name": "New Name",
            "description": "New description",
            "updated_at": "2024-01-02T00:00:00Z"
        }
        
        result = update_card_info_endpoint(
            "card-123",
            display_name="New Name",
            description="New description",
            db=mock_db,
            current_user=mock_user
        )
        
        assert result.code == 0
        assert result.message == "卡片信息更新成功"
        assert result.data["display_name"] == "New Name"

    @patch("app.routers.cards.update_card_info")
    @patch("app.routers.cards.card_router_logger")
    def test_update_info_partial(self, mock_logger, mock_update_info):
        """测试部分更新卡片信息"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "admin"
        
        mock_update_info.return_value = {
            "id": "card-123",
            "display_name": "New Name",
            "description": None,
            "updated_at": "2024-01-02T00:00:00Z"
        }
        
        result = update_card_info_endpoint(
            "card-123",
            display_name="New Name",
            description=None,
            db=mock_db,
            current_user=mock_user
        )
        
        assert result.code == 0
        mock_update_info.assert_called_once_with(
            db=mock_db,
            card_id="card-123",
            display_name="New Name",
            description=None
        )


class TestCompareMultipleVersions:
    """compare_multiple_versions 端点测试"""

    @patch("app.routers.cards.compare_versions")
    @patch("app.routers.cards.card_router_logger")
    def test_compare_versions_success(self, mock_logger, mock_compare):
        """测试成功对比版本"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_request = MagicMock()
        mock_request.version_ids = ["version-1", "version-2"]
        
        mock_compare.return_value = {
            "card_id": "card-123",
            "compared_versions": [],
            "compare_results": []
        }
        
        result = compare_multiple_versions("card-123", mock_request, mock_db, mock_user)
        
        assert result.code == 0
        assert result.message == "版本对比成功"
        assert "compare_results" in result.data

    @patch("app.routers.cards.compare_versions")
    @patch("app.routers.cards.card_router_logger")
    def test_compare_versions_http_exception(self, mock_logger, mock_compare):
        """测试HTTP异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        
        mock_request = MagicMock()
        mock_request.version_ids = ["version-1", "version-2"]
        
        mock_compare.side_effect = HTTPException(status_code=404, detail="Version not found")
        
        with pytest.raises(HTTPException) as exc_info:
            compare_multiple_versions("card-123", mock_request, mock_db, mock_user)
        
        assert exc_info.value.status_code == 404

    @patch("app.routers.cards.compare_versions")
    @patch("app.routers.cards.card_router_logger")
    def test_compare_versions_general_exception(self, mock_logger, mock_compare):
        """测试一般异常处理"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        
        mock_request = MagicMock()
        mock_request.version_ids = ["version-1", "version-2"]
        
        mock_compare.side_effect = Exception("Comparison failed")
        
        with pytest.raises(HTTPException) as exc_info:
            compare_multiple_versions("card-123", mock_request, mock_db, mock_user)
        
        assert exc_info.value.status_code == 500
        assert "版本对比失败" in exc_info.value.detail

    @patch("app.routers.cards.update_card_cover")
    @patch("app.routers.cards.card_router_logger")
    def test_upload_card_cover_invalid_image(self, mock_logger, mock_update_cover):
        """测试上传无效图片（行206-208: 一般异常处理）"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "admin"
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        
        # 模拟服务层抛出一般异常（非HTTPException）
        mock_update_cover.side_effect = Exception("图片处理失败")
        
        with pytest.raises(HTTPException) as exc_info:
            upload_card_cover("card-123", mock_file, mock_db, mock_user)
        
        assert exc_info.value.status_code == 500
        assert "上传封面失败" in exc_info.value.detail

    @patch("app.routers.cards.compare_versions")
    @patch("app.routers.cards.card_router_logger")
    def test_compare_versions_engine_error(self, mock_logger, mock_compare):
        """测试版本对比引擎错误（行263-267: 一般异常处理）"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        
        mock_request = MagicMock()
        mock_request.version_ids = ["version-1", "version-2"]
        
        # 模拟引擎错误
        mock_compare.side_effect = RuntimeError("Diff engine crashed")
        
        with pytest.raises(HTTPException) as exc_info:
            compare_multiple_versions("card-123", mock_request, mock_db, mock_user)
        
        assert exc_info.value.status_code == 500
        assert "版本对比失败" in exc_info.value.detail
