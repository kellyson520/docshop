import os
import shutil
import tempfile
import json
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, Form, Body, status
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord
from app.schemas.file import FileResponse, VersionResponse, VersionListResponse
from app.deps.auth import get_current_user, get_current_admin
from app.services.file_service import save_upload_file, get_file_extension
from app.services.diff_service import compute_diff
from app.services.git_store import git_store
from app.config import settings
from app.utils.response import success_response
from app.utils.logger import logger, get_logger, log_audit
from app.validators.file_validator import validate_file_type
from app.exceptions import ResourceNotFound, FileValidationError

router = APIRouter(prefix="/api/v1", tags=["files"])

# 获取模块日志器
files_logger = get_logger("routers.files")


def _versioned_name(filename: str, version_num: int, new_ext: str = None) -> str:
    """生成带版本号的文件名，如 报告_v3.pdf"""
    base, ext = os.path.splitext(filename)
    if new_ext:
        ext = new_ext if new_ext.startswith(".") else f".{new_ext}"
    return f"{base}_v{version_num}{ext}"


def _persist_to_document_store(file_id, file_content, ext, file_hash):
    """增量持久化：将上传文件写入 document_store 三层目录，注册哈希索引。"""
    import hashlib
    import tempfile as _tf
    content_hash = hashlib.sha256(file_content).hexdigest()
    from app.services.document_store import _lookup_hash, ensure_registered, store_original
    existing = _lookup_hash(content_hash)
    if existing:
        files_logger.info(f"增量去重命中 {content_hash[:16]} -> {existing}")
        return
    fd, tmp = _tf.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(file_content)
        store_original(file_id, tmp)
        ensure_registered(file_id, tmp)
        files_logger.info(f"document_store 持久化完成 {file_id}")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass



@router.post("/projects/{project_id}/files", status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate file type
    ext = get_file_extension(file.filename or "")
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_FILE_TYPES)}",
        )

    # 预检查 Content-Length（避免大文件先全部载入内存）
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Magic Bytes 深度验证
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False, dir=settings.TEMP_DIR) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        validate_file_type(
            file_path=__import__("pathlib").Path(tmp_path),
            declared_filename=file.filename or "unknown",
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件类型校验失败: {e.message}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Create DocumentFile record
    doc_file = DocumentFile(
        project_id=project_id,
        filename=file.filename,
        file_type=ext.lstrip("."),
        current_version=1,
    )
    db.add(doc_file)
    db.commit()
    db.refresh(doc_file)

    # Save file to disk and create version record
    storage_path, file_hash, file_size = save_upload_file(
        project_id=project_id,
        file_id=doc_file.id,
        version=1,
        filename=file.filename,
        content=content,
    )

    # ── 增量持久化：写入 document_store 三层结构 + 哈希索引 ──
    _persist_to_document_store(doc_file.id, content, ext, file_hash)

    # Git 风格存储：将文件内容存入对象库
    obj_hash = git_store.put_object(content)
    git_store.update_ref(doc_file.id, 1, obj_hash, "full")

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path=storage_path,
        file_hash=file_hash,
        file_size=file_size,
        storage_mode="full",
    )
    db.add(version)
    db.commit()

    # 审计日志
    log_audit(
        user_id=current_user.id,
        action="upload_file",
        resource=f"project:{project_id}/file:{doc_file.id}",
        result="success",
        details=f"filename={file.filename}, size={file_size}",
    )

    return success_response(
        data=FastAPIFileResponse(
            id=doc_file.id,
            project_id=doc_file.project_id,
            filename=doc_file.filename,
            file_type=doc_file.file_type,
            current_version=doc_file.current_version,
            created_at=doc_file.created_at,
        ).model_dump()
    )


