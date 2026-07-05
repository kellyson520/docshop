"""Lightweight in-process preview generation queue.

The queue stores durable user-visible state in document_store meta.json and
keeps only scheduling state in memory. It intentionally defaults to very low
concurrency so upload requests do not trigger competing Word/PDF render work.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import threading
import tarfile
from typing import Any, Deque, Dict, Optional
import uuid
import zipfile

from app.config import settings
from app.services import document_store
from app.services.archive_analysis_service import build_archive_manifest
from app.services.file_capability_service import (
    FILE_PROFILE_REGISTRY,
    PREVIEWABLE_CATEGORIES,
    resolve_file_profile,
)
from app.services.media_metadata_service import (
    extract_image_metadata,
    extract_video_metadata,
    extract_video_poster_frame,
    generate_compatible_video_preview,
    summarize_media_metadata,
)
from app.services.preview_scheduler import PreviewJobContext, sort_preview_jobs
from app.utils.logger import get_logger

logger = get_logger("services.preview_queue")

PREVIEWABLE_TYPES = {
    ext
    for ext, profile in FILE_PROFILE_REGISTRY.items()
    if profile.get("category") in PREVIEWABLE_CATEGORIES
}
RUNNING_STATUSES = {"queued", "pdf_generating", "pdf_ready", "images_generating"}
TERMINAL_STATUSES = {"missing", "ready", "failed", "interrupted", "unsupported"}
KNOWN_STATUSES = RUNNING_STATUSES | TERMINAL_STATUSES


@dataclass
class PreviewJob:
    file_id: str
    storage_path: str
    file_type: str
    force: bool = False
    project_id: Optional[str] = None
    file_size: int = 0
    updated_at: Optional[str] = None
    failure_count: int = 0
    queued_at: Optional[str] = None


_lock = threading.RLock()
_queue: Deque[PreviewJob] = deque()
_queued: Dict[str, PreviewJob] = {}
_running: Dict[str, PreviewJob] = {}
_worker_thread: Optional[threading.Thread] = None
_recent_project_ids: Deque[str] = deque(maxlen=8)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_error(exc: BaseException) -> str:
    message = str(exc) or exc.__class__.__name__
    return message[:500]


def _directory_size(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return 0
    for current_root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(current_root, name))
            except OSError:
                pass
    return total


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _short_hash(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value)
    return text[:8] if text else None


def _profile_for_preview_target(
    *,
    file_type: str | None = None,
    storage_path: str | None = None,
    filename: str | None = None,
) -> dict:
    normalized_type = (file_type or "").lower().lstrip(".")
    candidate_name = filename or Path(storage_path or "").name
    if not candidate_name and normalized_type:
        candidate_name = f"file.{normalized_type}"
    return resolve_file_profile(candidate_name)


def _is_previewable_profile(file_profile: dict) -> bool:
    return file_profile.get("category") in PREVIEWABLE_CATEGORIES


def _safe_file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _normalized_storage_path(path: str) -> str:
    resolved = resolve_storage_path(path)
    try:
        return os.path.normcase(os.path.realpath(resolved))
    except OSError:
        return os.path.normcase(str(resolved or ""))


def _image_workers() -> int:
    override = os.environ.get("PREVIEW_IMAGE_MAX_WORKERS")
    if override:
        try:
            return max(1, int(override))
        except ValueError:
            pass
    return min(os.cpu_count() or 2, 4, 2)


def _pdf_timeout_seconds() -> int:
    override = os.environ.get("PREVIEW_PDF_TIMEOUT_SECONDS")
    if override:
        try:
            return max(5, int(override))
        except ValueError:
            pass
    return 45


def resolve_storage_path(storage_path: str) -> str:
    """Resolve storage paths, preferring the configured upload directory.

    Historical records may contain relative values such as ``data/uploads/a.pdf``.
    In deployments with bind-mounted data, the current working directory can also
    contain stale files, so preview generation should first resolve against
    ``settings.UPLOAD_DIR`` before falling back to legacy project roots.
    """
    if not storage_path:
        return storage_path

    path = Path(storage_path)
    if path.is_absolute():
        return str(path)

    try:
        upload_dir = Path(settings.UPLOAD_DIR).resolve(strict=False)
        parts = path.parts
        lowered = [part.lower() for part in parts]
        if "uploads" in lowered:
            idx = lowered.index("uploads")
            configured_candidate = upload_dir.joinpath(*parts[idx + 1:])
        else:
            configured_candidate = upload_dir / path.name
        if configured_candidate.exists():
            return str(configured_candidate)
    except Exception:
        pass

    if path.exists():
        return str(path)

    cwd = Path.cwd()
    roots = [cwd]
    if cwd.name.lower() == "backend":
        roots.append(cwd.parent)
    try:
        roots.append(Path(__file__).resolve().parents[3])
    except IndexError:
        pass

    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        candidate = root / path
        if candidate.exists():
            return str(candidate)

    return storage_path


def _set_preview(file_id: str, **updates: Any) -> Dict[str, Any]:
    return document_store.update_preview_meta(file_id, **updates)


def _resolve_db_version(db, file_id: str, storage_path: str):
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        return None, None

    versions = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version.desc())
        .all()
    )
    normalized_storage = _normalized_storage_path(storage_path)
    matched_version = next(
        (
            item
            for item in versions
            if _normalized_storage_path(getattr(item, "storage_path", "")) == normalized_storage
        ),
        None,
    )
    if matched_version is None and getattr(doc_file, "current_version", None):
        matched_version = next(
            (item for item in versions if item.version == doc_file.current_version),
            None,
        )
    if matched_version is None and versions:
        matched_version = versions[0]
    return doc_file, matched_version


def _persist_derived_assets(
    *,
    file_id: str,
    storage_path: str,
    asset_specs: list[dict],
    analysis_record: dict | None,
    preview_status: str,
    analysis_status: str,
    preview_error: str | None = None,
    analysis_error: str | None = None,
    force: bool = False,
) -> None:
    from app.database import get_db_context
    from app.models.file_analysis_record import FileAnalysisRecord
    from app.models.file_preview_asset import FilePreviewAsset

    with get_db_context() as db:
        doc_file, version = _resolve_db_version(db, file_id, storage_path)
        if not doc_file or not version:
            return

        existing_asset_count = (
            db.query(FilePreviewAsset)
            .filter(FilePreviewAsset.version_id == version.id)
            .count()
        )
        existing_analysis_count = (
            db.query(FileAnalysisRecord)
            .filter(FileAnalysisRecord.version_id == version.id)
            .count()
        )

        db.query(FilePreviewAsset).filter(FilePreviewAsset.version_id == version.id).delete(synchronize_session=False)
        db.query(FileAnalysisRecord).filter(FileAnalysisRecord.version_id == version.id).delete(synchronize_session=False)

        for spec in asset_specs:
            db.add(
                FilePreviewAsset(
                    file_id=file_id,
                    version_id=version.id,
                    asset_type=spec["asset_type"],
                    storage_path=spec["storage_path"],
                    page_number=spec.get("page_number"),
                    width=spec.get("width"),
                    height=spec.get("height"),
                    size_bytes=spec.get("size_bytes") or _safe_file_size(spec["storage_path"]),
                    sort_order=int(spec.get("sort_order") or 0),
                    status=spec.get("status") or "ready",
                    error_message=spec.get("error_message"),
                )
            )

        if analysis_record:
            db.add(
                FileAnalysisRecord(
                    file_id=file_id,
                    version_id=version.id,
                    analysis_type=analysis_record["analysis_type"],
                    payload_json=json.dumps(analysis_record.get("payload") or {}, ensure_ascii=False),
                    status=analysis_record.get("status") or "ready",
                    error_message=analysis_record.get("error_message"),
                )
            )

        replacing_existing = existing_asset_count > 0 or existing_analysis_count > 0
        current_asset_version = max(int(getattr(version, "derived_asset_version", 1) or 1), 1)
        version.derived_asset_version = current_asset_version + 1 if (force or replacing_existing) else current_asset_version
        version.preview_refresh_token = str(uuid.uuid4())
        version.preview_status = preview_status
        version.analysis_status = analysis_status
        version.preview_error = preview_error
        version.analysis_error = analysis_error

        doc_file.preview_status = preview_status
        doc_file.analysis_status = analysis_status
        doc_file.preview_error = preview_error
        doc_file.analysis_error = analysis_error
        db.commit()


def _mark_generation_failure(file_id: str, storage_path: str, error_message: str) -> None:
    from app.database import get_db_context

    with get_db_context() as db:
        doc_file, version = _resolve_db_version(db, file_id, storage_path)
        if version:
            version.preview_status = "failed"
            version.analysis_status = "failed"
            version.preview_error = error_message
            version.analysis_error = error_message
        if doc_file:
            doc_file.preview_status = "failed"
            doc_file.analysis_status = "failed"
            doc_file.preview_error = error_message
            doc_file.analysis_error = error_message
        db.commit()


def _archive_entries_for(storage_path: str) -> list[dict]:
    def _normalized_member_path(path: str) -> str:
        normalized = str(path or "").replace("\\", "/").strip()
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized.lstrip("/")

    if not zipfile.is_zipfile(storage_path):
        if not tarfile.is_tarfile(storage_path):
            return []

        entries = []
        with tarfile.open(storage_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_path = _normalized_member_path(member.name)
                if not member_path:
                    continue
                entries.append({"path": member_path, "size": int(member.size or 0)})
        return entries

    entries = []
    with zipfile.ZipFile(storage_path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member_path = _normalized_member_path(info.filename)
            if not member_path:
                continue
            entries.append({"path": member_path, "size": int(info.file_size or 0)})
    return entries


def _persist_paginated_preview(
    *,
    file_id: str,
    storage_path: str,
    pdf_path: str,
    page_paths: list[str],
    page_count: int,
    analysis_type: str,
    force: bool,
) -> None:
    assets = [
        {
            "asset_type": "pdf",
            "storage_path": pdf_path,
            "sort_order": 0,
        }
    ]
    for page_number, page_path in enumerate(page_paths, start=1):
        assets.append(
            {
                "asset_type": "thumbnail",
                "storage_path": page_path,
                "page_number": page_number,
                "sort_order": page_number,
            }
        )
        assets.append(
            {
                "asset_type": "page_image",
                "storage_path": page_path,
                "page_number": page_number,
                "sort_order": page_number + page_count,
            }
        )

    _persist_derived_assets(
        file_id=file_id,
        storage_path=storage_path,
        asset_specs=assets,
        analysis_record={
            "analysis_type": analysis_type,
            "payload": {"page_count": page_count},
            "status": "ready",
        },
        preview_status="ready",
        analysis_status="ready",
        force=force,
    )


def _run_archive_job(job: PreviewJob, storage_path: str) -> None:
    entries = _archive_entries_for(storage_path)
    document_store.store_original(job.file_id, storage_path)
    _persist_derived_assets(
        file_id=job.file_id,
        storage_path=storage_path,
        asset_specs=[],
        analysis_record={
            "analysis_type": "archive_manifest",
            "payload": build_archive_manifest(entries),
            "status": "ready",
        },
        preview_status="ready",
        analysis_status="ready",
        force=job.force,
    )
    _set_preview(
        job.file_id,
        status="ready",
        progress=100,
        stage="预览已就绪",
        finished_at=_now_iso(),
        error=None,
        failure_count=0,
        storage_bytes=0,
    )


def _run_native_job(job: PreviewJob, storage_path: str, category: str) -> None:
    stored_original = document_store.store_original(job.file_id, storage_path)
    preview_path = storage_path if os.path.exists(storage_path) else stored_original
    analysis_payload = (
        extract_image_metadata(preview_path)
        if category == "image"
        else extract_video_metadata(preview_path)
    )
    dimensions = analysis_payload.get("dimensions") or {}
    asset_specs = []

    if category == "video":
        poster_path = os.path.join(document_store.dir_images(job.file_id), "video-poster.jpg")
        poster = extract_video_poster_frame(preview_path, poster_path)
        if poster.get("generated") and poster.get("path") and os.path.exists(poster["path"]):
            asset_specs.append(
                {
                    "asset_type": "poster",
                    "storage_path": poster["path"],
                    "sort_order": 0,
                }
            )
        compatible_video_path = os.path.join(document_store.dir_original(job.file_id), "preview-video.mp4")
        compatible_video = generate_compatible_video_preview(preview_path, compatible_video_path)
        if (
            compatible_video.get("generated")
            and compatible_video.get("path")
            and os.path.exists(compatible_video["path"])
        ):
            asset_specs.append(
                {
                    "asset_type": "preview_video",
                    "storage_path": compatible_video["path"],
                    "width": dimensions.get("width"),
                    "height": dimensions.get("height"),
                    "sort_order": len(asset_specs),
                }
            )
        asset_specs.append(
            {
                "asset_type": "video",
                "storage_path": preview_path,
                "width": dimensions.get("width"),
                "height": dimensions.get("height"),
                "sort_order": len(asset_specs),
            }
        )
    else:
        asset_specs.append(
            {
                "asset_type": "image",
                "storage_path": preview_path,
                "width": dimensions.get("width"),
                "height": dimensions.get("height"),
                "sort_order": 0,
            }
        )

    _persist_derived_assets(
        file_id=job.file_id,
        storage_path=storage_path,
        asset_specs=asset_specs,
        analysis_record={
            "analysis_type": "media_metadata",
            "payload": analysis_payload,
            "status": "ready",
        },
        preview_status="ready",
        analysis_status="ready",
        force=job.force,
    )
    _set_preview(
        job.file_id,
        status="ready",
        progress=100,
        stage="预览已就绪",
        finished_at=_now_iso(),
        error=None,
        failure_count=0,
        storage_bytes=0,
    )


def reset_queue_for_tests() -> None:
    """Clear in-memory queue state. Intended for unit tests only."""
    global _worker_thread
    with _lock:
        _queue.clear()
        _queued.clear()
        _running.clear()
        _recent_project_ids.clear()
        _worker_thread = None


def get_queue_state() -> Dict[str, int]:
    with _lock:
        return {"queued": len(_queued), "running": len(_running)}


def enqueue_preview_generation(
    file_id: str,
    storage_path: str,
    file_type: str,
    *,
    force: bool = False,
    autostart: bool = True,
    project_id: Optional[str] = None,
    file_size: Optional[int] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Queue preview generation and persist a queued state.

    If a job is already queued/running and force is false, return the existing
    snapshot and mark it as deduplicated.
    """
    normalized_type = (file_type or "").lower().lstrip(".")
    file_profile = _profile_for_preview_target(file_type=normalized_type, storage_path=storage_path)
    if not _is_previewable_profile(file_profile):
        preview = _set_preview(
            file_id,
            status="unsupported",
            progress=0,
            stage="该文件类型不支持托管预览",
            error=None,
            storage_bytes=0,
        )
        return {"file_id": file_id, **preview, "deduplicated": False}

    with _lock:
        if not force and (file_id in _queued or file_id in _running):
            snapshot = get_preview_snapshot(file_id, normalized_type)
            snapshot["deduplicated"] = True
            return snapshot

        if force:
            _queued.pop(file_id, None)
            try:
                _queue.remove(next(job for job in _queue if job.file_id == file_id))
            except (StopIteration, ValueError):
                pass
            document_store.clear_preview_cache(file_id)

        resolved_storage_path = resolve_storage_path(storage_path)
        source_hash = ""
        try:
            source_hash = document_store.file_sha256(resolved_storage_path)
        except OSError:
            pass

        previous_preview = document_store._read_meta(file_id).get("preview") or {}
        previous_failures = int(previous_preview.get("failure_count") or (1 if previous_preview.get("status") == "failed" else 0))
        if file_size is None:
            try:
                file_size = os.path.getsize(resolved_storage_path)
            except OSError:
                file_size = 0

        queued_at = _now_iso()
        preview = _set_preview(
            file_id,
            status="queued",
            progress=0,
            stage="等待生成预览",
            queued_at=queued_at,
            started_at=None,
            finished_at=None,
            error=None,
            source_hash=source_hash,
            storage_bytes=document_store.preview_storage_bytes(file_id),
        )
        job = PreviewJob(
            file_id=file_id,
            storage_path=resolved_storage_path,
            file_type=normalized_type,
            force=force,
            project_id=project_id,
            file_size=int(file_size or 0),
            updated_at=updated_at,
            failure_count=previous_failures,
            queued_at=queued_at,
        )
        _queue.append(job)
        _queued[file_id] = job

    if autostart:
        _start_worker_if_needed()

    return {"file_id": file_id, **preview, "deduplicated": False}


