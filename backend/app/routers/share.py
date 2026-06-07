import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.project import Project
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord
from app.schemas.project import ProjectResponse
from app.schemas.file import FileResponse, VersionResponse, VersionListResponse
from app.schemas.diff import DiffResponse, DiffListResponse
from app.utils.response import success_response
from app.utils.logger import get_logger

logger = get_logger("routers.share")

router = APIRouter(prefix="/api/v1/share", tags=["share"])


@router.get("/public-exams")
def list_public_exams(db: Session = Depends(get_db)):
    """公开考试列表（游客可浏览）"""
    from app.models.exam_schedule import ExamSchedule
    exams = db.query(ExamSchedule).order_by(ExamSchedule.start_time.asc()).limit(10).all()
    items = []
    for e in exams:
        items.append({
            "id": e.id, "name": e.name, "description": e.description,
            "start_time": e.start_time, "end_time": e.end_time,
            "status": e.status, "project_name": e.project.name if e.project else None,
        })
    return success_response(data=items)

@router.get("/public-exams/{exam_id}")
def get_public_exam_detail(
    exam_id: str,
    db: Session = Depends(get_db),
):
    from app.models.exam_schedule import ExamSchedule
    from datetime import datetime as dt
    exam = db.query(ExamSchedule).filter(ExamSchedule.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    now = dt.utcnow().isoformat()
    if now > exam.end_time:
        exam.status = "expired"
    elif now >= exam.start_time:
        exam.status = "ongoing"
    return success_response(data={
        "id": exam.id, "name": exam.name, "description": exam.description,
        "start_time": exam.start_time, "end_time": exam.end_time,
        "status": exam.status,
        "project_name": exam.project.name if exam.project else None,
        "creator_name": exam.creator.username if exam.creator else None,
        "reminder_15min": bool(exam.reminder_15min),
        "reminder_5min": bool(exam.reminder_5min),
        "reminder_start": bool(exam.reminder_start),
    })

@router.get("/public-projects")
def list_public_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """公开项目列表（无需登录，游客可浏览）"""
    query = db.query(Project).options(joinedload(Project.owner)).filter(Project.is_public == 1)
    if keyword:
        query = query.filter(Project.name.ilike(f"%{keyword}%"))
    total = query.count()
    projects = query.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 批量查询：一次取所有项目的文件数和首文件
    project_ids = [p.id for p in projects]
    file_counts = {}
    first_files = {}
    if project_ids:
        from sqlalchemy import func
        # 文件计数
        count_rows = (
            db.query(DocumentFile.project_id, func.count(DocumentFile.id))
            .filter(DocumentFile.project_id.in_(project_ids))
            .group_by(DocumentFile.project_id)
            .all()
        )
        file_counts = {row[0]: row[1] for row in count_rows}
        # 每个项目的第一个文件
        first_file_subq = (
            db.query(
                DocumentFile.project_id,
                func.min(DocumentFile.created_at).label("min_created"),
            )
            .filter(DocumentFile.project_id.in_(project_ids))
            .group_by(DocumentFile.project_id)
            .subquery()
        )
        ff_rows = (
            db.query(DocumentFile)
            .join(
                first_file_subq,
                (DocumentFile.project_id == first_file_subq.c.project_id)
                & (DocumentFile.created_at == first_file_subq.c.min_created),
            )
            .all()
        )
        first_files = {f.project_id: f for f in ff_rows}

    items = []
    for p in projects:
        first_file = first_files.get(p.id)
        cover_url = None
        if first_file and first_file.cover_image:
            c = first_file.cover_image
            cover_url = c if c.startswith("/api/") else "/api/v1/" + c.replace("\\", "/")

        items.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "share_token": p.share_token,
            "file_count": file_counts.get(p.id, 0),
            "cover_image": cover_url,
            "uploader": {
                "id": p.owner.id,
                "username": p.owner.username,
                "role": p.owner.role,
                "avatar": getattr(p.owner, "avatar_url", None) or "",
            } if p.owner else None,
            "first_file": {
                "id": first_file.id,
                "filename": first_file.filename,
                "file_type": first_file.file_type,
            } if first_file else None,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        })
    return success_response(data={"total": total, "page": page, "page_size": page_size, "items": items})


def _get_project_by_token(share_token: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.share_token == share_token).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    return project


def _versioned_name(filename: str, version_num: int, new_ext: str = None) -> str:
    """生成带版本号的文件名，如 报告_v3.pdf"""
    base, ext = os.path.splitext(filename)
    if new_ext:
        ext = new_ext if new_ext.startswith(".") else f".{new_ext}"
    return f"{base}_v{version_num}{ext}"