@router.post("/files/{file_id}/versions", status_code=status.HTTP_201_CREATED)
async def upload_version(
    file_id: str,
    file: UploadFile = File(...),
    changelog: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Validate file type matches
    ext = get_file_extension(file.filename or "")
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_FILE_TYPES)}",
        )

    # 预检查 Content-Length
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Magic Bytes 深度验证：先将文件写入临时文件，再进行校验
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False, dir=settings.TEMP_DIR) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        validate_file_type(
            file_path=__import__("pathlib").Path(tmp_path),
            declared_filename=file.filename or "unknown",
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件类型校验失败: {e.message}",
        )
    finally:
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    new_version_num = doc_file.current_version + 1

    storage_path, file_hash, file_size = save_upload_file(
        project_id=doc_file.project_id,
        file_id=doc_file.id,
        version=new_version_num,
        filename=doc_file.filename,
        content=content,
    )

    # ── 增量持久化：写入 document_store 三层结构 + 哈希索引 ──
    _persist_to_document_store(doc_file.id, content, ext, file_hash)

    # 增量存储：首个版本标记为 full，后续标记为 delta（保留 diff 记录）
    prev_version = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == file_id, FileVersion.version == new_version_num - 1)
        .first()
    )
    storage_mode = "delta" if prev_version else "full"

    # Git 风格存储
    obj_hash = git_store.put_object(content)
    git_store.update_ref(doc_file.id, new_version_num, obj_hash, storage_mode)

    # 构建 delta_chain 骨架（operations 由 compute_diff 稍后填充）
    _pending_delta_file_id = doc_file.id
    _pending_delta_version = new_version_num

    version = FileVersion(
        file_id=doc_file.id,
        version=new_version_num,
        sort_order=float(new_version_num),
        storage_path=storage_path,
        file_hash=file_hash,
        file_size=file_size,
        changelog=changelog,
        storage_mode=storage_mode,
        base_version_id=prev_version.id if prev_version else None,
    )
    db.add(version)

    # Update current version
    doc_file.current_version = new_version_num
    db.commit()
    db.refresh(version)

    # Auto compute diff with previous version
    diff_warning = None
    try:
        prev_version = (
            db.query(FileVersion)
            .filter(FileVersion.file_id == file_id, FileVersion.version == new_version_num - 1)
            .first()
        )
        if prev_version:
            diff_record = compute_diff(prev_version.id, version.id, db)
            # 将 diff 结果写入 delta_chain，使 git_store.reconstruct 可用
            if storage_mode == "delta" and diff_record.diff_data:
                try:
                    diff_data = json.loads(diff_record.diff_data) if isinstance(diff_record.diff_data, str) else diff_record.diff_data
                    operations = []
                    for p in diff_data.get("paragraphs", []):
                        ct = p.get("change_type", "equal")
                        if ct == "replace":
                            operations.append({"type": "replace_paragraph", "index": p.get("index", 0), "text": p.get("new_text", "")})
                        elif ct == "insert":
                            operations.append({"type": "insert_paragraph", "index": p.get("index", 0), "text": p.get("new_text", "")})
                        elif ct == "delete":
                            operations.append({"type": "delete_paragraph", "index": p.get("index", 0)})
                    if operations:
                        chain = [{"base_version": new_version_num - 1, "operations": operations}]
                        chain_hash = git_store.put_delta_chain(chain)
                        git_store.update_ref(doc_file.id, new_version_num, chain_hash, "delta")
                except Exception as chain_err:
                    files_logger.warning(f"delta_chain 写入失败: {chain_err}")
    except Exception as e:
        # Diff computation failure should not block upload, but log the error
        files_logger.warning(
            f"自动差异计算失败 - file_id: {file_id}, version: {new_version_num}, "
            f"错误: {e}",
            exc_info=True,
        )
        diff_warning = f"差异自动计算失败: {str(e)}"

    # 审计日志
    log_audit(
        user_id=current_user.id,
        action="upload_version",
        resource=f"file:{file_id}/version:{new_version_num}",
        result="success",
        details=f"filename={doc_file.filename}, size={file_size}, changelog={changelog}",
    )

    response_data = VersionResponse(
        id=version.id,
        version=version.version,
        file_size=version.file_size,
        changelog=version.changelog,
        has_diff=False,  # will be computed
        created_at=version.created_at,
    ).model_dump()

    if diff_warning:
        response_data["warning"] = diff_warning

    return success_response(data=response_data)