def _start_worker_if_needed() -> None:
    global _worker_thread
    with _lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="preview-queue")
        _worker_thread.start()


def _job_context(job: PreviewJob) -> PreviewJobContext:
    return PreviewJobContext(
        file_id=job.file_id,
        project_id=job.project_id,
        file_size=job.file_size,
        updated_at=_parse_dt(job.updated_at),
        failure_count=job.failure_count,
        queued_at=_parse_dt(job.queued_at),
    )


def _prioritize_queue_locked() -> None:
    if len(_queue) < 2:
        return
    contexts = {_job_context(job).file_id: _job_context(job) for job in _queue}
    ordered_contexts = sort_preview_jobs(contexts.values(), recent_project_ids=list(_recent_project_ids))
    jobs_by_id = {job.file_id: job for job in _queue}
    _queue.clear()
    _queue.extend(jobs_by_id[item.file_id] for item in ordered_contexts if item.file_id in jobs_by_id)


def _worker_loop() -> None:
    while True:
        with _lock:
            if not _queue:
                return
            _prioritize_queue_locked()
            job = _queue.popleft()
            _queued.pop(job.file_id, None)
            _running[job.file_id] = job
            if job.project_id:
                _recent_project_ids.append(job.project_id)
        try:
            _run_job(job)
        except Exception as exc:  # defensive; _run_job also marks failure
            logger.exception("Preview job crashed")
            _set_preview(
                job.file_id,
                status="failed",
                stage="预览生成失败",
                error=_short_error(exc),
                finished_at=_now_iso(),
            )
            _mark_generation_failure(job.file_id, job.storage_path, _short_error(exc))
        finally:
            with _lock:
                _running.pop(job.file_id, None)


