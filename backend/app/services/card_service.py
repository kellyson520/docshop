"""
卡片式文档管理服务模块

提供卡片相关的业务逻辑处理，包括卡片列表查询、详情获取、
封面管理、多版本对比等功能。
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import UploadFile, HTTPException, status

from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord
from app.config import settings
from app.utils.logger import logger, get_logger
from app.services.diff_service import compute_diff

# 获取模块日志器
card_logger = get_logger("services.card_service")

# 支持的图片格式
ALLOWED_IMAGE_TYPES = {"jpeg", "jpg", "png", "gif", "webp"}
# 最大图片大小（5MB）
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def normalize_cover_image_path(cover_image: Optional[str]) -> str:
    """Return a browser-ready cover URL under /api/v1/covers."""
    if not cover_image:
        return ""

    cover = str(cover_image).replace("\\", "/").strip()
    if not cover:
        return ""
    if cover.startswith("http://") or cover.startswith("https://"):
        return cover
    if cover.startswith("/api/v1/covers/"):
        return cover
    if cover.startswith("api/v1/covers/"):
        return f"/{cover}"
    if cover.startswith("/covers/"):
        return f"/api/v1{cover}"
    if cover.startswith("covers/"):
        return f"/api/v1/{cover}"

    data_root = Path(settings.UPLOAD_DIR).parent.resolve()
    try:
        cover_path = Path(cover).resolve()
        if cover_path.is_relative_to(data_root):
            relative = cover_path.relative_to(data_root).as_posix()
            if relative.startswith("covers/"):
                return f"/api/v1/{relative}"
    except (OSError, ValueError):
        pass

    return cover if cover.startswith("/") else f"/api/v1/{cover}"


def cover_image_to_disk_path(cover_image: Optional[str]) -> Optional[Path]:
    """Convert a stored cover URL/path back to the local covers directory."""
    cover_url = normalize_cover_image_path(cover_image)
    prefix = "/api/v1/"
    if not cover_url.startswith(prefix):
        return None

    relative = cover_url[len(prefix):].lstrip("/").replace("\\", "/")
    if not relative.startswith("covers/"):
        return None

    data_root = Path(settings.UPLOAD_DIR).parent.resolve()
    cover_path = (data_root / relative).resolve()
    try:
        if not cover_path.is_relative_to(data_root / "covers"):
            return None
    except ValueError:
        return None
    return cover_path


def get_cards_list(
    db: Session,
    project_id: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[dict], int]:
    """
    获取卡片列表（支持搜索、分页）
    
    Args:
        db: 数据库会话
        project_id: 项目ID（可选，用于筛选）
        keyword: 搜索关键词（可选，匹配显示名称、文件名、描述）
        page: 页码（从1开始）
        page_size: 每页数量
        
    Returns:
        Tuple[List[dict], int]: (卡片列表数据, 总数)
        
    Raises:
        HTTPException: 查询参数无效时抛出
    """
    operation_id = f"list_page{page}_size{page_size}"
    card_logger.info(f"获取卡片列表: {operation_id}")
    
    try:
        # 参数校验
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="页码必须大于0"
            )
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="每页数量必须在1-100之间"
            )
        
        # 构建基础查询
        query = db.query(DocumentFile)
        
        # 按项目筛选
        if project_id:
            query = query.filter(DocumentFile.project_id == project_id)
        
        # 关键词搜索（匹配显示名称、文件名、描述）
        if keyword:
            keyword_filter = or_(
                DocumentFile.display_name.ilike(f"%{keyword}%"),
                DocumentFile.filename.ilike(f"%{keyword}%"),
                DocumentFile.description.ilike(f"%{keyword}%")
            )
            query = query.filter(keyword_filter)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * page_size
        files = query.order_by(DocumentFile.updated_at.desc()) \
                     .offset(offset) \
                     .limit(page_size) \
                     .all()
        
        # 批量获取版本计数和最新版本大小
        file_ids = [f.id for f in files]
        version_counts = {}
        latest_sizes = {}
        if file_ids:
            # 获取每个文件的版本数
            version_rows = (
                db.query(FileVersion.file_id, func.count().label("cnt"))
                .filter(FileVersion.file_id.in_(file_ids))
                .group_by(FileVersion.file_id)
                .all()
            )
            version_counts = {row.file_id: row.cnt for row in version_rows}
            # 获取每个文件最新版本的大小：子查询取 max version per file
            from sqlalchemy import tuple_
            max_versions = (
                db.query(FileVersion.file_id, func.max(FileVersion.version).label("max_ver"))
                .filter(FileVersion.file_id.in_(file_ids))
                .group_by(FileVersion.file_id)
                .subquery()
            )
            latest_rows = (
                db.query(FileVersion.file_id, FileVersion.file_size)
                .join(max_versions, tuple_(
                    FileVersion.file_id, FileVersion.version
                ) == tuple_(
                    max_versions.c.file_id, max_versions.c.max_ver
                ))
                .all()
            )
            latest_sizes = {row.file_id: row.file_size for row in latest_rows}

        # 构建响应数据
        cards = []
        for file in files:
            display_name = file.display_name if file.display_name else file.filename
            updated_at = file.updated_at if file.updated_at else file.created_at

            # 确保 cover_image 是完整的 API 路径
            cover = normalize_cover_image_path(file.cover_image)

            card = {
                "id": file.id,
                "display_name": display_name,
                "filename": file.filename,
                "cover_image": cover,
                "version_count": version_counts.get(file.id, 0),
                "file_size": latest_sizes.get(file.id),
                "current_version": file.current_version,
                "updated_at": updated_at,
                "description": file.description,
                "file_type": file.file_type,
            }
            cards.append(card)
        
        card_logger.info(f"卡片列表查询成功: 总数={total}, 返回={len(cards)}")
        return cards, total
        
    except HTTPException:
        raise
    except Exception as e:
        card_logger.error(f"获取卡片列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取卡片列表失败: {str(e)}"
        )


def get_card_detail(db: Session, card_id: str) -> dict:
    """
    获取卡片详情
    
    包含文件信息和所有版本列表。
    
    Args:
        db: 数据库会话
        card_id: 卡片ID
        
    Returns:
        dict: 卡片详情数据
        
    Raises:
        HTTPException: 卡片不存在或查询失败时抛出
    """
    card_logger.info(f"获取卡片详情: {card_id}")
    
    try:
        # 查询文件记录
        doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
        if not doc_file:
            card_logger.warning(f"卡片不存在: {card_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 查询所有版本
        versions = db.query(FileVersion) \
                     .filter(FileVersion.file_id == card_id) \
                     .order_by(FileVersion.version.desc()) \
                     .all()
        
        # 构建版本列表
        version_list = []
        for v in versions:
            version_list.append({
                "id": v.id,
                "version": v.version,
                "created_at": v.created_at,
                "changelog": v.changelog,
                "file_size": v.file_size,
            })
        
        # 确定显示名称
        display_name = doc_file.display_name if doc_file.display_name else doc_file.filename
        
        # 确保 cover_image 是完整的 API 路径
        cover = normalize_cover_image_path(doc_file.cover_image)

        # 构建响应数据（含前端 CardDetail 需要的所有字段）
        detail = {
            "id": doc_file.id,
            "display_name": display_name,
            "filename": doc_file.filename,
            "cover_image": cover,
            "description": doc_file.description,
            "file_type": doc_file.file_type,
            "project_id": doc_file.project_id,
            "version_count": len(version_list),
            "current_version": doc_file.current_version,
            "created_at": doc_file.created_at,
            "updated_at": doc_file.updated_at or doc_file.created_at,
            "tags": [],
            "category": "",
            "visit_count": 0,
            "download_count": 0,
            "versions": version_list,
        }
        
        card_logger.info(f"卡片详情查询成功: {card_id}, 版本数={len(version_list)}")
        return detail
        
    except HTTPException:
        raise
    except Exception as e:
        card_logger.error(f"获取卡片详情失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取卡片详情失败: {str(e)}"
        )


# 图片 magic bytes 签名（替代已弃用的 imghdr 模块）
_IMAGE_SIGNATURES = [
    (b'\xff\xd8\xff', 'jpeg'),        # JPEG
    (b'\x89PNG\r\n\x1a\n', 'png'),    # PNG
    (b'GIF87a', 'gif'),               # GIF (87a)
    (b'GIF89a', 'gif'),               # GIF (89a)
    (b'RIFF', 'webp'),                # WebP (需进一步验证)
]


def _detect_image_type(content: bytes):
    """通过 magic bytes 检测图片类型"""
    if len(content) < 12:
        return None
    for sig, img_type in _IMAGE_SIGNATURES:
        if content.startswith(sig):
            # WebP 需要额外验证: RIFF....WEBP
            if img_type == 'webp' and content[8:12] != b'WEBP':
                continue
            return img_type
    return None


def validate_image_file(file: UploadFile, content: bytes) -> str:
    """
    验证图片文件格式和大小
    
    Args:
        file: 上传的文件对象
        content: 文件内容字节
        
    Returns:
        str: 验证通过的文件扩展名
        
    Raises:
        HTTPException: 验证失败时抛出
    """
    # 检查文件大小
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图片大小超过限制，最大支持 {MAX_IMAGE_SIZE // (1024 * 1024)}MB"
        )
    
    # 检查文件类型（使用 magic bytes，替代已弃用的 imghdr）
    file_type = _detect_image_type(content)
    
    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法识别的图片格式"
        )
    
    if file_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式: {file_type}，仅支持: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    
    # 根据实际类型确定扩展名
    ext = "jpg" if file_type == "jpeg" else file_type
    return ext


def update_card_cover(
    db: Session,
    card_id: str,
    cover: UploadFile,
) -> dict:
    """
    更新卡片封面图片
    
    保存图片到指定目录，并更新数据库记录。
    
    Args:
        db: 数据库会话
        card_id: 卡片ID
        cover: 上传的图片文件
        
    Returns:
        dict: 包含封面路径的响应数据
        
    Raises:
        HTTPException: 卡片不存在或处理失败时抛出
    """
    card_logger.info(f"更新卡片封面: {card_id}")
    
    try:
        # 检查卡片是否存在
        doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
        if not doc_file:
            card_logger.warning(f"卡片不存在: {card_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 流式大小预检查：先读 Content-Length 头（如果存在）
        content_length = cover.headers.get("content-length")
        if content_length and int(content_length) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片大小超过限制，最大支持 {MAX_IMAGE_SIZE // (1024 * 1024)}MB"
            )
        
        # 读取文件内容（限制最大读取量以防内存耗尽）
        content = cover.file.read(MAX_IMAGE_SIZE + 1)
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片大小超过限制，最大支持 {MAX_IMAGE_SIZE // (1024 * 1024)}MB"
            )
        
        # 验证图片格式
        ext = validate_image_file(cover, content)
        
        # 构建保存路径: uploads/covers/{card_id}/{filename}
        data_root = Path(settings.UPLOAD_DIR).parent.resolve()
        cover_dir = data_root / "covers" / card_id
        cover_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"cover_{timestamp}.{ext}"
        cover_path = cover_dir / filename
        
        # 保存文件
        with open(cover_path, "wb") as f:
            f.write(content)
        
        # 删除旧封面（如果存在且不是默认封面）
        if doc_file.cover_image:
            old_cover_path = cover_image_to_disk_path(doc_file.cover_image)
            if old_cover_path and old_cover_path.exists() and str(old_cover_path).startswith(str(cover_dir)):
                try:
                    old_cover_path.unlink()
                    card_logger.debug(f"删除旧封面: {old_cover_path}")
                except Exception as e:
                    card_logger.warning(f"删除旧封面失败: {e}")
        
        # 更新数据库记录（存储 API 路径，方便前端直接使用）
        relative_path = str(cover_path.relative_to(data_root))
        cover_url = normalize_cover_image_path(relative_path)
        doc_file.cover_image = cover_url
        doc_file.updated_at = datetime.utcnow().isoformat() + "Z"
        db.commit()
        
        card_logger.info(f"封面更新成功: {card_id}, 路径={relative_path}")
        
        return {
            "card_id": card_id,
            "cover_image": cover_url,
            "cover_url": cover_url,
            "relative_path": relative_path.replace("\\", "/"),
            "original_filename": cover.filename,
            "file_size": len(content),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        card_logger.error(f"更新卡片封面失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新封面失败: {str(e)}"
        )


def update_card_info(
    db: Session,
    card_id: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """
    更新卡片信息（名称、介绍）
    
    Args:
        db: 数据库会话
        card_id: 卡片ID
        display_name: 显示名称（可选）
        description: 文件介绍（可选）
        
    Returns:
        dict: 更新后的卡片信息
        
    Raises:
        HTTPException: 卡片不存在或更新失败时抛出
    """
    card_logger.info(f"更新卡片信息: {card_id}")
    
    try:
        # 检查卡片是否存在
        doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
        if not doc_file:
            card_logger.warning(f"卡片不存在: {card_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 更新字段
        if display_name is not None:
            # 校验显示名称长度
            if len(display_name) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="显示名称长度不能超过255个字符"
                )
            doc_file.display_name = display_name
            card_logger.debug(f"更新显示名称: {display_name}")
        
        if description is not None:
            doc_file.description = description
            card_logger.debug(f"更新描述: {description}")
        
        # 更新时间戳
        doc_file.updated_at = datetime.utcnow().isoformat() + "Z"
        db.commit()
        db.refresh(doc_file)
        
        # 构建响应数据
        result = {
            "id": doc_file.id,
            "display_name": doc_file.display_name or doc_file.filename,
            "description": doc_file.description,
            "updated_at": doc_file.updated_at,
        }
        
        card_logger.info(f"卡片信息更新成功: {card_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        card_logger.error(f"更新卡片信息失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新卡片信息失败: {str(e)}"
        )


def compare_versions(
    db: Session,
    card_id: str,
    version_ids: List[str],
) -> dict:
    """
    多版本横向对比
    
    接收多个版本 ID，返回这些版本之间的差异对比。
    用于同时对比 v1, v2, v3 等多个版本。
    
    Args:
        db: 数据库会话
        card_id: 卡片ID
        version_ids: 要对比的版本ID列表
        
    Returns:
        dict: 对比结果数据
        
    Raises:
        HTTPException: 参数无效或对比失败时抛出
    """
    card_logger.info(f"多版本对比: {card_id}, 版本数={len(version_ids)}")
    
    try:
        # 参数校验
        if len(version_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要选择2个版本进行对比"
            )
        
        if len(version_ids) > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最多支持同时对比5个版本"
            )
        
        # 检查卡片是否存在
        doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
        if not doc_file:
            card_logger.warning(f"卡片不存在: {card_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 查询所有指定版本
        versions = db.query(FileVersion) \
                     .filter(FileVersion.id.in_(version_ids)) \
                     .filter(FileVersion.file_id == card_id) \
                     .order_by(FileVersion.version.asc()) \
                     .all()
        
        if len(versions) != len(version_ids):
            found_ids = {v.id for v in versions}
            missing_ids = set(version_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"以下版本不存在或不属于该卡片: {', '.join(missing_ids)}"
            )
        
        # 构建版本信息列表
        version_list = []
        for v in versions:
            version_list.append({
                "id": v.id,
                "version": v.version,
                "created_at": v.created_at,
                "changelog": v.changelog,
                "file_size": v.file_size,
            })
        
        # 执行两两对比
        compare_results = []
        for i in range(len(versions)):
            for j in range(i + 1, len(versions)):
                v_a = versions[i]
                v_b = versions[j]
                
                # 检查是否已有差异记录
                diff_record = db.query(DiffRecord) \
                                .filter(
                                    ((DiffRecord.old_version_id == v_a.id) & 
                                     (DiffRecord.new_version_id == v_b.id)) |
                                    ((DiffRecord.old_version_id == v_b.id) & 
                                     (DiffRecord.new_version_id == v_a.id))
                                ) \
                                .first()
                
                if not diff_record:
                    # 如果没有差异记录，尝试计算（旧版本作为基准）
                    try:
                        if v_a.version < v_b.version:
                            diff_record = compute_diff(v_a.id, v_b.id, db)
                        else:
                            diff_record = compute_diff(v_b.id, v_a.id, db)
                    except Exception as e:
                        card_logger.warning(f"计算差异失败: {v_a.id} vs {v_b.id}, 错误: {e}")
                        diff_record = None
                
                # 构建对比结果
                result = {
                    "version_a_id": v_a.id,
                    "version_a_number": v_a.version,
                    "version_b_id": v_b.id,
                    "version_b_number": v_b.version,
                    "has_diff": diff_record is not None,
                    "diff_summary": diff_record.summary if diff_record else None,
                }
                compare_results.append(result)
        
        # 构建响应数据
        response = {
            "card_id": card_id,
            "compared_versions": version_list,
            "compare_results": compare_results,
        }
        
        card_logger.info(f"多版本对比完成: {card_id}, 对比对数={len(compare_results)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        card_logger.error(f"多版本对比失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"版本对比失败: {str(e)}"
        )


def delete_card_cover(db: Session, card_id: str) -> bool:
    """
    删除卡片封面
    
    Args:
        db: 数据库会话
        card_id: 卡片ID
        
    Returns:
        bool: 删除成功返回 True
        
    Raises:
        HTTPException: 卡片不存在或删除失败时抛出
    """
    card_logger.info(f"删除卡片封面: {card_id}")
    
    try:
        # 检查卡片是否存在
        doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
        if not doc_file:
            card_logger.warning(f"卡片不存在: {card_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="卡片不存在"
            )
        
        # 删除封面文件
        if doc_file.cover_image:
            cover_path = cover_image_to_disk_path(doc_file.cover_image)
            if cover_path and cover_path.exists():
                try:
                    cover_path.unlink()
                    card_logger.debug(f"删除封面文件: {cover_path}")
                except Exception as e:
                    card_logger.warning(f"删除封面文件失败: {e}")
            
            # 清空数据库记录
            doc_file.cover_image = None
            doc_file.updated_at = datetime.utcnow().isoformat() + "Z"
            db.commit()
        
        card_logger.info(f"卡片封面删除成功: {card_id}")
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        card_logger.error(f"删除卡片封面失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除封面失败: {str(e)}"
        )
