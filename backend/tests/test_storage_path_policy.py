import tempfile
from pathlib import Path


def test_allowed_storage_roots_include_upload_and_document_store(monkeypatch, tmp_path):
    from app.config import settings
    from app.services import document_store
    import app.services.storage_path_policy as storage_path_policy

    upload_root = tmp_path / "uploads"
    documents_root = tmp_path / "documents"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root), raising=False)
    monkeypatch.setattr(document_store, "ROOT", str(documents_root), raising=False)

    roots = storage_path_policy.allowed_storage_roots()

    assert Path(upload_root.resolve()) in roots
    assert Path(documents_root.resolve()) in roots


def test_is_allowed_storage_path_accepts_document_store_root(monkeypatch, tmp_path):
    from app.services import document_store
    import app.services.storage_path_policy as storage_path_policy

    documents_root = tmp_path / "documents"
    monkeypatch.setattr(document_store, "ROOT", str(documents_root), raising=False)

    stored_file = documents_root / "file-1" / "original" / "preview.pdf"
    stored_file.parent.mkdir(parents=True, exist_ok=True)
    stored_file.write_bytes(b"preview")

    assert storage_path_policy.is_allowed_storage_path(str(stored_file.resolve())) is True


def test_is_allowed_storage_path_accepts_tempdir_during_tests(monkeypatch):
    import app.services.storage_path_policy as storage_path_policy

    temp_file = Path(tempfile.gettempdir()) / "docshop-storage-policy-test.txt"
    temp_file.write_text("temp", encoding="utf-8")
    try:
        assert storage_path_policy.is_allowed_storage_path(str(temp_file.resolve())) is True
    finally:
        temp_file.unlink(missing_ok=True)


def test_is_allowed_storage_path_rejects_outside_roots(monkeypatch, tmp_path):
    from app.config import settings
    from app.services import document_store
    import app.services.storage_path_policy as storage_path_policy

    upload_root = tmp_path / "uploads"
    documents_root = tmp_path / "documents"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root), raising=False)
    monkeypatch.setattr(document_store, "ROOT", str(documents_root), raising=False)
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    outside_file = tmp_path / "outside" / "evil.pdf"
    outside_file.parent.mkdir(parents=True, exist_ok=True)
    outside_file.write_bytes(b"evil")

    assert storage_path_policy.is_allowed_storage_path(str(outside_file.resolve())) is False


def test_allowed_response_roots_include_temp_dir(monkeypatch, tmp_path):
    from app.config import settings
    from app.services import document_store
    import app.services.storage_path_policy as storage_path_policy

    upload_root = tmp_path / "uploads"
    documents_root = tmp_path / "documents"
    temp_root = tmp_path / "temp"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root), raising=False)
    monkeypatch.setattr(settings, "TEMP_DIR", str(temp_root), raising=False)
    monkeypatch.setattr(document_store, "ROOT", str(documents_root), raising=False)
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    roots = storage_path_policy.allowed_response_roots()

    assert Path(upload_root.resolve()) in roots
    assert Path(documents_root.resolve()) in roots
    assert Path(temp_root.resolve()) in roots


def test_is_allowed_response_path_accepts_temp_dir(monkeypatch, tmp_path):
    from app.config import settings
    import app.services.storage_path_policy as storage_path_policy

    temp_root = tmp_path / "temp"
    monkeypatch.setattr(settings, "TEMP_DIR", str(temp_root), raising=False)
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    generated_file = temp_root / "responses" / "preview.html"
    generated_file.parent.mkdir(parents=True, exist_ok=True)
    generated_file.write_text("<html>preview</html>", encoding="utf-8")

    assert storage_path_policy.is_allowed_response_path(str(generated_file.resolve())) is True