def _run_job(job: PreviewJob) -> None:
    from app.services.conversion_service import _ensure_pdf, _source_hash

    file_id = job.file_id
    try:
        storage_path = resolve_storage_path(job.storage_path)
        file_profile = resolve_file_profile(Path(storage_path).name or f"file.{job.file_type}")
        category = file_profile.get("category")

        if category == "archive":
            _set_preview(
                file_id,
                status="pdf_generating",
                progress=10,
                stage="正在解析压缩包结构",
                started_at=_now_iso(),
                error=None,
            )
            _run_archive_job(job, storage_path)
            return

        if category in {"video", "image"}:
            _set_preview(
                file_id,
                status="pdf_generating",
                progress=10,
                stage="正在准备原生预览",
                started_at=_now_iso(),
                error=None,
            )
            _run_native_job(job, storage_path, category)
            return

        _set_preview(
            file_id,
            status="pdf_generating",
            progress=10,
            stage="正在准备 PDF",
            started_at=_now_iso(),
            error=None,
        )

        document_store.store_original(file_id, storage_path)
        source_hash = _source_hash(storage_path)

        if file_profile.get("preview_mode") == "converted":
            pdf_path = _ensure_pdf(
                file_id,
                storage_path,
                source_hash,
                timeout_seconds=_pdf_timeout_seconds(),
            )
            if pdf_path is None:
                raise RuntimeError("PDF conversion failed")
            pdf_hash = _source_hash(pdf_path)
        else:
            document_store._ensure_dirs(file_id)
            pdf_dest = os.path.join(document_store.dir_pdf(file_id), "document.pdf")
            if os.path.normcase(os.path.realpath(storage_path)) != os.path.normcase(os.path.realpath(pdf_dest)):
                shutil.copy2(storage_path, pdf_dest)
            pdf_path = pdf_dest
            pdf_hash = source_hash
            meta = document_store._read_meta(file_id)
            meta["pdf_source_hash"] = source_hash
            meta["pdf_generated_at"] = _now_iso()
            document_store._write_meta(file_id, meta)

        _set_preview(
            file_id,
            status="pdf_ready",
            progress=50,
            stage="PDF 已生成",
            source_hash=source_hash,
            pdf_hash=pdf_hash,
        )

        import fitz

        doc = fitz.open(pdf_path)
        try:
            page_count = len(doc)
        finally:
            doc.close()

        if page_count <= 0:
            raise RuntimeError("PDF has no pages")

        cached = document_store.get_cached_images(file_id, pdf_hash, page_count)
        if not cached:
            _set_preview(
                file_id,
                status="images_generating",
                progress=50,
                stage="正在生成页面图片",
                page_count=page_count,
                rendered_pages=0,
            )

            def on_progress(rendered: int, total: int) -> None:
                progress = min(99, 50 + int((rendered / max(total, 1)) * 49))
                _set_preview(
                    file_id,
                    status="images_generating",
                    progress=progress,
                    stage="正在生成页面图片",
                    page_count=total,
                    rendered_pages=rendered,
                    storage_bytes=document_store.preview_storage_bytes(file_id),
                )

            dpi = document_store.adaptive_dpi(page_count)
            cached = document_store.generate_images(
                file_id,
                pdf_path,
                page_count,
                pdf_hash,
                dpi=dpi,
                quality=75,
                max_workers=_image_workers(),
                progress_callback=on_progress,
            )

        if len(cached or []) != page_count:
            raise RuntimeError(f"Only rendered {len(cached or [])}/{page_count} pages")

        storage_bytes = document_store.preview_storage_bytes(file_id)
        analysis_type = "office_summary" if category == "office" else "pdf_summary"
        _persist_paginated_preview(
            file_id=file_id,
            storage_path=storage_path,
            pdf_path=pdf_path,
            page_paths=list(cached or []),
            page_count=page_count,
            analysis_type=analysis_type,
            force=job.force,
        )
        _set_preview(
            file_id,
            status="ready",
            progress=100,
            stage="预览已就绪",
            page_count=page_count,
            rendered_pages=page_count,
            storage_bytes=storage_bytes,
            finished_at=_now_iso(),
            error=None,
            failure_count=0,
        )
    except Exception as exc:
        existing = document_store._read_meta(file_id).get("preview") or {}
        progress = min(int(existing.get("progress") or 0), 99)
        failure_count = int(existing.get("failure_count") or 0) + 1
        _set_preview(
            file_id,
            status="failed",
            progress=progress,
            stage="预览生成失败",
            error=_short_error(exc),
            failure_count=failure_count,
            storage_bytes=document_store.preview_storage_bytes(file_id),
            finished_at=_now_iso(),
        )
        _mark_generation_failure(file_id, storage_path if "storage_path" in locals() else job.storage_path, _short_error(exc))


