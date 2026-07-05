"""
卡片式文档管理 API 路由模块

提供卡片式文件管理的 RESTful API，包括：
- 卡片列表查询（支持搜索、分页）
- 卡片详情获取
- 封面上传/修改
- 卡片信息更新
- 多版本横向对比
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.utils.time import utc_now, utc_now_iso
from app.config import settings
from app.database import get_db
from app.deps.auth import get_current_admin, get_current_user
from app.models.user import User
from app.models.access_log import AccessLog
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.schemas.response import ApiResponse
from app.schemas.card import (
    CardListItem,
    CardDetail,
    CardUpdateRequest,
    MultiVersionCompareRequest,
    CardListResponse,
    CoverUploadResponse,
)
from app.services.card_service import (
    get_cards_list,
    get_card_detail,
    normalize_cover_image_path,
    update_card_cover,
    update_card_info,
    compare_versions,
)
from app.services.storage_path_policy import is_allowed_storage_path
from app.utils.logger import logger, get_logger

# 获取模块日志器
card_router_logger = get_logger("routers.cards")

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


@router.get("", response_model=ApiResponse)
def get_cards(
    project_id: Optional[str] = Query(None, description="项目ID，用于筛选特定项目的卡片"),
    keyword: Optional[str] = Query(None, description="搜索关键词，匹配名称和描述"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，1-100"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取卡片列表
    
    返回卡片信息：id, display_name, cover_image, version_count, 
    updated_at, description, file_type
    
    支持按项目筛选和关键词搜索，结果按更新时间倒序排列。
    
    Args:
        project_id: 可选，项目ID用于筛选
        keyword: 可选，搜索关键词
        page: 页码，从1开始
        page_size: 每页数量
        
    Returns:
        ApiResponse: 包含分页卡片列表的响应
        
    Raises:
        HTTPException: 查询参数无效时抛出400错误
    """
    card_router_logger.info(
        f"获取卡片列表: project_id={project_id}, keyword={keyword}, "
        f"page={page}, page_size={page_size}, user={current_user.username}"
    )
    
    try:
        # 调用服务层获取卡片列表
        cards, total = get_cards_list(
            db=db,
            project_id=project_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        
        # 构建分页响应
        response_data = CardListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=cards,
        )
        
        card_router_logger.info(f"卡片列表查询成功: 总数={total}, 返回={len(cards)}")
        
        return ApiResponse(
            code=0,
            message="success",
            data=response_data.model_dump(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        card_router_logger.error(f"获取卡片列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取卡片列表失败: {str(e)}"
        )


# 静态路由必须在动态路由 /{card_id} 之前定义
@router.get("/categories", response_model=ApiResponse)
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.category import Category
    cats = db.query(Category).order_by(Category.name.asc()).all()
    items = [{"id": c.id, "name": c.name, "color": c.color} for c in cats]
    return ApiResponse(code=0, message="success", data={"categories": items})

def _escape_like(s: str) -> str:
    """Escape SQL LIKE special characters in user input."""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


@router.get("/tags", response_model=ApiResponse)
def get_tags(keyword: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.category import Tag
    q = db.query(Tag)
    if keyword:
        escaped = _escape_like(keyword)
        q = q.filter(Tag.name.ilike(f"%{escaped}%", escape='\\'))
    tags = q.order_by(Tag.name.asc()).all()
    items = [{"id": t.id, "name": t.name, "color": t.color} for t in tags]
    return ApiResponse(code=0, message="success", data={"tags": items})


@router.get("/{card_id}", response_model=ApiResponse)
def get_card_detail_endpoint(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取卡片详情
    
    包含：文件信息 + 所有版本列表（version, created_at, changelog, file_size）
    
    Args:
        card_id: 卡片ID
        
    Returns:
        ApiResponse: 包含卡片详情的响应
        
    Raises:
        HTTPException: 卡片不存在时抛出404错误
    """
    card_router_logger.info(f"获取卡片详情: card_id={card_id}, user={current_user.username}")
    
    try:
        # 调用服务层获取卡片详情
        detail = get_card_detail(db=db, card_id=card_id)
        
        card_router_logger.info(f"卡片详情查询成功: {card_id}")
        
        return ApiResponse(
            code=0,
            message="success",
            data=detail,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        card_router_logger.error(f"获取卡片详情失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取卡片详情失败: {str(e)}"
        )


@router.post("/{card_id}/cover", response_model=ApiResponse)
def upload_card_cover(
    card_id: str,
    cover: UploadFile = File(..., description="封面图片文件，支持 jpg/png/gif/webp 格式，最大5MB"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    上传/修改卡片封面图片
    
    上传新的封面图片，自动替换旧封面。仅管理员可操作。
    
    Args:
        card_id: 卡片ID
        cover: 封面图片文件
        
    Returns:
        ApiResponse: 包含上传后封面路径的响应
        
    Raises:
        HTTPException: 
            - 403: 非管理员用户
            - 404: 卡片不存在
            - 400: 图片格式或大小不符合要求
    """
    card_router_logger.info(
        f"上传卡片封面: card_id={card_id}, filename={cover.filename}, "
        f"admin={current_user.username}"
    )
    
    try:
        # 调用服务层更新封面
        result = update_card_cover(
            db=db,
            card_id=card_id,
            cover=cover,
        )
        
        card_router_logger.info(f"卡片封面上传成功: {card_id}")
        
        return ApiResponse(
            code=0,
            message="封面上传成功",
            data=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        card_router_logger.error(f"上传卡片封面失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传封面失败: {str(e)}"
        )


@router.put("/{card_id}/info", response_model=ApiResponse)
def update_card_info_endpoint(
    card_id: str,
    body: Optional[dict] = Body(None),
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    修改卡片信息（名称、介绍）

    更新卡片的显示名称和描述信息。仅管理员可操作。

    Args:
        card_id: 卡片ID
        display_name: 可选，新的显示名称
        description: 可选，新的文件介绍

    Returns:
        ApiResponse: 包含更新后卡片信息的响应

    Raises:
        HTTPException:
            - 403: 非管理员用户
            - 404: 卡片不存在
            - 400: 参数无效
    """
    if isinstance(body, dict):
        display_name = body.get("display_name", display_name)
        description = body.get("description", description)
    card_router_logger.info(
        f"更新卡片信息: card_id={card_id}, display_name={display_name}, "
        f"admin={current_user.username}"
    )
    
    try:
        # 调用服务层更新卡片信息
        result = update_card_info(
            db=db,
            card_id=card_id,
            display_name=display_name,
            description=description,
        )
        
        card_router_logger.info(f"卡片信息更新成功: {card_id}")
        
        return ApiResponse(
            code=0,
            message="卡片信息更新成功",
            data=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        card_router_logger.error(f"更新卡片信息失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新卡片信息失败: {str(e)}"
        )


@router.post("/{card_id}/versions/compare", response_model=ApiResponse)
def compare_multiple_versions(
    card_id: str,
    request: MultiVersionCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    多版本横向对比
    
    接收多个版本 ID，返回这些版本之间的差异对比。
    用于同时对比 v1, v2, v3 等多个版本。
    
    支持2-5个版本同时对比，系统会自动计算版本之间的两两差异。
    
    Args:
        card_id: 卡片ID
        request: 包含版本ID列表的请求体
            - version_ids: 要对比的版本ID列表（至少2个，最多5个）
        
    Returns:
        ApiResponse: 包含对比结果的响应
            - card_id: 卡片ID
            - compared_versions: 参与对比的版本列表
            - compare_results: 两两对比结果列表
        
    Raises:
        HTTPException:
            - 404: 卡片不存在或版本不存在
            - 400: 版本数量不符合要求（<2 或 >5）
    """
    version_ids = request.version_ids
    
    card_router_logger.info(
        f"多版本对比: card_id={card_id}, version_ids={version_ids}, "
        f"user={current_user.username}"
    )
    
    try:
        # 调用服务层执行多版本对比
        result = compare_versions(
            db=db,
            card_id=card_id,
            version_ids=version_ids,
        )
        
        card_router_logger.info(f"多版本对比成功: {card_id}, 对比对数={len(result.get('compare_results', []))}")
        
        return ApiResponse(
            code=0,
            message="版本对比成功",
            data=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        card_router_logger.error(f"多版本对比失败: {card_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"版本对比失败: {str(e)}"
        )


# ===== 排行榜与下载端点 =====

def _rank_period_start(period: Optional[str]) -> Optional[str]:
    """Return an ISO timestamp lower bound for rank periods."""
    normalized = (period or "all").lower()
    if normalized == "all":
        return None

    now = utc_now().replace(microsecond=0)
    if normalized in {"day", "today"}:
        start = now.replace(hour=0, minute=0, second=0)
    elif normalized == "week":
        start = now - timedelta(days=7)
    elif normalized == "month":
        start = now - timedelta(days=30)
    else:
        return None
    return start.isoformat() + "Z"


def _version_counts_for_files(db: Session, file_ids: list[str]) -> dict[str, int]:
    if not file_ids:
        return {}
    rows = (
        db.query(FileVersion.file_id, func.count(FileVersion.id))
        .filter(FileVersion.file_id.in_(file_ids))
        .group_by(FileVersion.file_id)
        .all()
    )
    return {row[0]: row[1] for row in rows}


def _access_log_counts(
    db: Session,
    actions: list[str],
    period: Optional[str],
    limit: int,
) -> list[tuple[str, int]]:
    query = (
        db.query(AccessLog.target_id, func.count(AccessLog.id).label("count"))
        .filter(
            AccessLog.is_deleted == 0,
            AccessLog.target_type.in_(["file", "share_file"]),
            AccessLog.target_id.isnot(None),
            AccessLog.action_type.in_(actions),
        )
    )
    start = _rank_period_start(period)
    if start:
        query = query.filter(AccessLog.timestamp >= start)

    return (
        query.group_by(AccessLog.target_id)
        .order_by(desc("count"))
        .limit(limit)
        .all()
    )


def _rank_cards_from_counts(
    db: Session,
    rows: list[tuple[str, int]],
    count_field: str,
) -> list[dict]:
    file_ids = [row[0] for row in rows if row[0]]
    if not file_ids:
        return []

    files = db.query(DocumentFile).filter(DocumentFile.id.in_(file_ids)).all()
    file_by_id = {f.id: f for f in files}
    version_counts = _version_counts_for_files(db, file_ids)

    cards = []
    for file_id, count in rows:
        f = file_by_id.get(file_id)
        if not f:
            continue
        item = {
            "id": f.id,
            "display_name": f.display_name or f.filename,
            "filename": f.filename,
            "file_type": f.file_type,
            "cover_image": normalize_cover_image_path(f.cover_image),
            count_field: int(count or 0),
            "version_count": version_counts.get(f.id, 0),
            "updated_at": f.updated_at or f.created_at,
        }
        cards.append(item)
    return cards

@router.get("/rank/download", response_model=ApiResponse)
def get_download_rank(
    limit: Optional[int] = Query(20, ge=1, le=100),
    period: Optional[str] = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取下载排行榜（按下载量降序）"""
    rows = _access_log_counts(db, ["download"], period, limit)
    return ApiResponse(
        code=0,
        message="success",
        data=_rank_cards_from_counts(db, rows, "download_count"),
    )


@router.get("/rank/visit", response_model=ApiResponse)
def get_visit_rank(
    limit: Optional[int] = Query(20, ge=1, le=100),
    period: Optional[str] = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取访问排行榜（按访问量降序）"""
    rows = _access_log_counts(db, ["view", "preview"], period, limit)
    return ApiResponse(
        code=0,
        message="success",
        data=_rank_cards_from_counts(db, rows, "visit_count"),
    )


@router.post("/{card_id}/visit", response_model=ApiResponse)
def record_card_visit(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录一次卡片查看行为。真实访问日志由 TrackingMiddleware 写入。"""
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return ApiResponse(code=0, message="success", data={"id": card_id})


@router.get("/{card_id}/download", response_model=None)
def download_card(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载卡片最新版本文件"""
    from fastapi.responses import FileResponse
    from app.models.file_version import FileVersion

    doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="卡片不存在")

    # 增加下载计数
    doc_file.download_count = (doc_file.download_count or 0) + 1
    db.commit()

    latest = (
        db.query(FileVersion)
        .filter(FileVersion.file_id == card_id)
        .order_by(FileVersion.version.desc())
        .first()
    )
    if not latest or not os.path.exists(latest.storage_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    real_path = os.path.realpath(latest.storage_path)
    if not is_allowed_storage_path(real_path):
        raise HTTPException(status_code=404, detail="File not found")

    from fastapi.responses import FileResponse as FastAPIFileResponse
    from urllib.parse import quote
    safe_name = quote(doc_file.filename)
    return FastAPIFileResponse(
        path=latest.storage_path,
        filename=doc_file.filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除卡片及其所有版本文件和封面"""
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == card_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="卡片不存在")

    from app.models.file_version import FileVersion
    from app.services.card_service import delete_card_cover

    # 删除封面文件
    delete_card_cover(db, card_id)

    # 收集所有版本的存储路径
    versions = db.query(FileVersion).filter(FileVersion.file_id == card_id).all()
    storage_paths = [v.storage_path for v in versions]

    # 保存需要的属性值，避免 commit 后 SQLAlchemy expire
    project_id = doc_file.project_id
    file_id = doc_file.id

    # 删除数据库记录
    db.delete(doc_file)
    db.commit()

    # 清理磁盘文件
    import shutil
    for sp in storage_paths:
        real_path = os.path.realpath(sp or "")
        if not real_path or not is_allowed_storage_path(real_path):
            card_router_logger.warning(f"skip deleting storage outside allowed roots: {sp}")
            continue
        if os.path.exists(real_path):
            try:
                os.remove(real_path)
            except OSError:
                pass

    file_dir = os.path.join(settings.UPLOAD_DIR, project_id, file_id)
    file_dir_real_path = os.path.realpath(file_dir)
    if is_allowed_storage_path(file_dir_real_path) and os.path.isdir(file_dir_real_path):
        try:
            shutil.rmtree(file_dir_real_path)
        except OSError:
            pass
    elif os.path.isdir(file_dir):
        card_router_logger.warning(f"skip deleting directory outside allowed roots: {file_dir}")

    return None
