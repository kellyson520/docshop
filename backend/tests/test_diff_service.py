"""
差异计算服务模块测试

测试 diff_service.py 中的功能，包括版本不存在、文件记录不存在、
磁盘文件不存在和不支持的文件类型等异常场景。
"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from app.services.diff_service import compute_diff
from app.exceptions import ResourceNotFound, DiffCalculationError


# ===== 辅助函数：创建测试数据链 =====

def _create_project_and_file(db_session, test_user, file_type="pdf", filename="test.pdf"):
    """
    创建完整的项目 -> 文件 数据链

    Args:
        db_session: 数据库会话
        test_user: 测试用户（用于 owner_id）
        file_type: 文件类型
        filename: 文件名

    Returns:
        tuple: (project, doc_file)
    """
    from app.models.project import Project
    from app.models.document_file import DocumentFile

    project = Project(
        name="test_project",
        description="test",
        owner_id=test_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename=filename,
        file_type=file_type,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    return project, doc_file


# ===== test_compute_diff_version_not_found: 测试版本不存在时抛出 ResourceNotFound =====

class TestComputeDiffVersionNotFound:
    """测试版本不存在时的异常处理"""

    def test_compute_diff_version_not_found(self, db_session):
        """
        测试版本不存在时抛出 ResourceNotFound：
        当旧版本或新版本的 ID 在数据库中找不到时，应抛出 ResourceNotFound。
        """
        # 不向数据库添加任何版本记录，查询结果为 None
        with pytest.raises(ResourceNotFound) as exc_info:
            compute_diff(
                old_version_id="nonexistent-old-version-id",
                new_version_id="nonexistent-new-version-id",
                db=db_session,
            )

        # 验证异常信息包含"文件版本不存在"
        assert "文件版本" in str(exc_info.value.message) or "不存在" in str(exc_info.value.message)

    def test_compute_diff_old_version_not_found(self, db_session, test_user):
        """测试仅旧版本不存在时抛出 ResourceNotFound"""
        from app.models.file_version import FileVersion

        # 创建项目和文件
        _, doc_file = _create_project_and_file(db_session, test_user)

        new_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path="/fake/path/new.pdf",
            file_hash="abc123",
            file_size=100,
        )
        db_session.add(new_version)
        db_session.commit()

        with pytest.raises(ResourceNotFound, match="文件版本"):
            compute_diff(
                old_version_id="nonexistent-old-id",
                new_version_id=new_version.id,
                db=db_session,
            )

    def test_compute_diff_new_version_not_found(self, db_session, test_user):
        """测试仅新版本不存在时抛出 ResourceNotFound"""
        from app.models.file_version import FileVersion

        _, doc_file = _create_project_and_file(db_session, test_user)

        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path="/fake/path/old.pdf",
            file_hash="abc123",
            file_size=100,
        )
        db_session.add(old_version)
        db_session.commit()

        with pytest.raises(ResourceNotFound, match="文件版本"):
            compute_diff(
                old_version_id=old_version.id,
                new_version_id="nonexistent-new-id",
                db=db_session,
            )


# ===== test_compute_diff_file_not_found: 测试文件记录不存在时抛出 ResourceNotFound =====

class TestComputeDiffFileNotFound:
    """测试文件记录不存在时的异常处理"""

    def test_compute_diff_file_not_found(self, db_session):
        """
        测试文件记录不存在时抛出 ResourceNotFound：
        当版本记录存在但关联的 DocumentFile 记录不存在时，应抛出 ResourceNotFound。
        """
        from app.models.file_version import FileVersion

        # 创建版本记录，但 file_id 指向不存在的文件记录
        old_version = FileVersion(
            file_id="nonexistent-file-id",
            version=1,
            storage_path="/fake/path/old.pdf",
            file_hash="abc123",
            file_size=100,
        )
        new_version = FileVersion(
            file_id="nonexistent-file-id",
            version=2,
            storage_path="/fake/path/new.pdf",
            file_hash="def456",
            file_size=200,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        with pytest.raises(ResourceNotFound, match="文件记录"):
            compute_diff(
                old_version_id=old_version.id,
                new_version_id=new_version.id,
                db=db_session,
            )


# ===== test_compute_diff_file_not_on_disk: 测试磁盘文件不存在时抛出 DiffCalculationError =====

class TestComputeDiffFileNotOnDisk:
    """测试磁盘文件不存在时的异常处理"""

    def test_compute_diff_file_not_on_disk(self, db_session, test_user, tmp_path):
        """
        测试磁盘文件不存在时抛出 ResourceNotFound：
        当版本记录和文件记录都存在，但 storage_path 指向的磁盘文件不存在时，
        应抛出 ResourceNotFound。
        """
        from app.models.file_version import FileVersion

        # 创建完整的项目 -> 文件 -> 版本 链
        _, doc_file = _create_project_and_file(db_session, test_user)

        # 使用不存在的磁盘路径
        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path="/nonexistent/path/old_v1.pdf",
            file_hash="abc123",
            file_size=100,
        )
        new_version = FileVersion(
            file_id=doc_file.id,
            version=2,
            storage_path="/nonexistent/path/new_v2.pdf",
            file_hash="def456",
            file_size=200,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        # 磁盘文件不存在，应抛出 ResourceNotFound
        with pytest.raises(ResourceNotFound):
            compute_diff(
                old_version_id=old_version.id,
                new_version_id=new_version.id,
                db=db_session,
            )

    def test_compute_diff_new_version_not_on_disk(self, db_session, test_user, tmp_path):
        """
        测试新版本磁盘文件不存在时抛出 ResourceNotFound（行63-67）。
        旧版本文件存在但新版本文件不存在。
        """
        from app.models.file_version import FileVersion

        _, doc_file = _create_project_and_file(db_session, test_user)

        # 旧版本文件存在
        old_file = tmp_path / "old.pdf"
        old_file.write_bytes(b"old content")

        # 新版本文件不存在
        new_version = FileVersion(
            file_id=doc_file.id,
            version=2,
            storage_path="/nonexistent/path/new_v2.pdf",
            file_hash="def456",
            file_size=200,
        )
        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path=str(old_file),
            file_hash="abc123",
            file_size=100,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        # 新版本磁盘文件不存在，应抛出 ResourceNotFound
        with pytest.raises(ResourceNotFound):
            compute_diff(
                old_version_id=old_version.id,
                new_version_id=new_version.id,
                db=db_session,
            )


# ===== test_compute_diff_unsupported_type: 测试不支持的文件类型 =====

class TestComputeDiffUnsupportedType:
    """测试不支持的文件类型时的异常处理"""

    def test_compute_diff_unsupported_type(self, db_session, test_user, tmp_path):
        """
        测试不支持的文件类型：当文件类型不被差异引擎支持时，
        应抛出 DiffCalculationError。
        """
        from app.models.file_version import FileVersion

        # 创建项目和文件，使用不支持的文件类型
        _, doc_file = _create_project_and_file(
            db_session, test_user, file_type="txt", filename="test.txt"
        )

        # 创建版本记录，storage_path 指向真实存在的文件
        old_file = tmp_path / "old.txt"
        old_file.write_text("old content")
        new_file = tmp_path / "new.txt"
        new_file.write_text("new content")

        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path=str(old_file),
            file_hash="abc123",
            file_size=100,
        )
        new_version = FileVersion(
            file_id=doc_file.id,
            version=2,
            storage_path=str(new_file),
            file_hash="def456",
            file_size=200,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        # 不支持的文件类型应抛出 DiffCalculationError
        with pytest.raises(DiffCalculationError, match="不支持的文件类型"):
            compute_diff(
                old_version_id=old_version.id,
                new_version_id=new_version.id,
                db=db_session,
            )


# ===== test_compute_diff_engine_error: 测试引擎计算失败 =====

class TestComputeDiffEngineError:
    """测试差异引擎计算失败时的异常处理"""

    def test_compute_diff_engine_error(self, db_session, test_user, tmp_path):
        """
        测试差异引擎计算失败时抛出 DiffCalculationError（行80-91）。
        使用 mock 让引擎的 compare 方法抛出异常。
        """
        from app.models.file_version import FileVersion

        _, doc_file = _create_project_and_file(
            db_session, test_user, file_type="pdf", filename="test.pdf"
        )

        # 创建版本记录，storage_path 指向真实存在的文件
        old_file = tmp_path / "old.pdf"
        old_file.write_bytes(b"old pdf content")
        new_file = tmp_path / "new.pdf"
        new_file.write_bytes(b"new pdf content")

        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path=str(old_file),
            file_hash="abc123",
            file_size=100,
        )
        new_version = FileVersion(
            file_id=doc_file.id,
            version=2,
            storage_path=str(new_file),
            file_hash="def456",
            file_size=200,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        # Mock 引擎的 compare 方法使其抛出异常
        with patch("app.services.diff_service.get_diff_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.compare.side_effect = RuntimeError("引擎内部错误")
            mock_get_engine.return_value = mock_engine

            with pytest.raises(DiffCalculationError, match="差异计算过程中发生错误"):
                compute_diff(
                    old_version_id=old_version.id,
                    new_version_id=new_version.id,
                    db=db_session,
                )


# ===== test_compute_diff_success_with_audit: 测试成功计算并验证审计日志 =====

class TestComputeDiffSuccess:
    """测试成功计算差异并验证结果"""

    def test_compute_diff_success_with_audit(self, db_session, test_user, tmp_path):
        """
        测试成功计算差异并验证审计日志（行93-125）。
        使用 mock 引擎返回预定义的差异结果。
        """
        from app.models.file_version import FileVersion
        from app.models.diff_record import DiffRecord

        _, doc_file = _create_project_and_file(
            db_session, test_user, file_type="pdf", filename="test.pdf"
        )

        # 创建版本记录，storage_path 指向真实存在的文件
        old_file = tmp_path / "old.pdf"
        old_file.write_bytes(b"old pdf content")
        new_file = tmp_path / "new.pdf"
        new_file.write_bytes(b"new pdf content")

        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path=str(old_file),
            file_hash="abc123",
            file_size=100,
        )
        new_version = FileVersion(
            file_id=doc_file.id,
            version=2,
            storage_path=str(new_file),
            file_hash="def456",
            file_size=200,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        # Mock 引擎返回预定义结果
        mock_result = {
            "type": "pdf_diff",
            "identical": False,
            "page_count": {"old": 1, "new": 1},
            "hashes": {"old": "abc", "new": "def"},
            "page_diffs": [],
            "table_diffs": [],
            "summary": "测试摘要",
            "stats": {"pages_added": 0, "pages_deleted": 0, "pages_modified": 1, "tables_changed": 0},
        }

        with patch("app.services.diff_service.get_diff_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.compare.return_value = mock_result
            mock_get_engine.return_value = mock_engine

            with patch("app.services.diff_service.log_audit") as mock_log_audit:
                result = compute_diff(
                    old_version_id=old_version.id,
                    new_version_id=new_version.id,
                    db=db_session,
                )

        # 验证返回的 DiffRecord
        assert result is not None
        assert isinstance(result, DiffRecord)
        assert result.old_version_id == old_version.id
        assert result.new_version_id == new_version.id
        assert result.diff_type == "visual"  # pdf_diff -> visual
        assert "测试摘要" in result.summary

        # 验证审计日志被调用
        mock_log_audit.assert_called_once()
        call_kwargs = mock_log_audit.call_args[1]
        assert call_kwargs["action"] == "compute_diff"
        assert call_kwargs["result"] == "success"
        assert "old_version" in call_kwargs["details"]
        assert "new_version" in call_kwargs["details"]

    def test_compute_diff_persists_normalized_schema_and_elapsed_ms(self, db_session, test_user, tmp_path):
        """服务层保存 diff_data 前应统一 schema，并补充任务状态/耗时。"""
        from app.models.file_version import FileVersion

        _, doc_file = _create_project_and_file(
            db_session, test_user, file_type="docx", filename="test.docx"
        )

        old_file = tmp_path / "old.docx"
        old_file.write_bytes(b"old docx content")
        new_file = tmp_path / "new.docx"
        new_file.write_bytes(b"new docx content")

        old_version = FileVersion(
            file_id=doc_file.id,
            version=1,
            storage_path=str(old_file),
            file_hash="abc123",
            file_size=100,
        )
        new_version = FileVersion(
            file_id=doc_file.id,
            version=2,
            storage_path=str(new_file),
            file_hash="def456",
            file_size=200,
        )
        db_session.add(old_version)
        db_session.add(new_version)
        db_session.commit()
        db_session.refresh(old_version)
        db_session.refresh(new_version)

        mock_result = {
            "type": "docx_diff",
            "paragraph_diffs": [{"type": "move", "old_index": 11, "new_index": 29}],
            "images": {"added": [{"filename": "new.png"}]},
            "summary": "DOCX changed",
        }

        with patch("app.services.diff_service.get_diff_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_engine.compare.return_value = mock_result
            mock_get_engine.return_value = mock_engine
            with patch("app.services.diff_service.log_audit"):
                result = compute_diff(
                    old_version_id=old_version.id,
                    new_version_id=new_version.id,
                    db=db_session,
                )

        saved = json.loads(result.diff_data)
        assert set(["text", "tables", "images", "metadata", "summary", "stats"]).issubset(saved)
        assert saved["status"] == "completed"
        assert saved["error"] is None
        assert saved["text"] == mock_result["paragraph_diffs"]
        assert saved["images"]["added"][0]["filename"] == "new.png"
        assert saved["metadata"]["file_type"] == "docx"
        assert isinstance(saved["metadata"]["elapsed_ms"], int)
        assert saved["stats"]["text_moves"] == 1
        assert saved["stats"]["image_added"] == 1
        assert saved["stats"]["total_changes"] == 2