@router.get("/{share_token}")
def get_shared_project(share_token: str, db: Session = Depends(get_db)):
    project = _get_project_by_token(share_token, db)

    file_count = db.query(DocumentFile).filter(DocumentFile.project_id == project.id).count()
    files = db.query(DocumentFile).filter(DocumentFile.project_id == project.id).all()
    file_ids = [f.id for f in files]

    # 批量获取最新版本信息（download 和 changelog 用）
    latest_versions = {}
    if file_ids:
        from sqlalchemy import tuple_
        from sqlalchemy.sql import func
        max_v = (
            db.query(FileVersion.file_id, func.max(FileVersion.version).label("max_ver"))
            .filter(FileVersion.file_id.in_(file_ids))
            .group_by(FileVersion.file_id)
            .subquery()
        )
        rows = (
            db.query(FileVersion)
            .join(max_v, tuple_(FileVersion.file_id, FileVersion.version) == tuple_(max_v.c.file_id, max_v.c.max_ver))
            .all()
        )
        latest_versions = {r.file_id: r for r in rows}

    file_list = []
    for f in files:
        latest = latest_versions.get(f.id)
        versions_info = []
        if latest:
            versions_info = [{"id": latest.id, "version": latest.version, "file_size": latest.file_size, "changelog": latest.changelog}]
        file_list.append({
            "id": f.id,
            "project_id": f.project_id,
            "original_filename": f.filename,
            "filename": f.filename,
            "file_type": f.file_type,
            "current_version": f.current_version,
            "file_size": latest.file_size if latest else 0,
            "created_at": f.created_at,
            "updated_at": f.updated_at or f.created_at,
            "latest_changelog": latest.changelog if latest else "",
            "versions": versions_info,
        })

    return success_response(
        data={
            "project": ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                share_token=project.share_token,
                is_public=project.is_public,
                file_count=file_count,
                created_at=project.created_at,
                updated_at=project.updated_at,
            ).model_dump(),
            "files": file_list,
        }
    )


@router.get("/{share_token}/files/{file_id}")
def get_shared_file(
    share_token: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # 获取最新版本大小
    latest_ver = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version.desc())
        .first()
    )
    return success_response(
        data={
            "id": doc_file.id,
            "project_id": doc_file.project_id,
            "original_filename": doc_file.filename,
            "filename": doc_file.filename,
            "file_type": doc_file.file_type,
            "current_version": doc_file.current_version,
            "file_size": latest_ver.file_size if latest_ver else 0,
            "created_at": doc_file.created_at,
            "updated_at": doc_file.updated_at or doc_file.created_at,
        }
    )


@router.get("/{share_token}/files/{file_id}/versions")
def get_shared_versions(
    share_token: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    versions = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version.desc())
        .all()
    )

    version_list = []
    for v in versions:
        has_diff = (
            db.query(DiffRecord)
            .filter(DiffRecord.new_version_id == v.id)
            .first()
            is not None
        )
        version_list.append(
            VersionResponse(
                id=v.id,
                version=v.version,
                file_size=v.file_size,
                changelog=v.changelog,
                has_diff=has_diff,
                created_at=v.created_at,
            ).model_dump()
        )

    result = VersionListResponse(
        file_id=doc_file.id,
        filename=doc_file.filename,
        file_type=doc_file.file_type,
        current_version=doc_file.current_version,
        versions=version_list,
    ).model_dump()
    return success_response(data=result)


