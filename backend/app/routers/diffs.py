import json
from typing import Optional, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.params import Param
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord
from app.models.project import Project
from app.schemas.diff import DiffResponse, DiffListResponse
from app.deps.auth import get_current_user
from app.services.access_control_service import require_resource_action
from app.services.diff_service import compute_diff
from app.utils.response import success_response


def _normalize_optional_query_value(value):
    return None if isinstance(value, Param) else value


def _extract_version_number_snapshot(
    diff: DiffRecord,
    *,
    old_version: Optional[FileVersion],
    new_version: Optional[FileVersion],
) -> tuple[int, int]:
    old_number = old_version.version if old_version else 0
    new_number = new_version.version if new_version else 0

    raw_data = diff.diff_data
    if not raw_data:
        return old_number, new_number

    try:
        payload = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
    except (TypeError, ValueError, json.JSONDecodeError):
        return old_number, new_number

    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    if not isinstance(metadata, dict):
        return old_number, new_number

    old_snapshot = metadata.get("old_version_number", old_number)
    new_snapshot = metadata.get("new_version_number", new_number)

    try:
        return int(old_snapshot), int(new_snapshot)
    except (TypeError, ValueError):
        return old_number, new_number


def _resolve_version_for_diff(db: Session, file_id: str, raw_value: Optional[str]) -> Optional[FileVersion]:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None

    version = (
        db.query(FileVersion)
        .filter(FileVersion.id == value, FileVersion.file_id == file_id)
        .first()
    )
    if version:
        return version

    if value.isdigit():
        return (
            db.query(FileVersion)
            .filter(FileVersion.file_id == file_id, FileVersion.version == int(value))
            .first()
        )
    return None


def _get_or_create_diff(db: Session, old_v: FileVersion, new_v: FileVersion) -> DiffRecord:
    diff = (
        db.query(DiffRecord)
        .filter(DiffRecord.old_version_id == old_v.id, DiffRecord.new_version_id == new_v.id)
        .first()
    )
    if diff:
        return diff

    reverse_diff = (
        db.query(DiffRecord)
        .filter(DiffRecord.old_version_id == new_v.id, DiffRecord.new_version_id == old_v.id)
        .first()
    )
    if reverse_diff:
        return reverse_diff

    try:
        return compute_diff(old_v.id, new_v.id, db)
    except IntegrityError:
        db.rollback()
        diff = (
            db.query(DiffRecord)
            .filter(DiffRecord.old_version_id == old_v.id, DiffRecord.new_version_id == new_v.id)
            .first()
        )
        if diff:
            return diff
        raise

