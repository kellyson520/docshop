from __future__ import annotations

"""Diff computation service."""

import json
import os
import time

from sqlalchemy.orm import Session

from app.diff_engine.factory import get_diff_engine
from app.exceptions import DiffCalculationError, ResourceNotFound
from app.models.diff_record import DiffRecord
from app.models.document_file import DocumentFile
from app.models.file_analysis_record import FileAnalysisRecord
from app.models.file_version import FileVersion
from app.schemas.diff_result import normalize_diff_result
from app.services.archive_analysis_service import diff_archive_manifests
from app.services.file_capability_service import resolve_file_profile
from app.services.media_metadata_service import summarize_media_metadata
from app.utils.logger import get_logger, log_audit


diff_logger = get_logger("services.diff_service")


def _safe_json_loads(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _version_download_url(file_id: str, version_id: str) -> str:
    return f"/api/v1/files/{file_id}/versions/{version_id}/download"


def _resolve_file_category(doc_file: DocumentFile) -> str:
    profile = resolve_file_profile(
        filename=getattr(doc_file, "filename", None) or f"file.{doc_file.file_type}",
        mime_type=getattr(doc_file, "mime_type", None),
    )
    stored_category = getattr(doc_file, "file_category", None)
    if stored_category and stored_category != "binary":
        return stored_category
    return profile["category"]


def _load_analysis_payload(
    db: Session,
    *,
    file_id: str,
    version_id: str,
    preferred_types: tuple[str, ...],
) -> dict:
    analysis = (
        db.query(FileAnalysisRecord)
        .filter(
            FileAnalysisRecord.file_id == file_id,
            FileAnalysisRecord.version_id == version_id,
            FileAnalysisRecord.analysis_type.in_(preferred_types),
        )
        .order_by(FileAnalysisRecord.updated_at.desc())
        .first()
    )
    if analysis:
        return _safe_json_loads(analysis.payload_json)

    fallback = (
        db.query(FileAnalysisRecord)
        .filter(
            FileAnalysisRecord.file_id == file_id,
            FileAnalysisRecord.version_id == version_id,
        )
        .order_by(FileAnalysisRecord.updated_at.desc())
        .first()
    )
    if fallback:
        return _safe_json_loads(fallback.payload_json)
    return {}


def _humanize_archive_summary(summary: dict) -> str:
    return f"新增 {summary.get('files_added', 0)} 个文件，删除 {summary.get('files_removed', 0)} 个文件"


def _numeric_delta(current, previous) -> int:
    try:
        current_value = float(current or 0)
        previous_value = float(previous or 0)
    except (TypeError, ValueError):
        return 0
    return int(abs(current_value - previous_value))


def _humanize_media_summary(summary: dict) -> str:
    parts = [
        f"时长变化 {summary.get('duration_delta_seconds', 0)} 秒",
        f"大小变化 {summary.get('size_delta_bytes', 0)} 字节",
    ]
    if summary.get("codec_changed"):
        parts.append("编码发生变化")
    return "，".join(parts)


def _build_archive_diff_result(
    *,
    db: Session,
    doc_file: DocumentFile,
    old_version: FileVersion,
    new_version: FileVersion,
) -> tuple[str, dict]:
    previous_manifest = _load_analysis_payload(
        db,
        file_id=doc_file.id,
        version_id=old_version.id,
        preferred_types=("archive_manifest",),
    )
    current_manifest = _load_analysis_payload(
        db,
        file_id=doc_file.id,
        version_id=new_version.id,
        preferred_types=("archive_manifest",),
    )

    if not previous_manifest or not current_manifest:
        raise DiffCalculationError(
            message="归档结构分析尚未就绪",
            file_type=doc_file.file_type,
        )

    structural_summary = diff_archive_manifests(previous_manifest, current_manifest)
    stats = {
        "files_added": structural_summary["files_added"],
        "files_removed": structural_summary["files_removed"],
        "total_changes": structural_summary["files_added"] + structural_summary["files_removed"],
    }

    return "structure", {
        "type": "archive_diff",
        "payload": {
            "added_paths": structural_summary["added_paths"],
            "removed_paths": structural_summary["removed_paths"],
            "left": {
                "entry_count": previous_manifest.get("entry_count", 0),
                "root_nodes": previous_manifest.get("root_nodes", []),
            },
            "right": {
                "entry_count": current_manifest.get("entry_count", 0),
                "root_nodes": current_manifest.get("root_nodes", []),
            },
        },
        "summary": {
            "files_added": structural_summary["files_added"],
            "files_removed": structural_summary["files_removed"],
        },
        "summary_text": _humanize_archive_summary(structural_summary),
        "metadata": {
            "file_type": doc_file.file_type,
            "file_category": "archive",
        },
        "stats": stats,
        "status": "completed",
        "error": None,
    }


def _build_media_diff_result(
    *,
    db: Session,
    doc_file: DocumentFile,
    old_version: FileVersion,
    new_version: FileVersion,
) -> tuple[str, dict]:
    old_analysis_raw = _load_analysis_payload(
        db,
        file_id=doc_file.id,
        version_id=old_version.id,
        preferred_types=("media_metadata",),
    )
    new_analysis_raw = _load_analysis_payload(
        db,
        file_id=doc_file.id,
        version_id=new_version.id,
        preferred_types=("media_metadata",),
    )

    old_analysis = summarize_media_metadata(old_analysis_raw) if old_analysis_raw else {}
    new_analysis = summarize_media_metadata(new_analysis_raw) if new_analysis_raw else {}

    duration_delta = _numeric_delta(
        new_analysis.get("duration_seconds"),
        old_analysis.get("duration_seconds"),
    )
    size_delta = _numeric_delta(new_version.file_size, old_version.file_size)
    codec_changed = bool(
        old_analysis.get("codec")
        and new_analysis.get("codec")
        and old_analysis.get("codec") != new_analysis.get("codec")
    )
    bit_rate_delta = _numeric_delta(
        new_analysis.get("bit_rate"),
        old_analysis.get("bit_rate"),
    )

    summary = {
        "duration_delta_seconds": duration_delta,
        "size_delta_bytes": size_delta,
        "codec_changed": codec_changed,
        "bit_rate_delta": bit_rate_delta,
    }
    stats = {
        "duration_changed": int(duration_delta > 0),
        "size_changed": int(size_delta > 0),
        "codec_changed": int(codec_changed),
        "bit_rate_changed": int(bit_rate_delta > 0),
    }
    stats["total_changes"] = sum(stats.values())

    return "media", {
        "type": "media_diff",
        "payload": {
            "left": {
                "version_id": old_version.id,
                "version_number": old_version.version,
                "preview_url": _version_download_url(doc_file.id, old_version.id),
                "filename": doc_file.filename,
                "analysis": old_analysis,
            },
            "right": {
                "version_id": new_version.id,
                "version_number": new_version.version,
                "preview_url": _version_download_url(doc_file.id, new_version.id),
                "filename": doc_file.filename,
                "analysis": new_analysis,
            },
        },
        "summary": summary,
        "summary_text": _humanize_media_summary(summary),
        "metadata": {
            "file_type": doc_file.file_type,
            "file_category": _resolve_file_category(doc_file),
        },
        "stats": stats,
        "status": "completed",
        "error": None,
    }


def _compute_specialized_diff(
    *,
    db: Session,
    doc_file: DocumentFile,
    old_version: FileVersion,
    new_version: FileVersion,
) -> tuple[str, dict] | None:
    category = _resolve_file_category(doc_file)
    if category == "archive":
        return _build_archive_diff_result(
            db=db,
            doc_file=doc_file,
            old_version=old_version,
            new_version=new_version,
        )
    if category in {"video", "audio"}:
        return _build_media_diff_result(
            db=db,
            doc_file=doc_file,
            old_version=old_version,
            new_version=new_version,
        )
    return None


def compute_diff(old_version_id: str, new_version_id: str, db: Session) -> DiffRecord:
    """Compute a diff record between two file versions and persist it."""
    diff_logger.info(f"开始计算差异 - old: {old_version_id}, new: {new_version_id}")

    old_version = db.query(FileVersion).filter(FileVersion.id == old_version_id).first()
    new_version = db.query(FileVersion).filter(FileVersion.id == new_version_id).first()

    if not old_version:
        raise ResourceNotFound(resource="文件版本", resource_id=old_version_id)
    if not new_version:
        raise ResourceNotFound(resource="文件版本", resource_id=new_version_id)

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == new_version.file_id).first()
    if not doc_file:
        raise ResourceNotFound(resource="文件记录", resource_id=new_version.file_id)

    if not os.path.exists(old_version.storage_path):
        raise ResourceNotFound(
            resource="旧版本文件",
            resource_id=old_version.storage_path,
        )
    if not os.path.exists(new_version.storage_path):
        raise ResourceNotFound(
            resource="新版本文件",
            resource_id=new_version.storage_path,
        )

    diff_type = "text"
    diff_result = None
    started_at = time.perf_counter()

    try:
        specialized_result = _compute_specialized_diff(
            db=db,
            doc_file=doc_file,
            old_version=old_version,
            new_version=new_version,
        )

        if specialized_result:
            diff_type, diff_result = specialized_result
            metadata = diff_result.setdefault("metadata", {})
            metadata["elapsed_ms"] = int((time.perf_counter() - started_at) * 1000)
        else:
            try:
                engine = get_diff_engine(doc_file.file_type)
            except Exception as e:
                diff_logger.error(f"获取差异引擎失败 - file_type: {doc_file.file_type}, 错误: {e}")
                raise DiffCalculationError(
                    message=f"不支持的文件类型: {doc_file.file_type}",
                    file_type=doc_file.file_type,
                )

            diff_result = engine.compare(old_version.storage_path, new_version.storage_path)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            diff_result = normalize_diff_result(
                diff_result,
                file_type=doc_file.file_type,
                elapsed_ms=elapsed_ms,
                status="completed",
                error=None,
            )
            diff_type_map = {
                "docx_diff": "text",
                "xlsx_diff": "cell",
                "pdf_diff": "visual",
                "html_diff": "html",
            }
            diff_type = diff_type_map.get(diff_result.get("type", ""), "text")
    except DiffCalculationError:
        raise
    except Exception as e:
        diff_logger.error(
            f"差异计算失败 - old: {old_version.storage_path}, new: {new_version.storage_path}, 错误: {e}",
            exc_info=True,
        )
        raise DiffCalculationError(
            message=f"差异计算过程中发生错误: {str(e)}",
            file_type=doc_file.file_type,
        )

    metadata = diff_result.setdefault("metadata", {})
    metadata["old_version_id"] = old_version.id
    metadata["new_version_id"] = new_version.id
    metadata["old_version_number"] = old_version.version
    metadata["new_version_number"] = new_version.version

    diff_record = DiffRecord(
        old_version_id=old_version_id,
        new_version_id=new_version_id,
        diff_type=diff_type,
        diff_data=json.dumps(diff_result, ensure_ascii=False, default=str),
        summary=str(diff_result.get("summary_text") or diff_result.get("summary") or ""),
    )

    db.add(diff_record)
    db.commit()
    db.refresh(diff_record)

    log_audit(
        user_id="system",
        action="compute_diff",
        resource=f"diff:{diff_record.id}",
        result="success",
        details=f"old_version={old_version_id}, new_version={new_version_id}, type={diff_type}",
    )

    diff_logger.info(f"差异计算完成 - diff_id: {diff_record.id}, type: {diff_type}")
    return diff_record
