import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.config import Settings
from app.services.mobile_model_sync import (
    is_cache_stale,
    parse_mobile_models_csv,
    refresh_mobile_model_cache,
    write_mobile_model_cache,
)


CSV_TEXT = """model,brand_title,model_name,ver_name
ANA-AL00,Huawei,P40,ANA-AL00
SM-G9980,Samsung,Galaxy S21 Ultra,SM-G9980
"""


def make_settings(cache_dir, **overrides):
    values = {
        "MOBILE_MODEL_SYNC_ENABLED": True,
        "MOBILE_MODEL_SYNC_INTERVAL_HOURS": 168,
        "MOBILE_MODEL_SOURCE_URL": "https://example.test/models.csv",
        "MOBILE_MODEL_CACHE_DIR": str(cache_dir),
        "MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS": 3,
        "MOBILE_MODEL_MAX_DOWNLOAD_BYTES": 1024 * 1024,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_settings_include_mobile_model_cache_defaults():
    settings = Settings(_env_file=None)

    assert settings.MOBILE_MODEL_SYNC_ENABLED is True
    assert settings.MOBILE_MODEL_SYNC_INTERVAL_HOURS == 168
    assert settings.MOBILE_MODEL_SOURCE_URL.endswith("/models.csv")
    assert settings.MOBILE_MODEL_CACHE_DIR == "./data/cache"
    assert settings.MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS == 15


def test_parse_mobile_models_csv_normalizes_required_rows():
    mapping = parse_mobile_models_csv(CSV_TEXT)

    assert mapping["ANA-AL00"] == {
        "model": "ANA-AL00",
        "brand_title": "Huawei",
        "model_name": "P40",
        "ver_name": "ANA-AL00",
    }
    assert mapping["SM-G9980"]["model_name"] == "Galaxy S21 Ultra"


def test_write_mobile_model_cache_writes_csv_json_and_meta(tmp_path):
    result = write_mobile_model_cache(tmp_path, CSV_TEXT, "https://example.test/models.csv")

    assert result["updated"] is True
    assert result["row_count"] == 2
    assert (tmp_path / "mobile_models.csv").read_text(encoding="utf-8") == CSV_TEXT
    data = json.loads((tmp_path / "mobile_models.json").read_text(encoding="utf-8"))
    meta = json.loads((tmp_path / "mobile_models.meta.json").read_text(encoding="utf-8"))
    assert data["ANA-AL00"]["model_name"] == "P40"
    assert meta["source_url"] == "https://example.test/models.csv"
    assert meta["row_count"] == 2


def test_refresh_keeps_existing_cache_when_download_fails(tmp_path):
    write_mobile_model_cache(tmp_path, CSV_TEXT, "old-url")
    before = (tmp_path / "mobile_models.json").read_text(encoding="utf-8")

    def failing_downloader(url, timeout, max_bytes):
        raise TimeoutError("network timeout")

    result = refresh_mobile_model_cache(make_settings(tmp_path), downloader=failing_downloader)

    assert result["updated"] is False
    assert "network timeout" in result["error"]
    assert (tmp_path / "mobile_models.json").read_text(encoding="utf-8") == before


def test_refresh_rejects_oversized_download_without_overwriting_cache(tmp_path):
    write_mobile_model_cache(tmp_path, CSV_TEXT, "old-url")
    before = (tmp_path / "mobile_models.csv").read_text(encoding="utf-8")

    def oversized_downloader(url, timeout, max_bytes):
        return "x" * (max_bytes + 1)

    result = refresh_mobile_model_cache(
        make_settings(tmp_path, MOBILE_MODEL_MAX_DOWNLOAD_BYTES=12),
        downloader=oversized_downloader,
    )

    assert result["updated"] is False
    assert "too large" in result["error"].lower()
    assert (tmp_path / "mobile_models.csv").read_text(encoding="utf-8") == before


def test_is_cache_stale_for_missing_old_and_fresh_meta(tmp_path):
    meta_path = tmp_path / "mobile_models.meta.json"
    assert is_cache_stale(meta_path, interval_hours=168) is True

    fresh = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    meta_path.write_text(json.dumps({"updated_at": fresh}), encoding="utf-8")
    assert is_cache_stale(meta_path, interval_hours=168) is False

    old = (datetime.now(UTC) - timedelta(hours=169)).isoformat().replace("+00:00", "Z")
    meta_path.write_text(json.dumps({"updated_at": old}), encoding="utf-8")
    assert is_cache_stale(meta_path, interval_hours=168) is True