def get_preview_snapshot(
    file_id: str,
    file_type: str,
    *,
    filename: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_type = (file_type or "").lower().lstrip(".")
    file_profile = _profile_for_preview_target(file_type=normalized_type, filename=filename)
    if not _is_previewable_profile(file_profile):
        status = "unsupported"
        preview: Dict[str, Any] = {"status": status, "progress": 0, "storage_bytes": 0}
    else:
        meta = document_store._read_meta(file_id)
        preview = dict(meta.get("preview") or {})
        status = preview.get("status") or "missing"
        with _lock:
            in_memory = file_id in _queued or file_id in _running
        if status in RUNNING_STATUSES and not in_memory:
            preview = document_store.update_preview_meta(
                file_id,
                status="interrupted",
                progress=min(int(preview.get("progress") or 0), 99),
                stage="上一次预览生成已中断",
                error="后台任务已中断，可重新生成",
                finished_at=_now_iso(),
            )
            status = "interrupted"
        elif not preview:
            preview = {"status": "missing", "progress": 0, "storage_bytes": document_store.preview_storage_bytes(file_id)}
            status = "missing"
        elif status not in KNOWN_STATUSES:
            preview = document_store.update_preview_meta(
                file_id,
                status="missing",
                progress=0,
                stage="预览状态未知，需重新生成",
                error=None,
                finished_at=_now_iso(),
            )
            status = "missing"

    pdf_bytes = _directory_size(document_store.dir_pdf(file_id))
    image_bytes = _directory_size(document_store.dir_images(file_id))
    actual_storage_bytes = pdf_bytes + image_bytes
    storage_bytes = preview.get("storage_bytes")
    if actual_storage_bytes or storage_bytes in (None, ""):
        storage_bytes = actual_storage_bytes

    row = {
        "file_id": file_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": normalized_type,
        "status": status,
        "progress": int(preview.get("progress") or 0),
        "stage": preview.get("stage"),
        "error": preview.get("error"),
        "page_count": preview.get("page_count"),
        "rendered_pages": preview.get("rendered_pages"),
        "storage_bytes": int(storage_bytes or 0),
        "pdf_bytes": int(pdf_bytes or 0),
        "image_bytes": int(image_bytes or 0),
        "source_hash_short": _short_hash(preview.get("source_hash")),
        "pdf_hash_short": _short_hash(preview.get("pdf_hash")),
        "queued_at": preview.get("queued_at"),
        "started_at": preview.get("started_at"),
        "updated_at": preview.get("updated_at"),
        "finished_at": preview.get("finished_at"),
    }
    return row
