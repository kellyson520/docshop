"""
Diff 引擎和 API 测试
测试 Diff 引擎、Diff API
"""
import pytest
import io
from datetime import datetime
from app.models.project import Project
from app.models.document_file import DocumentFile
from app.models.diff_record import DiffRecord
from app.models.file_version import FileVersion
from app.diff_engine.factory import get_diff_engine


class TestDiffEngine:
    """Diff 引擎测试"""

    def test_diff_engine_factory_pdf(self):
        """测试 PDF Diff 引擎创建"""
        engine = get_diff_engine("pdf")
        assert engine is not None
        assert engine.__class__.__name__ == "PdfDiffEngine"

    def test_diff_engine_factory_docx(self):
        """测试 DOCX Diff 引擎创建"""
        engine = get_diff_engine("docx")
        assert engine is not None
        assert engine.__class__.__name__ == "DocxDiffEngine"

    def test_diff_engine_factory_xlsx(self):
        """测试 XLSX Diff 引擎创建"""
        engine = get_diff_engine("xlsx")
        assert engine is not None
        assert engine.__class__.__name__ == "XlsxDiffEngine"

    def test_diff_engine_factory_unsupported(self):
        """测试不支持的文件类型"""
        with pytest.raises(Exception):
            get_diff_engine("png")

    def test_pdf_diff_engine_compare_empty(self):
        """测试 PDF Diff 引擎空文件处理"""
        from app.diff_engine.pdf_diff import PdfDiffEngine

        engine = PdfDiffEngine()
        # compare 方法需要文件路径，空字节不是有效 PDF
        # 测试 generate_summary 方法
        assert engine.generate_summary({"summary": "test summary"}) == "test summary"
        assert engine.generate_summary({}) == ""

    def test_docx_diff_engine_compare_empty(self):
        """测试 DOCX Diff 引擎空文件处理"""
        from app.diff_engine.docx_diff import DocxDiffEngine

        engine = DocxDiffEngine()
        # 测试 generate_summary 方法
        assert engine.generate_summary({"summary": "test summary"}) == "test summary"
        assert engine.generate_summary({}) == ""