def _require_diff_file_action(db: Session, doc_file: DocumentFile, current_user: User) -> None:
    project = db.query(Project).filter(Project.id == doc_file.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    require_resource_action(
        db=db,
        user=current_user,
        resource_type="file",
        resource_id=doc_file.id,
        owner_id=project.owner_id,
        project_id=project.id,
        action="view_diff",
    )


router = APIRouter(prefix="/api/v1", tags=["diffs"])


@router.post("/diffs", status_code=status.HTTP_201_CREATED)
def create_diff_legacy(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compatibility endpoint for older clients: compare two file versions."""
    version1_id = payload.get("version1_id") or payload.get("old_version_id")
    version2_id = payload.get("version2_id") or payload.get("new_version_id")
    if not version1_id or not version2_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version ids are required")

    version1 = db.query(FileVersion).filter(FileVersion.id == version1_id).first()
    version2 = db.query(FileVersion).filter(FileVersion.id == version2_id).first()
    if not version1 or not version2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    if version1.file_id != version2.file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Versions must belong to the same file")
    if payload.get("file_id") and payload.get("file_id") != version1.file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == version1.file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    _require_diff_file_action(db, doc_file, current_user)

    old_v, new_v = sorted([version1, version2], key=lambda item: item.version)
    try:
        diff = _get_or_create_diff(db, old_v, new_v)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diff computation failed: {exc}",
        )

    return success_response(
        data=DiffResponse(
            id=diff.id,
            old_version_id=old_v.id,
            new_version_id=new_v.id,
            old_version=old_v.version,
            new_version=new_v.version,
            diff_type=diff.diff_type,
            diff_data=diff.diff_data,
            summary=diff.summary,
            created_at=diff.created_at,
        ).model_dump()
    )


@router.get("/files/{file_id}/diffs")
def list_diffs(
    file_id: str,
    old_version: Optional[str] = Query(None),
    new_version: Optional[str] = Query(None),
    old_version_id: Optional[str] = Query(None),
    new_version_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    old_version = _normalize_optional_query_value(old_version)
    new_version = _normalize_optional_query_value(new_version)
    old_version_id = _normalize_optional_query_value(old_version_id)
    new_version_id = _normalize_optional_query_value(new_version_id)

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    _require_diff_file_action(db, doc_file, current_user)

    resolved_old = _resolve_version_for_diff(db, file_id, old_version or old_version_id)
    resolved_new = _resolve_version_for_diff(db, file_id, new_version or new_version_id)

    if (old_version or old_version_id) and not resolved_old:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Old version not found")
    if (new_version or new_version_id) and not resolved_new:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New version not found")

    if resolved_old and resolved_new:
        if resolved_old.id == resolved_new.id:
            return success_response(data=DiffListResponse(diffs=[]).model_dump())
        old_v, new_v = sorted([resolved_old, resolved_new], key=lambda item: item.version)
        try:
            diff = _get_or_create_diff(db, old_v, new_v)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Diff computation failed: {exc}",
            )
        diffs = [diff]
    else:
        query = (
            db.query(DiffRecord)
            .join(FileVersion, DiffRecord.new_version_id == FileVersion.id)
            .filter(FileVersion.file_id == file_id)
        )

        if resolved_old:
            query = query.filter(DiffRecord.old_version_id == resolved_old.id)
        if resolved_new:
            query = query.filter(DiffRecord.new_version_id == resolved_new.id)

        diffs = query.order_by(DiffRecord.created_at.desc()).all()

    # 批量查询所有相关的 FileVersion，避免 N+1 查询
    version_ids: set = set()
    for d in diffs:
        version_ids.add(d.old_version_id)
        version_ids.add(d.new_version_id)

    # 一次性批量查询所有版本记录
    version_map: Dict[str, FileVersion] = {}
    if version_ids:
        versions = (
            db.query(FileVersion)
            .filter(FileVersion.id.in_(version_ids))
            .all()
        )
        version_map = {v.id: v for v in versions}

    diff_list = []
    for d in diffs:
        old_v = version_map.get(d.old_version_id)
        new_v = version_map.get(d.new_version_id)
        old_number, new_number = _extract_version_number_snapshot(
            d,
            old_version=old_v,
            new_version=new_v,
        )
        diff_list.append(
            DiffResponse(
                id=d.id,
                old_version_id=d.old_version_id,
                new_version_id=d.new_version_id,
                old_version=old_number,
                new_version=new_number,
                diff_type=d.diff_type,
                diff_data=d.diff_data,
                summary=d.summary,
                created_at=d.created_at,
            ).model_dump()
        )

    return success_response(data=DiffListResponse(diffs=diff_list).model_dump())


@router.get("/files/{file_id}/diffs/{diff_id}")
def get_diff(
    file_id: str,
    diff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diff = db.query(DiffRecord).filter(DiffRecord.id == diff_id).first()
    if not diff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diff not found")

    # Verify the diff belongs to the file
    new_v = db.query(FileVersion).filter(FileVersion.id == diff.new_version_id).first()
    if not new_v or new_v.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diff not found for this file")

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    _require_diff_file_action(db, doc_file, current_user)

    old_v = db.query(FileVersion).filter(FileVersion.id == diff.old_version_id).first()
    old_number, new_number = _extract_version_number_snapshot(
        diff,
        old_version=old_v,
        new_version=new_v,
    )

    return success_response(
        data=DiffResponse(
            id=diff.id,
            old_version_id=diff.old_version_id,
            new_version_id=diff.new_version_id,
            old_version=old_number,
            new_version=new_number,
            diff_type=diff.diff_type,
            diff_data=diff.diff_data,
            summary=diff.summary,
            created_at=diff.created_at,
        ).model_dump()
    )
