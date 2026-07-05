from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest


def test_share_token_expiry_respects_timezone_offsets(monkeypatch):
    """expires_at 带 +08:00 等时区时，应先归一到 UTC 再比较。"""
    from app.services import share_token_service

    monkeypatch.setattr(share_token_service, "utc_now", lambda: datetime(2026, 1, 1, 0, 30, 0))

    assert share_token_service._expired("2026-01-01T08:00:00+08:00") is True
    assert share_token_service._expired("2026-01-01T09:00:00+08:00") is False


def test_exam_reminder_offset_validation_messages_are_readable():
    from app.exceptions import ValidationError
    from app.routers.exams import normalize_reminder_offsets

    with pytest.raises(ValidationError) as invalid_type:
        normalize_reminder_offsets(["abc"])
    assert "提醒时间必须是整数分钟" in str(invalid_type.value)
    assert "?" not in str(invalid_type.value)

    with pytest.raises(ValidationError) as out_of_range:
        normalize_reminder_offsets([-1])
    assert "提醒时间范围必须在 0 到 525600 分钟之间" in str(out_of_range.value)
    assert "?" not in str(out_of_range.value)


def test_preview_storage_path_prefers_configured_upload_dir(tmp_path, monkeypatch):
    from app.config import settings
    from app.services.preview_queue import resolve_storage_path

    stale_root = tmp_path / "old-root"
    configured_root = tmp_path / "configured-root"
    stale_file = stale_root / "data" / "uploads" / "same.pdf"
    configured_file = configured_root / "data" / "uploads" / "same.pdf"
    stale_file.parent.mkdir(parents=True)
    configured_file.parent.mkdir(parents=True)
    stale_file.write_text("stale", encoding="utf-8")
    configured_file.write_text("current", encoding="utf-8")

    monkeypatch.chdir(stale_root)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(configured_root / "data" / "uploads"))

    assert Path(resolve_storage_path("data/uploads/same.pdf")).resolve() == configured_file.resolve()


def test_docx_diff_uses_unicode_normalization_and_streaming_large_hash():
    source = Path("app/diff_engine/docx_diff.py").read_text(encoding="utf-8")

    assert "unicodedata.normalize" in source
    assert "def _hash_paragraphs" in source
    assert "join(old_paragraphs)" not in source
    assert "join(new_paragraphs)" not in source


def test_docx_diff_rejects_oversized_embedded_images_before_copy():
    source = Path("app/diff_engine/docx_diff.py").read_text(encoding="utf-8")

    assert "MAX_IMAGE_PIXELS" in source
    assert "max_image_blob_bytes" in source
    assert "if len(blob) > self.max_image_blob_bytes" in source


def test_xlsx_diff_limits_rows_at_read_time(monkeypatch):
    from app.diff_engine.xlsx_diff import XlsxDiffEngine

    calls = []

    def fake_read_excel(path, **kwargs):
        calls.append(kwargs)
        return pd.DataFrame({"A": ["x"]})

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    engine = XlsxDiffEngine()
    engine.max_rows = 10
    engine._compare_sheet(0, "Sheet1", "old.xlsx", None)

    assert calls
    assert calls[0]["nrows"] == 11


def test_unknown_ole_container_is_rejected(tmp_path):
    from app.validators.file_validator import FileValidationError, _detect_ole_content_type

    ole_file = tmp_path / "unknown.doc"
    ole_file.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 4096)

    with pytest.raises(FileValidationError):
        _detect_ole_content_type(ole_file)


def test_announcements_sanitize_title_and_content_before_persisting():
    source = Path("app/routers/announcements.py").read_text(encoding="utf-8")

    assert "sanitize_user_text" in source
    assert "title=sanitize_user_text(body.title)" in source
    assert "content=sanitize_user_text(body.content)" in source
    assert "sanitize_user_text(value)" in source
