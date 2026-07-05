"""Download and maintain the local MobileModels cache."""

from __future__ import annotations

import csv
import json
import urllib.request
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Callable

from app.services.mobile_model_resolver import normalize_model_code


CSV_FILENAME = "mobile_models.csv"
JSON_FILENAME = "mobile_models.json"
META_FILENAME = "mobile_models.meta.json"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_mobile_models_csv(csv_text: str) -> dict[str, dict[str, str]]:
    """Parse MobileModels CSV into a normalized exact-match mapping."""
    reader = csv.DictReader(StringIO(csv_text or ""))
    required = {"model", "brand_title", "model_name", "ver_name"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError("MobileModels CSV missing required columns")

    mapping: dict[str, dict[str, str]] = {}
    for row in reader:
        model = (row.get("model") or row.get("ver_name") or "").strip()
        brand_title = (row.get("brand_title") or "").strip()
        model_name = (row.get("model_name") or "").strip()
        ver_name = (row.get("ver_name") or model).strip()
        key = normalize_model_code(model)
        if not key or not (brand_title or model_name or ver_name):
            continue
        mapping[key] = {
            "model": model,
            "brand_title": brand_title,
            "model_name": model_name,
            "ver_name": ver_name,
        }

    if not mapping:
        raise ValueError("MobileModels CSV contains no usable rows")
    return mapping


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def write_mobile_model_cache(cache_dir: str | Path, csv_text: str, source_url: str) -> dict:
    """Write raw CSV, normalized JSON and metadata atomically."""
    cache_path = Path(cache_dir)
    mapping = parse_mobile_models_csv(csv_text)

    _atomic_write_text(cache_path / CSV_FILENAME, csv_text)
    _atomic_write_text(
        cache_path / JSON_FILENAME,
        json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=2),
    )
    meta = {
        "updated_at": _utc_now_iso(),
        "source_url": source_url,
        "row_count": len(mapping),
    }
    _atomic_write_text(
        cache_path / META_FILENAME,
        json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=2),
    )
    return {"updated": True, "row_count": len(mapping), "error": None}


def _parse_updated_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_cache_stale(meta_path: str | Path, interval_hours: int = 168) -> bool:
    """Return True when cache metadata is missing, invalid, or too old."""
    try:
        meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        updated_at = _parse_updated_at(str(meta.get("updated_at") or ""))
    except (OSError, ValueError, json.JSONDecodeError):
        return True

    return datetime.now(UTC) - updated_at >= timedelta(hours=interval_hours)


def download_mobile_models_csv(url: str, timeout: int, max_bytes: int) -> str:
    """Download CSV using stdlib urllib with a strict byte cap."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"MobileModels CSV too large: {len(data)} bytes")
    return data.decode("utf-8-sig")


def refresh_mobile_model_cache(
    settings,
    downloader: Callable[[str, int, int], str] | None = None,
) -> dict:
    """Refresh the local cache; keep existing cache untouched on failure."""
    if not getattr(settings, "MOBILE_MODEL_SYNC_ENABLED", True):
        return {"updated": False, "row_count": 0, "error": "sync disabled"}

    source_url = getattr(settings, "MOBILE_MODEL_SOURCE_URL")
    timeout = int(getattr(settings, "MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS", 15))
    max_bytes = int(getattr(settings, "MOBILE_MODEL_MAX_DOWNLOAD_BYTES", 20 * 1024 * 1024))
    cache_dir = getattr(settings, "MOBILE_MODEL_CACHE_DIR")
    downloader = downloader or download_mobile_models_csv

    try:
        csv_text = downloader(source_url, timeout, max_bytes)
        if len(csv_text.encode("utf-8")) > max_bytes:
            raise ValueError("MobileModels CSV too large")
        return write_mobile_model_cache(cache_dir, csv_text, source_url)
    except Exception as exc:  # keep stale cache available
        return {"updated": False, "row_count": 0, "error": str(exc)}