@router.get("/{share_token}/files/{file_id}/diffs")
def get_shared_diffs(
    share_token: str,
    file_id: str,
    old_version: Optional[str] = Query(None),
    new_version: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
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

    version_map: dict = {}
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


@router.get("/{share_token}/files/{file_id}/versions/{version_id}/download")
def download_shared_version(
    share_token: str,
    file_id: str,
    version_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    if not os.path.exists(version.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # 路径穿越防御：确保文件在 UPLOAD_DIR 内
    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(version.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from urllib.parse import quote
    download_name = _versioned_name(doc_file.filename, version.version)
    safe_name = quote(download_name)
    return FastAPIFileResponse(
        path=version.storage_path,
        filename=download_name,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.get("/{share_token}/files/{file_id}/versions/{version_id}/download/{format}")
def download_shared_version_formatted(
    share_token: str,
    file_id: str,
    version_id: str,
    format: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    以指定格式下载分享文件的版本。

    支持的 format 值：
    - ``docx`` / ``word`` — 返回 Word 格式（原始 docx/doc 文件）
    - ``pdf`` — 返回 PDF 格式（服务端转换）

    对于 PDF 格式请求：
    - 如果原文件已是 PDF → 直接返回
    - 如果原文件是 DOCX/DOC → LibreOffice 原生转换（不可用时生成 HTML 供浏览器打印）
    - 如果原文件是 XLSX/XLS → 同理转换
    """
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    if not os.path.exists(version.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # 路径穿越防御
    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(version.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from app.services.conversion_service import convert_to_pdf, convert_to_word, schedule_cleanup
    from urllib.parse import quote

    fmt = format.lower().strip()
    file_type = doc_file.file_type.lower()

    if fmt in ("docx", "word"):
        output_path, media_type, actual_fmt, needs_cleanup = convert_to_word(
            version.storage_path, file_type, doc_file.filename
        )
        # Word 格式：带版本号
        download_name = _versioned_name(doc_file.filename, version.version, ".docx")
        if needs_cleanup:
            schedule_cleanup(background_tasks, output_path)
        return FastAPIFileResponse(
            path=output_path,
            filename=download_name,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(download_name)}"},
        )

    elif fmt == "pdf":
        output_path, media_type, actual_fmt, needs_cleanup = convert_to_pdf(
            version.storage_path, file_type, doc_file.filename
        )
        # PDF 文件名（带版本号）
        pdf_name = _versioned_name(doc_file.filename, version.version, ".pdf")
        disposition = "inline" if actual_fmt == "html" else "attachment"
        if needs_cleanup:
            schedule_cleanup(background_tasks, output_path)
        return FastAPIFileResponse(
            path=output_path,
            filename=pdf_name,
            media_type=media_type,
            headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(pdf_name)}"},
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}. Supported: docx, pdf",
        )


@router.get("/{share_token}/files/{file_id}/preview")
def preview_shared_file(
    share_token: str,
    file_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """公开预览分享文件（无需登录）。优先使用 MS Word COM 导出 HTML，保真度最高。"""
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    fv = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version.desc())
        .first()
    )
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # 路径穿越防御
    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(fv.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from app.services.conversion_service import convert_to_html, convert_to_pdf, convert_to_images_html

    if doc_file.file_type == "pdf":
        from urllib.parse import quote
        safe_name = quote(doc_file.filename)
        html = f'<iframe src="/api/v1/share/{share_token}/files/{file_id}/preview/pdf" width="100%" height="100%" style="border:none;min-height:700px"></iframe>'
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)

    # DOCX/DOC: 优先图片预览（像素级完美，浏览器100%兼容）
    if doc_file.file_type in ("docx", "doc"):
        from app.exceptions import ConversionError
        try:
            html = convert_to_images_html(file_id, fv.storage_path, doc_file.file_type)
            if html:
                from fastapi.responses import HTMLResponse
                return HTMLResponse(content=html)
        except ConversionError as e:
            raise HTTPException(status_code=422, detail=e.message)
        except Exception as e:
            logger.warning(f"图片预览生成失败: {e}，回退")

    # DOCX/DOC/XLSX: 回退 — Word COM 转为 PDF（公式、图片、排版 100% 还原）
    if doc_file.file_type in ("docx", "doc", "xlsx", "xls"):
        try:
            pdf_path, media_type, actual_fmt, needs_cleanup = convert_to_pdf(
                fv.storage_path, doc_file.file_type, doc_file.filename
            )
            if actual_fmt == "pdf":
                # 成功生成 PDF → 内嵌显示
                from urllib.parse import quote
                if needs_cleanup:
                    from app.services.conversion_service import schedule_cleanup
                    schedule_cleanup(background_tasks, pdf_path)
                safe_name = quote(os.path.basename(pdf_path))
                return FastAPIFileResponse(
                    path=pdf_path,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}", "Content-Encoding": "identity"},
                )
        except Exception as e:
            logger.warning(f"PDF 预览转换失败: {e}，回退 HTML")

    # Fallback: HTML 预览
    try:
        html, media_type, _ = convert_to_html(fv.storage_path, doc_file.file_type)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览生成失败: {str(e)}")


@router.get("/{share_token}/files/{file_id}/preview/pdf")
def preview_shared_pdf(
    share_token: str,
    file_id: str,
    db: Session = Depends(get_db),
):
    """公开预览 PDF 文件（内嵌渲染）。"""
    project = _get_project_by_token(share_token, db)

    doc_file = (
        db.query(DocumentFile)
        .filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id)
        .first()
    )
    if not doc_file or doc_file.file_type != "pdf":
        raise HTTPException(status_code=404, detail="Not a PDF file")

    fv = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id)
        .order_by(FileVersion.version.desc())
        .first()
    )
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=404, detail="File not found")

    from urllib.parse import quote
    safe_name = quote(doc_file.filename)
    return FastAPIFileResponse(
        path=fv.storage_path,
        filename=doc_file.filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}", "Content-Encoding": "identity"},
    )
