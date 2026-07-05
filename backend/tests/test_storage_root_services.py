import importlib
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.config import settings


def test_document_store_root_uses_documents_dir(monkeypatch, tmp_path):
    from app.services import document_store

    storage_root = tmp_path / "canonical-data"
    upload_dir = tmp_path / "custom-upload-root" / "uploads"

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root), raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir), raising=False)

    importlib.reload(document_store)
    try:
        assert Path(document_store.ROOT) == settings.documents_dir
    finally:
        importlib.reload(document_store)


def test_git_store_uses_objects_dir_from_storage_root(monkeypatch, tmp_path):
    from app.services.git_store import GitStore

    storage_root = tmp_path / "canonical-data"
    upload_dir = tmp_path / "custom-upload-root" / "uploads"

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root), raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir), raising=False)

    store = GitStore()

    assert store.objects_dir == settings.objects_dir


def test_mobile_model_resolver_default_cache_path_uses_settings_cache_dir(monkeypatch, tmp_path):
    from app.services import mobile_model_resolver

    cache_dir = tmp_path / "canonical-data" / "cache"
    monkeypatch.setattr(settings, "MOBILE_MODEL_CACHE_DIR", str(cache_dir), raising=False)

    importlib.reload(mobile_model_resolver)
    try:
        resolver = mobile_model_resolver.MobileModelResolver()
        assert resolver.cache_path == Path(settings.MOBILE_MODEL_CACHE_DIR) / "mobile_models.json"
    finally:
        importlib.reload(mobile_model_resolver)


def test_security_settings_env_path_uses_backend_env_file(monkeypatch, tmp_path):
    from app import config as config_module
    from app.services import security_settings

    project_root = tmp_path / "docshop"
    backend_root = project_root / "backend"
    fake_config = backend_root / "app" / "config.py"
    fake_config.parent.mkdir(parents=True, exist_ok=True)
    fake_config.write_text("# stub", encoding="utf-8")

    monkeypatch.setattr(config_module, "__file__", str(fake_config))
    monkeypatch.delenv("DOCSHOP_ENV_FILE", raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "wrong" / "uploads"), raising=False)

    assert security_settings._env_path() == (backend_root / ".env").resolve()


def test_file_service_safe_delete_uses_explicit_trash_dir(monkeypatch, tmp_path):
    from app.services.file_service import delete_file

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    explicit_trash = tmp_path / "canonical-data" / "trash"

    test_file = upload_dir / "to-delete.txt"
    test_file.write_text("delete me", encoding="utf-8")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir), raising=False)
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path / "canonical-data"), raising=False)

    result = delete_file(test_file, safe=True)

    assert result is True
    assert explicit_trash.exists()
    assert len(list(explicit_trash.glob("*"))) == 1
    assert not (upload_dir.parent / "trash").exists()


def test_card_service_cover_paths_use_storage_root(monkeypatch, tmp_path):
    from app.services.card_service import normalize_cover_image_path, cover_image_to_disk_path

    storage_root = tmp_path / "canonical-data"
    upload_dir = tmp_path / "custom-upload-root" / "uploads"
    cover_path = storage_root / "covers" / "doc-1" / "cover.jpg"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.write_bytes(b"jpg")

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root), raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir), raising=False)

    normalized = normalize_cover_image_path(str(cover_path))

    assert normalized == "/api/v1/covers/doc-1/cover.jpg"
    assert cover_image_to_disk_path(normalized) == cover_path.resolve()


def test_update_card_cover_does_not_delete_sibling_cover_with_prefix_match(monkeypatch, tmp_path):
    from app.services.card_service import update_card_cover

    storage_root = tmp_path / "canonical-data"
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root), raising=False)

    current_card_id = "card-1"
    sibling_card_id = "card-11"
    sibling_cover = storage_root / "covers" / sibling_card_id / "cover.jpg"
    sibling_cover.parent.mkdir(parents=True, exist_ok=True)
    sibling_cover.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF-sibling")

    doc_file = SimpleNamespace(
        id=current_card_id,
        cover_image=f"/api/v1/covers/{sibling_card_id}/cover.jpg",
        updated_at=None,
    )
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = doc_file
    mock_db = MagicMock()
    mock_db.query.return_value = mock_query

    upload = SimpleNamespace(
        filename="new.jpg",
        file=io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF-new-cover"),
        content_type="image/jpeg",
    )

    result = update_card_cover(mock_db, current_card_id, upload)

    assert result["cover_image"].startswith(f"/api/v1/covers/{current_card_id}/")
    assert sibling_cover.exists() is True