def _renumber_versions(db, file_id):
    """按 sort_order 重新编号 version 1,2,3..."""
    from app.models.file_version import FileVersion as FV
    versions = db.query(FV).filter(FV.file_id == file_id).order_by(FV.sort_order.asc()).all()
    for i, v in enumerate(versions, 1):
        v.version = i
    db.commit()


@router.put("/files/{file_id}/versions/reorder")
def reorder_versions(
    file_id: str,
    version_ids: list = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """拖拽排序/调整顺序后调用，version_ids 按新顺序排列。"""
    from app.models.file_version import FileVersion as FV
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")
    id_set = set(version_ids)
    all_versions = {v.id: v for v in db.query(FV).filter(FV.file_id == file_id).all()}
    if not id_set.issubset(all_versions.keys()):
        raise HTTPException(status_code=400, detail="Some version IDs are invalid")
    for i, vid in enumerate(version_ids):
        all_versions[vid].sort_order = float(i + 1)
    db.commit()
    _renumber_versions(db, file_id)
    return success_response(message="排序完成")


@router.delete("/files/{file_id}/versions/{version_id}", status_code=200)
def delete_version(
    file_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除某个版本并自动重排剩余版本的 V 数字。"""
    from app.models.file_version import FileVersion as FV
    v = db.query(FV).filter(FV.id == version_id, FV.file_id == file_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    db.delete(v)
    db.commit()
    _renumber_versions(db, file_id)
    # 更新 document_files.current_version
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    latest = db.query(FV).filter(FV.file_id == file_id).order_by(FV.sort_order.desc()).first()
    if doc_file and latest:
        doc_file.current_version = latest.version
    db.commit()
    return success_response(message="已删除并重排版本")


@router.put("/files/{file_id}/version/{version_id}/category-tags")
def set_file_category_tags(
    file_id: str,
    version_id: str,
    category_id: Optional[str] = Body(None),
    tag_ids: list = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """设置文档的分类和标签。"""
    from app.models.document_file import DocumentFile as DF
    from app.models.category import Category, Tag
    doc = db.query(DF).filter(DF.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    if category_id is not None:
        doc.category_id = category_id if category_id else None
    if tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
        doc.tags = tags
    db.commit()
    return success_response(message="分类标签已更新", data={"category_id": doc.category_id, "tag_ids": [t.id for t in doc.tags]})



@router.get("/files/{file_id}/versions")
def list_versions(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
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
                storage_mode=v.storage_mode or "full",
                created_at=v.created_at,
            ).model_dump()
        )

    return success_response(
        data=VersionListResponse(
            file_id=doc_file.id,
            filename=doc_file.filename,
            file_type=doc_file.file_type,
            current_version=doc_file.current_version,
            versions=version_list,
        ).model_dump()
    )


@router.get("/files/{file_id}/versions/{version_id}/download")
def download_version(
    file_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not os.path.exists(version.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # 路径穿越防御：确保文件在 UPLOAD_DIR 内
    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(version.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        files_logger.error(f"路径穿越检测: {version.storage_path} 不在 {upload_root} 内")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # 审计日志
    log_audit(
        user_id=current_user.id,
        action="download_version",
        resource=f"file:{file_id}/version:{version_id}",
        result="success",
        details=f"filename={doc_file.filename}",
    )

    download_name = _versioned_name(doc_file.filename, version.version)
    safe_name = quote(download_name)
    return FastAPIFileResponse(
        path=version.storage_path,
        filename=download_name,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
        },
    )


@router.get("/files/{file_id}/versions/{version_id}/download/{format}")
def download_version_formatted(
    file_id: str,
    version_id: str,
    format: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    以指定格式下载文件版本（需认证）。

    支持的 format 值：
    - ``docx`` / ``word`` — 返回 Word 格式
    - ``pdf`` — 返回 PDF 格式（服务端转换）
    """
    version = db.query(FileVersion).filter(FileVersion.id == version_id).first()
    if not version or version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not os.path.exists(version.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # 路径穿越防御
    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(version.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        files_logger.error(f"路径穿越检测: {version.storage_path} 不在 {upload_root} 内")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from app.services.conversion_service import convert_to_pdf, convert_to_word, schedule_cleanup

    fmt = format.lower().strip()
    file_type = doc_file.file_type.lower()

    if fmt in ("docx", "word"):
        output_path, media_type, actual_fmt, needs_cleanup = convert_to_word(
            version.storage_path, file_type, doc_file.filename
        )
        download_name = _versioned_name(doc_file.filename, version.version, ".docx")
        if needs_cleanup:
            schedule_cleanup(background_tasks, output_path)
        log_audit(
            user_id=current_user.id,
            action="download_version_formatted",
            resource=f"file:{file_id}/version:{version_id}",
            result="success",
            details=f"format=docx, filename={doc_file.filename}",
        )
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
        pdf_name = _versioned_name(doc_file.filename, version.version, ".pdf")
        disposition = "inline" if actual_fmt == "html" else "attachment"
        if needs_cleanup:
            schedule_cleanup(background_tasks, output_path)
        log_audit(
            user_id=current_user.id,
            action="download_version_formatted",
            resource=f"file:{file_id}/version:{version_id}",
            result="success",
            details=f"format=pdf, actual_fmt={actual_fmt}, filename={doc_file.filename}",
        )
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


@router.get("/files/{file_id}/html")
def get_file_html(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将文件转换为 HTML 用于在线预览（保留格式）"""
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")
    fv = db.query(FileVersion).filter(FileVersion.file_id == file_id).order_by(FileVersion.version.desc()).first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=404, detail="File not found")

    html = "<p>暂不支持此文件类型的格式预览</p>"
    try:
        if doc_file.file_type == "docx":
            from docx import Document as DocxDoc
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from lxml import etree
            from pathlib import Path
            doc = DocxDoc(fv.storage_path)

            # MathML 命名空间
            MNS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

            # 加载 OMML → MathML XSLT 转换器
            xsl_path = Path(__file__).parent.parent / "diff_engine" / "omml2mml.xsl"
            xslt_transform = None
            if xsl_path.exists():
                try:
                    xslt_doc = etree.parse(str(xsl_path))
                    xslt_transform = etree.XSLT(xslt_doc)
                except Exception:
                    pass

            parts = [
                '<meta charset="utf-8">',
                '<script>MathJax={tex:{inlineMath:[["$","$"]]}};</script>',
                '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>',
                '<style>',
                '.docx-page{max-width:210mm;margin:20px auto;padding:20mm 25mm;background:#fff;box-shadow:0 0 12px rgba(0,0,0,.08);',
                'font-family:"Times New Roman","SimSun",serif;font-size:12pt;color:#111;line-height:1.5;}',
                '.docx-page h1{font-size:22pt;margin:16pt 0 8pt;font-weight:bold;border-bottom:1px solid #000;padding-bottom:4pt;}',
                '.docx-page h2{font-size:16pt;margin:14pt 0 6pt;font-weight:bold;}',
                '.docx-page h3{font-size:14pt;margin:12pt 0 4pt;font-weight:bold;}',
                '.docx-page p{margin:0 0 6pt 0;text-indent:0;}',
                '.docx-page table{border-collapse:collapse;width:100%;margin:8pt 0;}',
                '.docx-page td,.docx-page th{border:1px solid #333;padding:3pt 6pt;vertical-align:top;font-size:11pt;}',
                '@media(max-width:800px){.docx-page{padding:10px;max-width:100%;margin:0;}}',
                '</style>',
                '<div class="docx-page">'
            ]

            for para in doc.paragraphs:
                pf = para.paragraph_format
                css = []
                if pf.alignment == WD_ALIGN_PARAGRAPH.CENTER: css.append("text-align:center")
                elif pf.alignment == WD_ALIGN_PARAGRAPH.RIGHT: css.append("text-align:right")
                elif pf.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY: css.append("text-align:justify")
                if pf.first_line_indent: css.append(f"text-indent:{pf.first_line_indent.pt}pt")
                if pf.space_before: css.append(f"margin-top:{pf.space_before.pt}pt")
                if pf.space_after: css.append(f"margin-bottom:{pf.space_after.pt}pt")
                if pf.line_spacing and pf.line_spacing != 1.0: css.append(f"line-height:{pf.line_spacing}")
                style = ";".join(css) if css else ""
                is_heading = para.style.name.startswith("Heading")
                hn = para.style.name.replace("Heading ", "") if is_heading else ""

                math_elements = para._element.findall(f"{{{MNS}}}oMath") + para._element.findall(f"{{{MNS}}}oMathPara")
                if math_elements:
                    parts.append(f'<p style="{style}">' if not is_heading else f'<h{hn} style="{style}">')
                    for me in math_elements:
                        try:
                            if xslt_transform is not None:
                                # 使用 XSLT 完整转换
                                result = xslt_transform(me)
                                mathml = str(result)
                                if mathml.strip():
                                    parts.append(mathml)
                                else:
                                    parts.append('<span style="color:#999">[数学公式]</span>')
                            else:
                                parts.append('<span style="color:#999">[数学公式]</span>')
                        except Exception:
                            parts.append('<span style="color:#999">[数学公式]</span>')
                    parts.append('</p>' if not is_heading else f'</h{hn}>')
                    continue

                if not para.text.strip() and not para.runs:
                    parts.append('<p><br></p>')
                    continue

                default_style = style if style else "margin:3pt 0;line-height:1.5"
                parts.append(f'<h{hn} style="{style or "margin:12pt 0 6pt"}">' if is_heading else f'<p style="{default_style}">')
                for run in para.runs:
                    text = run.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    if not text: continue
                    tags, sty = [], []
                    if run.bold: tags.append("b")
                    if run.italic: tags.append("i")
                    if run.underline: tags.append("u")
                    if run.font.size: sty.append(f"font-size:{run.font.size.pt}pt")
                    if run.font.name: sty.append(f"font-family:'{run.font.name}'")
                    if run.font.color and run.font.color.rgb: sty.append(f"color:#{run.font.color.rgb}")
                    if sty: tags.append(f'span style=\"{";".join(sty)}\"')
                    for t in tags: parts.append(f"<{t}>")
                    parts.append(text)
                    for t in reversed(tags): parts.append(f"</{t.split()[0]}>")
                parts.append(f'</h{hn}>' if is_heading else '</p>')

            for table in doc.tables:
                parts.append('<table class="docx-table">')
                for row in table.rows:
                    parts.append('<tr>')
                    for cell in row.cells:
                        parts.append('<td>')
                        for cp in cell.paragraphs:
                            if cp.text.strip():
                                parts.append('<p>')
                                for r in cp.runs:
                                    t = r.text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                    if r.bold: parts.append(f"<b>{t}</b>")
                                    elif r.italic: parts.append(f"<i>{t}</i>")
                                    else: parts.append(t)
                                parts.append('</p>')
                        parts.append('</td>')
                    parts.append('</tr>')
                parts.append('</table>')

            parts.append('</div>')
            html = "".join(parts)

        elif doc_file.file_type == "pdf":
            html = f'<iframe src="/api/v1/files/{file_id}/preview" width="100%" height="700px" style="border:none"></iframe>'

    except Exception as e:
        html = f"<p>转换失败: {str(e)}</p>"

    return success_response(data={"html": html, "filename": doc_file.filename, "file_type": doc_file.file_type})


@router.get("/files/{file_id}/text")
def get_file_text(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提取文件文本内容用于在线预览"""
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")
    fv = db.query(FileVersion).filter(FileVersion.file_id == file_id).order_by(FileVersion.version.desc()).first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=404, detail="File not found")

    text = ""
    try:
        if doc_file.file_type == "docx":
            from docx import Document as DocxDoc
            doc = DocxDoc(fv.storage_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif doc_file.file_type in ("xlsx", "xls"):
            import openpyxl
            wb = openpyxl.load_workbook(fv.storage_path, data_only=True)
            for name in wb.sheetnames:
                ws = wb[name]
                text += f"\n=== {name} ===\n"
                for row in ws.iter_rows(max_row=200, values_only=True):
                    text += "\t".join(str(c) if c is not None else "" for c in row) + "\n"
        elif doc_file.file_type == "pdf" and HAS_PYMUPDF:
            import fitz
            doc = fitz.open(fv.storage_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        else:
            text = "暂不支持此文件类型的文本预览"
    except Exception as e:
        text = f"提取失败: {str(e)}"
    return success_response(data={"text": text[:50000], "filename": doc_file.filename, "file_type": doc_file.file_type})


@router.get("/files/{file_id}/preview")
def preview_file(
    file_id: str,
    version: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
):
    """文件预览（浏览器内嵌展示，PDF 等格式直接渲染）"""
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")

    query = db.query(FileVersion).filter(FileVersion.file_id == file_id)
    if version:
        query = query.filter(FileVersion.version == version)
    else:
        query = query.order_by(FileVersion.version.desc())
    fv = query.first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(fv.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        raise HTTPException(status_code=404, detail="File not found")

    from app.services.conversion_service import convert_to_html, convert_to_pdf, convert_to_images_html

    # PDF: 直接返回，inline 显示
    if doc_file.file_type == "pdf":
        safe_name = quote(doc_file.filename)
        return FastAPIFileResponse(
            path=fv.storage_path,
            filename=doc_file.filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}", "Content-Encoding": "identity"},
        )

    # DOCX/DOC: 优先图片预览（像素级完美，浏览器100%兼容）
    if doc_file.file_type in ("docx", "doc"):
        from fastapi.responses import HTMLResponse
        from app.exceptions import ConversionError
        try:
            html = convert_to_images_html(file_id, fv.storage_path, doc_file.file_type)
            if html:
                return HTMLResponse(content=html)
        except ConversionError as e:
            raise HTTPException(status_code=422, detail=e.message)
        except Exception as e:
            logger.warning(f"图片预览生成失败: {e}，回退")

    # DOCX/DOC/XLSX: 回退 — 转换引擎 → PDF inline 或 HTML
    if doc_file.file_type in ("docx", "doc", "xlsx", "xls"):
        try:
            pdf_path, media_type, actual_fmt, needs_cleanup = convert_to_pdf(
                fv.storage_path, doc_file.file_type, doc_file.filename
            )
            if actual_fmt == "pdf":
                if needs_cleanup:
                    from app.services.conversion_service import schedule_cleanup
                    schedule_cleanup(background_tasks, pdf_path)
                safe_name = quote(os.path.basename(pdf_path))
                return FastAPIFileResponse(
                    path=pdf_path,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_name}", "Content-Encoding": "identity"},
                )
            elif actual_fmt == "html":
                from fastapi.responses import HTMLResponse
                with open(pdf_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                if needs_cleanup:
                    from app.services.conversion_service import schedule_cleanup
                    schedule_cleanup(background_tasks, pdf_path)
                return HTMLResponse(content=html_content)
        except Exception as e:
            logger.warning(f"PDF 预览转换失败: {e}，回退 HTML")

    # Fallback: HTML 预览
    try:
        html, media_type, _ = convert_to_html(fv.storage_path, doc_file.file_type)
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览生成失败: {str(e)}")
@router.get("/files/{file_id}/download")
def download_file(
    file_id: str,
    version: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文件下载（按版本号）"""
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")

    query = db.query(FileVersion).filter(FileVersion.file_id == file_id)
    if version:
        query = query.filter(FileVersion.version == version)
    else:
        query = query.order_by(FileVersion.version.desc())
    fv = query.first()
    if not fv or not os.path.exists(fv.storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    real_path = os.path.realpath(fv.storage_path)
    if not real_path.startswith(upload_root + os.sep):
        raise HTTPException(status_code=404, detail="File not found")

    log_audit(
        user_id=current_user.id,
        action="download_file",
        resource=f"file:{file_id}",
        result="success",
    )

    download_name = _versioned_name(doc_file.filename, fv.version)
    safe_name = quote(download_name)
    return FastAPIFileResponse(
        path=fv.storage_path,
        filename=doc_file.filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.get("/files/{file_id}/versions/{version_id}/reconstruct")
def reconstruct_version(
    file_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从增量存储重建完整文件"""
    version = db.query(FileVersion).filter(FileVersion.id == version_id, FileVersion.file_id == file_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()

    # 如果是 full 模式或文件存在，直接返回
    if version.storage_mode == "full" or os.path.exists(version.storage_path):
        safe_name = quote(doc_file.filename)
        return FastAPIFileResponse(
            path=version.storage_path, filename=doc_file.filename,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
        )

    # Delta 模式：从基版本重建
    base = db.query(FileVersion).filter(FileVersion.id == version.base_version_id).first()
    if not base or not os.path.exists(base.storage_path):
        raise HTTPException(status_code=404, detail="Base version not found, cannot reconstruct")

    # 查找该版本的 DiffRecord
    diff = db.query(DiffRecord).filter(DiffRecord.new_version_id == version_id).first()
    if not diff or not diff.diff_data:
        raise HTTPException(status_code=404, detail="Diff data not found")

    try:
        import json
        diff_data = json.loads(diff.diff_data) if isinstance(diff.diff_data, str) else diff.diff_data

        if doc_file.file_type != "docx":
            # 非 DOCX：直接返回基版本（无法文本重建）
            safe_name = quote(doc_file.filename)
            return FastAPIFileResponse(
                path=base.storage_path, filename=doc_file.filename,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
            )

        # DOCX 重建：克隆基版本，应用段落变更
        from docx import Document as DocxDoc
        import shutil, tempfile
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".docx", dir=settings.TEMP_DIR)
        os.close(tmp_fd)
        shutil.copy2(base.storage_path, tmp_path)

        doc = DocxDoc(tmp_path)
        paragraphs = doc.paragraphs
        table_diffs = diff_data.get("tables", [])
        para_diffs = diff_data.get("paragraphs", [])

        # 构建段落索引映射
        para_map = {i: p for i, p in enumerate(paragraphs)}

        for pd in para_diffs:
            ct = pd.get("change_type", "equal")
            idx = pd.get("index", 0)
            if ct == "equal":
                continue
            elif ct == "replace" and idx < len(paragraphs):
                new_text = pd.get("new_text", "")
                if new_text:
                    # 清除旧内容，写入新内容
                    p = paragraphs[idx]
                    for run in p.runs:
                        run.text = ""
                    if p.runs:
                        p.runs[0].text = new_text
                    else:
                        p.add_run(new_text)
            elif ct == "insert":
                # 在末尾追加新段落
                new_text = pd.get("new_text", "")
                if new_text:
                    doc.add_paragraph(new_text)

        doc.save(tmp_path)

        safe_name = quote(doc_file.filename)
        return FastAPIFileResponse(
            path=tmp_path, filename=doc_file.filename,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
        )
    except Exception as e:
        files_logger.error(f"重建失败: {e}")
        raise HTTPException(status_code=500, detail=f"Reconstruction failed: {str(e)}")


@router.get("/storage/stats")
def storage_stats(current_user: User = Depends(get_current_admin)):
    """Git 风格存储统计"""
    return success_response(data=git_store.get_stats())


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # 先收集所有版本的存储路径
    versions = db.query(FileVersion).filter(FileVersion.file_id == file_id).all()
    storage_paths = [v.storage_path for v in versions]

    # 先删除数据库记录（原子性：先删数据库再删磁盘文件）
    db.delete(doc_file)
    db.commit()

    # 再删除磁盘文件
    for storage_path in storage_paths:
        if os.path.exists(storage_path):
            try:
                os.remove(storage_path)
            except OSError as e:
                files_logger.warning(f"删除磁盘文件失败 {storage_path}: {e}")

    # Remove file directory if empty
    file_dir = os.path.join(settings.UPLOAD_DIR, doc_file.project_id, file_id)
    if os.path.isdir(file_dir):
        try:
            shutil.rmtree(file_dir)
        except OSError as e:
            files_logger.warning(f"删除文件目录失败 {file_dir}: {e}")

    # 审计日志
    log_audit(
        user_id=current_user.id,
        action="delete_file",
        resource=f"file:{file_id}",
        result="success",
        details=f"filename={doc_file.filename}, project_id={doc_file.project_id}",
    )

    return None
