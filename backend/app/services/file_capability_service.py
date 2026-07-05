from __future__ import annotations

import mimetypes
from pathlib import Path


FILE_PROFILE_REGISTRY: dict[str, dict[str, str]] = {
    "jpg": {"category": "image", "preview_mode": "native"},
    "jpeg": {"category": "image", "preview_mode": "native"},
    "png": {"category": "image", "preview_mode": "native"},
    "gif": {"category": "image", "preview_mode": "native"},
    "webp": {"category": "image", "preview_mode": "native"},
    "pdf": {"category": "pdf", "preview_mode": "native"},
    "html": {"category": "html", "preview_mode": "native"},
    "mp4": {"category": "video", "preview_mode": "native"},
    "webm": {"category": "video", "preview_mode": "native"},
    "mp3": {"category": "audio", "preview_mode": "native"},
    "wav": {"category": "audio", "preview_mode": "native"},
    "txt": {"category": "text", "preview_mode": "native"},
    "md": {"category": "text", "preview_mode": "native"},
    "doc": {"category": "office", "preview_mode": "converted"},
    "docx": {"category": "office", "preview_mode": "converted"},
    "ppt": {"category": "office", "preview_mode": "converted"},
    "pptx": {"category": "office", "preview_mode": "converted"},
    "xls": {"category": "office", "preview_mode": "converted"},
    "xlsx": {"category": "office", "preview_mode": "converted"},
    "zip": {"category": "archive", "preview_mode": "structure"},
    "tar": {"category": "archive", "preview_mode": "structure"},
    "tgz": {"category": "archive", "preview_mode": "structure"},
    "tar.gz": {"category": "archive", "preview_mode": "structure"},
    "tbz2": {"category": "archive", "preview_mode": "structure"},
    "tar.bz2": {"category": "archive", "preview_mode": "structure"},
    "txz": {"category": "archive", "preview_mode": "structure"},
    "tar.xz": {"category": "archive", "preview_mode": "structure"},
    "7z": {"category": "archive", "preview_mode": "structure"},
    "rar": {"category": "archive", "preview_mode": "structure"},
}
COMPOUND_EXTENSIONS = ("tar.gz", "tar.bz2", "tar.xz")
PREVIEWABLE_CATEGORIES = {"office", "pdf", "archive", "video", "image"}


def resolve_original_download_format(filename: str, file_type: str | None = None) -> str:
    ext = (file_type or _detect_extension(filename)).strip().lower().lstrip(".")
    return ext


def resolve_download_formats(filename: str, file_type: str | None = None) -> list[str]:
    ext = resolve_original_download_format(filename, file_type)
    if not ext:
        return []

    if ext in {"doc", "docx", "xls", "xlsx", "ppt", "pptx"}:
        return [ext, "pdf"]

    return [ext]


def build_download_contract(filename: str, file_type: str | None = None) -> dict[str, object]:
    download_formats = resolve_download_formats(filename, file_type)
    original_format = resolve_original_download_format(filename, file_type)
    return {
        "download_formats": download_formats,
        "original_download_format": original_format or None,
        "has_alternate_downloads": len(download_formats) > 1,
    }


def _detect_extension(filename: str) -> str:
    normalized = (filename or "").strip().lower()
    for ext in COMPOUND_EXTENSIONS:
        if normalized.endswith(f".{ext}"):
            return ext
    return Path(normalized).suffix.lower().lstrip(".")


def _capabilities_for(category: str, preview_mode: str) -> dict[str, bool]:
    return {
        "can_preview": preview_mode in {"native", "converted", "structure"},
        "can_play": category in {"video", "audio"},
        "can_diff_visual": category in {"image", "video", "pdf", "office", "text"},
        "can_diff_structural": category == "archive",
        "can_download": True,
        "can_extract_metadata": True,
        "can_generate_thumbnail": category in {"image", "video", "pdf", "office"},
    }


def resolve_file_profile(filename: str, mime_type: str | None = None) -> dict:
    ext = _detect_extension(filename)
    profile = FILE_PROFILE_REGISTRY.get(ext, {"category": "binary", "preview_mode": "fallback"})
    category = profile["category"]
    preview_mode = profile["preview_mode"]
    resolved_mime = mime_type or mimetypes.guess_type(filename or "")[0] or "application/octet-stream"
    if category == "html" and preview_mode == "native":
        preview_status = "ready"
    else:
        preview_status = "pending" if preview_mode != "fallback" else "not_supported"
    analysis_status = "pending"

    return {
        "ext": ext,
        "mime_type": resolved_mime,
        "category": category,
        "preview_mode": preview_mode,
        "preview_status": preview_status,
        "analysis_status": analysis_status,
        "preview_fallback": "structure_only" if category == "archive" else "download_only",
        "capabilities": _capabilities_for(category, preview_mode),
    }