def test_clear_preview_cache_rejects_file_id_path_traversal(monkeypatch, tmp_path):
    from app.services import document_store

    documents_root = tmp_path / "canonical-data" / "documents"
    outside_pdf = tmp_path / "canonical-data" / "outside-doc" / "pdf" / "document.pdf"
    outside_image = tmp_path / "canonical-data" / "outside-doc" / "images" / "page_0001.jpg"
    outside_pdf.parent.mkdir(parents=True, exist_ok=True)
    outside_image.parent.mkdir(parents=True, exist_ok=True)
    outside_pdf.write_bytes(b"pdf")
    outside_image.write_bytes(b"image")

    monkeypatch.setattr(document_store, "ROOT", str(documents_root))

    with pytest.raises(ValueError):
        document_store.clear_preview_cache("../outside-doc")

    assert outside_pdf.exists() is True
    assert outside_image.exists() is True


def test_generate_images_rejects_file_id_path_traversal(monkeypatch, tmp_path):
    from app.services import document_store

    documents_root = tmp_path / "canonical-data" / "documents"
    outside_image = tmp_path / "canonical-data" / "outside-doc" / "images" / "page_0001.jpg"
    outside_image.parent.mkdir(parents=True, exist_ok=True)
    outside_image.write_bytes(b"image")
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(document_store, "ROOT", str(documents_root))

    with pytest.raises(ValueError):
        document_store.generate_images("../outside-doc", str(pdf_path), page_count=0, pdf_hash="hash")

    assert outside_image.exists() is True


def test_convert_to_pdf_cache_cleanup_does_not_delete_sibling_temp_dir_with_prefix_match(monkeypatch, tmp_path):
    from app.services import conversion_service

    source = tmp_path / "source.docx"
    source.write_bytes(b"fake-docx")

    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    outside_parent = tmp_path / "temp-sibling" / "converted-parent"
    outside_parent.mkdir(parents=True, exist_ok=True)
    outside_pdf = outside_parent / "converted.pdf"
    outside_pdf.write_bytes(b"%PDF-1.4\n")

    cached_path = tmp_path / "cache" / "cached.pdf"

    monkeypatch.setattr(conversion_service.tempfile, "gettempdir", lambda: str(temp_root))
    monkeypatch.setattr(conversion_service, "_ensure_temp_dir", lambda: str(temp_root))
    monkeypatch.setattr(conversion_service, "_ensure_cache_dir", lambda: None)
    monkeypatch.setattr(conversion_service, "_read_cache", lambda *args, **kwargs: None)
    monkeypatch.setattr(conversion_service, "_detect_engine", lambda: "libreoffice")
    monkeypatch.setattr(
        conversion_service,
        "_convert_via_libreoffice",
        lambda *args, **kwargs: str(outside_pdf),
    )
    monkeypatch.setattr(conversion_service, "_write_cache", lambda *args, **kwargs: str(cached_path))

    result = conversion_service.convert_to_pdf(str(source), "docx", source.name)

    assert result[0] == str(cached_path)
    assert outside_parent.exists() is True
    assert outside_pdf.exists() is True


def test_ensure_pdf_cleanup_does_not_delete_sibling_temp_dir_with_prefix_match(monkeypatch, tmp_path):
    from app.services import conversion_service, document_store

    source = tmp_path / "source.docx"
    source.write_bytes(b"fake-docx")

    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    outside_parent = tmp_path / "temp-sibling" / "word-output"
    outside_parent.mkdir(parents=True, exist_ok=True)
    outside_pdf = outside_parent / "converted.pdf"
    outside_pdf.write_bytes(b"%PDF-1.4\n")

    stored_pdf = tmp_path / "documents" / "stored.pdf"
    meta: dict[str, object] = {}

    monkeypatch.setattr(conversion_service.tempfile, "gettempdir", lambda: str(temp_root))
    monkeypatch.setattr(document_store, "get_cached_pdf", lambda *args, **kwargs: None)
    monkeypatch.setattr(document_store, "store_pdf", lambda *args, **kwargs: str(stored_pdf))
    monkeypatch.setattr(conversion_service, "_read_meta_internal", lambda file_id: dict(meta))
    monkeypatch.setattr(conversion_service, "_write_meta_internal", lambda file_id, data: meta.update(data))
    monkeypatch.setattr(conversion_service, "_convert_via_docx2pdf", lambda *args, **kwargs: str(outside_pdf))

    result = conversion_service._ensure_pdf("file-1", str(source), "hash-1")

    assert result == str(stored_pdf)
    assert outside_parent.exists() is True
    assert outside_pdf.exists() is True
