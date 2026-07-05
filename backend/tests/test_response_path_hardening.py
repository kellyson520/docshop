import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project


def test_stream_native_preview_file_uses_resolved_path(monkeypatch):
    from app.routers import files as files_router

    raw_path = r"C:\preview\link.png"
    resolved_path = r"C:\preview\real.png"

    monkeypatch.setattr(files_router.os.path, "realpath", lambda path: resolved_path)
    monkeypatch.setattr(files_router, "FastAPIFileResponse", lambda **kwargs: kwargs)

    response = files_router._stream_native_preview_file(
        SimpleNamespace(filename="image.png", mime_type="image/png"),
        raw_path,
    )

    assert response["path"] == resolved_path


def test_download_version_uses_resolved_path_in_response(monkeypatch, tmp_path, db_session, test_user):
    from app.config import settings
    from app.routers import files as files_router

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    raw_path = str(upload_root / "link.pdf")
    resolved_path = str(upload_root / "real.pdf")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root), raising=False)
    monkeypatch.setattr(files_router, "_require_file_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(files_router, "_is_allowed_download_path", lambda path: path == resolved_path)
    monkeypatch.setattr(files_router, "FastAPIFileResponse", lambda **kwargs: kwargs)
    monkeypatch.setattr(files_router, "log_audit", lambda **kwargs: None)

    real_realpath = os.path.realpath
    upload_root_real = real_realpath(str(upload_root))

    def fake_realpath(path: str, *args, **kwargs) -> str:
        if path == raw_path:
            return resolved_path
        if path == str(upload_root):
            return upload_root_real
        return real_realpath(path)

    monkeypatch.setattr(files_router.os.path, "realpath", fake_realpath)
    monkeypatch.setattr(files_router.os.path, "exists", lambda path: path in {raw_path, resolved_path})

    project = Project(name="download-version-hardening", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="document.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        storage_path=raw_path,
        file_hash="response-hardening-hash",
        file_size=1,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    response = files_router.download_version(doc_file.id, version.id, db=db_session, current_user=test_user)

    assert response["path"] == resolved_path


def test_download_shared_version_uses_resolved_path_in_response(monkeypatch):
    from app.routers import share as share_router

    raw_path = r"C:\share\link.pdf"
    resolved_path = r"C:\share\real.pdf"

    project = SimpleNamespace(id="project-1")
    doc_file = SimpleNamespace(
        id="file-1",
        project_id="project-1",
        filename="shared.pdf",
        file_type="pdf",
        current_version=1,
    )
    version = SimpleNamespace(
        id="version-1",
        file_id="file-1",
        version=1,
        storage_path=raw_path,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = version

    monkeypatch.setattr(
        share_router,
        "_resolve_share_context",
        lambda *args, **kwargs: {"share_token": object(), "project": project},
    )
    monkeypatch.setattr(share_router, "_require_share_password_grant", lambda *args, **kwargs: None)
    monkeypatch.setattr(share_router, "share_scope_file_filter", lambda *args, **kwargs: doc_file)
    monkeypatch.setattr(share_router, "_require_shared_file_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(share_router, "assert_version_in_share_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(share_router, "consume_share_token", lambda *args, **kwargs: None)
    monkeypatch.setattr(share_router, "_is_allowed_storage_path", lambda path: path == resolved_path)
    monkeypatch.setattr(share_router, "FastAPIFileResponse", lambda **kwargs: kwargs)

    real_realpath = os.path.realpath

    def fake_realpath(path: str) -> str:
        if path == raw_path:
            return resolved_path
        return real_realpath(path)

    monkeypatch.setattr(share_router.os.path, "realpath", fake_realpath)
    monkeypatch.setattr(share_router.os.path, "exists", lambda path: path in {raw_path, resolved_path})

    response = share_router.download_shared_version(
        "share-token",
        "file-1",
        "version-1",
        db=db,
        share_access_grant=None,
        current_user=None,
    )

    assert response["path"] == resolved_path
    assert db.commit.call_count == 1