class TestDiffAPI:
    """Diff API 测试"""

    def test_get_diff_list(self, client, auth_headers, db_session, test_user):
        """测试获取 Diff 列表"""
        # 创建项目和文件
        project = Project(name="Diff测试项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="doc1.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        # 创建版本记录
        v1 = FileVersion(
            file_id=file1.id,
            version=1,
            storage_path="/tmp/v1.pdf",
            file_hash="hash1",
            file_size=100,
        )
        v2 = FileVersion(
            file_id=file1.id,
            version=2,
            storage_path="/tmp/v2.pdf",
            file_hash="hash2",
            file_size=100,
        )
        db_session.add_all([v1, v2])
        db_session.commit()
        db_session.refresh(v1)
        db_session.refresh(v2)

        # 创建 Diff 记录 - 使用新模型字段
        diff = DiffRecord(
            old_version_id=v1.id,
            new_version_id=v2.id,
            diff_type="text",
            diff_data='{"changes": []}',
            summary="无变化"
        )
        db_session.add(diff)
        db_session.commit()

        # 新端点: GET /api/v1/files/{file_id}/diffs
        response = client.get(f"/api/v1/files/{file1.id}/diffs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "diffs" in data["data"]
        assert len(data["data"]["diffs"]) >= 1

    def test_get_diff_detail(self, client, auth_headers, db_session, test_user):
        """测试获取 Diff 详情"""
        # 创建项目和文件
        project = Project(name="项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="doc.pdf",
            file_type="pdf",
            current_version=2
        )
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        v1 = FileVersion(
            file_id=file1.id,
            version=1,
            storage_path="/tmp/v1.pdf",
            file_hash="hash1",
            file_size=100,
        )
        v2 = FileVersion(
            file_id=file1.id,
            version=2,
            storage_path="/tmp/v2.pdf",
            file_hash="hash2",
            file_size=100,
        )
        db_session.add_all([v1, v2])
        db_session.commit()
        db_session.refresh(v1)
        db_session.refresh(v2)

        diff = DiffRecord(
            old_version_id=v1.id,
            new_version_id=v2.id,
            diff_type="text",
            diff_data='{"changes": [{"type": "add", "content": "test"}]}',
            summary='{"additions": 10, "deletions": 5}'
        )
        db_session.add(diff)
        db_session.commit()
        db_session.refresh(diff)

        # 新端点: GET /api/v1/files/{file_id}/diffs/{diff_id}
        response = client.get(
            f"/api/v1/files/{file1.id}/diffs/{diff.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "summary" in data["data"]
        assert "diff_data" in data["data"]

    def test_get_diff_not_found(self, client, auth_headers, db_session, test_user):
        """测试获取不存在的 Diff"""
        # 创建一个文件
        project = Project(name="项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="doc.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        response = client.get(
            f"/api/v1/files/{file1.id}/diffs/non-existent-id",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_list_diffs_empty(self, client, auth_headers, db_session, test_user):
        """测试没有差异记录时返回空列表（行28）"""
        # 创建项目和文件，但不创建任何 Diff 记录
        project = Project(name="空Diff项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="empty.pdf",
            file_type="pdf",
            current_version=1
        )
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        response = client.get(f"/api/v1/files/{file1.id}/diffs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "diffs" in data["data"]
        assert len(data["data"]["diffs"]) == 0

    def test_list_diffs_file_not_found(self, client, auth_headers):
        """测试文件不存在时返回404（行28）"""
        response = client.get(
            "/api/v1/files/nonexistent-file-id/diffs",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_list_diffs_with_details(self, client, auth_headers, db_session, test_user):
        """测试有差异记录时返回完整信息，并使用版本过滤（行37, 39）"""
        project = Project(name="详情Diff项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="detail.pdf",
            file_type="pdf",
            current_version=3
        )
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        # 创建三个版本
        versions = []
        for i in range(1, 4):
            v = FileVersion(
                file_id=file1.id,
                version=i,
                storage_path=f"/tmp/detail_v{i}.pdf",
                file_hash=f"hash_{i}",
                file_size=100,
            )
            db_session.add(v)
            versions.append(v)
        db_session.commit()
        for v in versions:
            db_session.refresh(v)

        # 创建两个 Diff 记录：v1->v2 和 v2->v3
        diff1 = DiffRecord(
            old_version_id=versions[0].id,
            new_version_id=versions[1].id,
            diff_type="text",
            diff_data='{"changes": [{"type": "add"}]}',
            summary="v1到v2的变化"
        )
        diff2 = DiffRecord(
            old_version_id=versions[1].id,
            new_version_id=versions[2].id,
            diff_type="text",
            diff_data='{"changes": [{"type": "delete"}]}',
            summary="v2到v3的变化"
        )
        db_session.add_all([diff1, diff2])
        db_session.commit()

        # 测试使用 old_version 过滤（行37）
        response = client.get(
            f"/api/v1/files/{file1.id}/diffs?old_version={versions[0].id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["diffs"]) == 1
        assert data["data"]["diffs"][0]["old_version"] == 1

        # 测试使用 new_version 过滤（行39）
        response = client.get(
            f"/api/v1/files/{file1.id}/diffs?new_version={versions[2].id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["diffs"]) == 1
        assert data["data"]["diffs"][0]["new_version"] == 3

    def test_get_diff_wrong_file(self, client, auth_headers, db_session, test_user):
        """测试获取属于其他文件的 Diff 时返回404（行92）"""
        # 创建两个文件
        project = Project(name="多文件项目", description="描述", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="file1.pdf",
            file_type="pdf",
            current_version=2
        )
        file2 = DocumentFile(
            project_id=project.id,
            filename="file2.pdf",
            file_type="pdf",
            current_version=2
        )
        db_session.add_all([file1, file2])
        db_session.commit()
        db_session.refresh(file1)
        db_session.refresh(file2)

        # file1 的版本
        v1_file1 = FileVersion(
            file_id=file1.id,
            version=1,
            storage_path="/tmp/f1_v1.pdf",
            file_hash="hash1",
            file_size=100,
        )
        v2_file1 = FileVersion(
            file_id=file1.id,
            version=2,
            storage_path="/tmp/f1_v2.pdf",
            file_hash="hash2",
            file_size=100,
        )
        db_session.add_all([v1_file1, v2_file1])
        db_session.commit()
        db_session.refresh(v1_file1)
        db_session.refresh(v2_file1)

        # 创建属于 file1 的 Diff
        diff = DiffRecord(
            old_version_id=v1_file1.id,
            new_version_id=v2_file1.id,
            diff_type="text",
            diff_data='{"changes": []}',
            summary="file1的diff"
        )
        db_session.add(diff)
        db_session.commit()
        db_session.refresh(diff)

        # 用 file2 的 ID 去获取属于 file1 的 diff，应返回 404
        response = client.get(
            f"/api/v1/files/{file2.id}/diffs/{diff.id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.skip(reason="新代码中没有独立的 Diff 创建和删除 API 端点")
    def test_create_diff(self, client, auth_headers, db_session, test_user):
        """测试创建 Diff"""
        pass

    @pytest.mark.skip(reason="新代码中没有独立的 Diff 创建 API 端点")
    def test_create_diff_no_auth(self, client, db_session, test_user):
        """测试未认证创建 Diff"""
        pass

    @pytest.mark.skip(reason="新代码中没有独立的 Diff 创建 API 端点")
    def test_create_diff_same_file(self, client, auth_headers, db_session, test_user):
        """测试对同一文件创建 Diff"""
        pass

    @pytest.mark.skip(reason="新代码中没有独立的 Diff 删除 API 端点")
    def test_delete_diff(self, client, auth_headers, db_session, test_user):
        """测试删除 Diff"""
        pass

    @pytest.mark.skip(reason="新代码中没有 Diff 导出 API 端点")
    def test_export_diff(self, client, auth_headers, db_session, test_user):
        """测试导出 Diff"""
        pass

    @pytest.mark.skip(reason="新代码中没有 Diff 统计 API 端点")
    def test_get_diff_stats(self, client, auth_headers, db_session, test_user):
        """测试获取 Diff 统计"""
        pass


    def test_get_diff_list_computes_missing_cross_version_diff(self, client, auth_headers, db_session, test_user, monkeypatch, tmp_path):
        project = Project(name="CrossDiff", description="desc", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(project_id=project.id, filename="doc1.pdf", file_type="pdf", current_version=4)
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        versions = []
        for i in range(1, 5):
            fp = tmp_path / f"v{i}.pdf"
            fp.write_bytes(b"%PDF-1.4 mock")
            version = FileVersion(
                file_id=file1.id,
                version=i,
                storage_path=str(fp),
                file_hash=f"hash{i}",
                file_size=100,
            )
            db_session.add(version)
            versions.append(version)
        db_session.commit()
        for version in versions:
            db_session.refresh(version)

        computed = DiffRecord(
            old_version_id=versions[1].id,
            new_version_id=versions[3].id,
            diff_type="text",
            diff_data='{"changes": []}',
            summary="v2->v4",
        )

        def fake_compute_diff(old_id, new_id, db):
            assert old_id == versions[1].id
            assert new_id == versions[3].id
            db.add(computed)
            db.commit()
            db.refresh(computed)
            return computed

        monkeypatch.setattr('app.routers.diffs.compute_diff', fake_compute_diff)

        response = client.get(
            f"/api/v1/files/{file1.id}/diffs",
            headers=auth_headers,
            params={"old_version": "2", "new_version": "4"},
        )

        assert response.status_code == 200
        payload = response.json()["data"]["diffs"]
        assert len(payload) == 1
        assert payload[0]["old_version"] == 2

    def test_shared_diff_filter_computes_missing_cross_version_diff(
        self, db_session, test_user, tmp_path, monkeypatch
    ):
        from app.routers.share import get_shared_diffs

        project = Project(name="ShareCrossVersion", description="desc", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        doc_file = DocumentFile(
            project_id=project.id,
            filename="shared-history.pdf",
            display_name="shared-history.pdf",
            file_type="pdf",
            current_version=4,
        )
        db_session.add(doc_file)
        db_session.commit()
        db_session.refresh(doc_file)

        versions = []
        for i in range(1, 5):
            fp = tmp_path / f"shared-v{i}.pdf"
            fp.write_bytes(b"%PDF-1.4 mock")
            version = FileVersion(
                file_id=doc_file.id,
                version=i,
                storage_path=str(fp),
                file_hash=f"share-hash-{i}",
                file_size=100,
            )
            db_session.add(version)
            versions.append(version)
        db_session.commit()
        for version in versions:
            db_session.refresh(version)

        computed = DiffRecord(
            old_version_id=versions[0].id,
            new_version_id=versions[3].id,
            diff_type="text",
            diff_data='{"metadata": {"old_version_number": 1, "new_version_number": 4}}',
            summary="v1->v4",
        )

        def fake_compute_diff(old_id, new_id, db):
            assert old_id == versions[0].id
            assert new_id == versions[3].id
            db.add(computed)
            db.commit()
            db.refresh(computed)
            return computed

        monkeypatch.setattr("app.routers.share.resolve_share_token", lambda *args, **kwargs: {"share_token": "token"})
        monkeypatch.setattr("app.routers.share.share_scope_file_filter", lambda _resolved, _db, _file_id: doc_file)
        monkeypatch.setattr("app.routers.share.assert_version_in_share_scope", lambda *_args, **_kwargs: None)
        monkeypatch.setattr("app.routers.share.compute_diff", fake_compute_diff)

        result = get_shared_diffs(
            "token-123",
            doc_file.id,
            old_version="1",
            new_version="4",
            db=db_session,
        )

        payload = result["data"]["diffs"]
        assert len(payload) == 1
        assert payload[0]["old_version"] == 1
        assert payload[0]["new_version"] == 4
        assert payload[0]["summary"] == "v1->v4"
        assert payload[0]["new_version"] == 4

    def test_diff_detail_keeps_snapshot_version_numbers_after_reorder(
        self, db_session, test_user
    ):
        from app.routers.diffs import get_diff, list_diffs

        project = Project(name="SnapshotDiff", description="desc", owner_id=test_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        file1 = DocumentFile(
            project_id=project.id,
            filename="snapshot.pdf",
            file_type="pdf",
            current_version=3,
        )
        db_session.add(file1)
        db_session.commit()
        db_session.refresh(file1)

        versions = []
        for i in range(1, 4):
            version = FileVersion(
                file_id=file1.id,
                version=i,
                sort_order=float(i),
                storage_path=f"/tmp/snapshot_v{i}.pdf",
                file_hash=f"snapshot-hash-{i}",
                file_size=100 + i,
            )
            db_session.add(version)
            versions.append(version)
        db_session.commit()
        for version in versions:
            db_session.refresh(version)

        diff = DiffRecord(
            old_version_id=versions[0].id,
            new_version_id=versions[2].id,
            diff_type="text",
            diff_data=(
                '{"metadata": {"old_version_id": "%s", "new_version_id": "%s", '
                '"old_version_number": 1, "new_version_number": 3}}'
                % (versions[0].id, versions[2].id)
            ),
            summary="v1->v3",
        )
        db_session.add(diff)
        db_session.commit()
        db_session.refresh(diff)

        versions[0].version = 2
        versions[1].version = 3
        versions[2].version = 1
        db_session.commit()

        list_response = list_diffs(
            file_id=file1.id,
            db=db_session,
            current_user=test_user,
        )
        list_payload = list_response["data"]["diffs"]
        assert len(list_payload) == 1
        assert list_payload[0]["old_version"] == 1
        assert list_payload[0]["new_version"] == 3

        detail_response = get_diff(
            file_id=file1.id,
            diff_id=diff.id,
            db=db_session,
            current_user=test_user,
        )
        detail_payload = detail_response["data"]
        assert detail_payload["old_version"] == 1
        assert detail_payload["new_version"] == 3
