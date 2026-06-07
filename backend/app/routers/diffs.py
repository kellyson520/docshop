from typing import Optional, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord
from app.schemas.diff import DiffResponse, DiffListResponse
from app.deps.auth import get_current_user
from app.utils.response import success_response

router = APIRouter(prefix="/api/v1/files", tags=["diffs"])


@router.get("/{file_id}/diffs")
def list_diffs(
    file_id: str,
    old_version: Optional[str] = Query(None),
    new_version: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    query = (
        db.query(DiffRecord)
        .join(FileVersion, DiffRecord.new_version_id == FileVersion.id)
        .filter(FileVersion.file_id == file_id)
    )

    if old_version:
        query = query.filter(DiffRecord.old_version_id == old_version)
    if new_version:
        query = query.filter(DiffRecord.new_version_id == new_version)

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
        diff_list.append(
            DiffResponse(
                id=d.id,
                old_version=old_v.version if old_v else 0,
                new_version=new_v.version if new_v else 0,
                diff_type=d.diff_type,
                diff_data=d.diff_data,
                summary=d.summary,
                created_at=d.created_at,
            ).model_dump()
        )

    return success_response(data=DiffListResponse(diffs=diff_list).model_dump())


@router.get("/{file_id}/diffs/{diff_id}")
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

    old_v = db.query(FileVersion).filter(FileVersion.id == diff.old_version_id).first()

    return success_response(
        data=DiffResponse(
            id=diff.id,
            old_version=old_v.version if old_v else 0,
            new_version=new_v.version if new_v else 0,
            diff_type=diff.diff_type,
            diff_data=diff.diff_data,
            summary=diff.summary,
            created_at=diff.created_at,
        ).model_dump()
    )
