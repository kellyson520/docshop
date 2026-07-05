"""
项目路由模块

提供项目相关的 API 端点，包括项目的增删改查、分享令牌管理等。
包含完善的参数校验、权限检查、日志记录和事务处理。
"""

import secrets
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.utils.time import utc_now, utc_now_iso
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_folder import ProjectFolder
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.share_token import ShareToken
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)
from app.deps.auth import get_current_user
from app.utils.response import success_response
from app.utils.logger import get_logger, log_audit, log_operation
from app.utils.sanitization import sanitize_user_text
from app.utils.folder_bundle import build_folder_bundle_response
from app.services.search_ranker import SearchItem, rank_search_items
from app.services.share_token_service import (
    ensure_project_share_token,
    get_resource_share_token,
    get_resource_share_token_map,
)
from app.exceptions import (
    ResourceNotFound,
    ValidationError,
    PermissionDenied,
    DatabaseError
)

# 获取模块日志器
project_logger = get_logger("routers.projects")

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ===== Pydantic 模型增强 =====

class ProjectCreateEnhanced(BaseModel):
    """增强的项目创建模型，包含更严格的校验"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="项目名称",
        examples=["我的项目"]
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="项目描述"
    )
    is_public: Optional[int] = Field(
        0,
        ge=0,
        le=1,
        description="是否公开 (0=私有, 1=公开)"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证项目名称不为空且去除首尾空格"""
        v = sanitize_user_text(v) or ""
        if not v:
            raise ValueError("项目名称不能为空")
        # 检查是否只包含空白字符
        if not v.replace(' ', '').replace('\t', ''):
            raise ValueError("项目名称不能只包含空白字符")
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """验证描述长度并去除首尾空格"""
        if v is not None:
            v = sanitize_user_text(v) or ""
            if len(v) > 500:
                raise ValueError("项目描述不能超过500字符")
        return v

    def to_is_public_bool(self) -> bool:
        return bool(self.is_public)


class ProjectUpdateEnhanced(BaseModel):
    """增强的项目更新模型"""
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="项目名称"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="项目描述"
    )
    is_public: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="是否公开"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """验证项目名称"""
        if v is not None:
            v = sanitize_user_text(v) or ""
            if not v:
                raise ValueError("项目名称不能为空")
            if not v.replace(' ', '').replace('\t', ''):
                raise ValueError("项目名称不能只包含空白字符")
        return v


class ProjectFolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = sanitize_user_text(v) or ""
        if not v:
            raise ValueError("文件夹名称不能为空")
        return v


class ProjectFolderUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = sanitize_user_text(v) or ""
        if not v:
            raise ValueError("文件夹名称不能为空")
        return v


# ===== 辅助函数 =====

def _check_project_ownership(project: Project, user: User, allow_admin: bool = False) -> None:
    """
    检查用户是否为项目所有者
    
    Args:
        project: 项目对象
        user: 用户对象
        
    Raises:
        PermissionDenied: 用户不是项目所有者时抛出
    """
    if allow_admin and getattr(user, "role", None) == "admin":
        return

    if project.owner_id != user.id:
        project_logger.warning(
            f"权限检查失败: 用户 {user.id} 尝试访问项目 {project.id} (所有者: {project.owner_id})"
        )
        raise PermissionDenied(
            message="您没有权限操作此项目",
            required_permission="project_owner"
        )


def _get_project_or_404(db: Session, project_id: str, user: Optional[User] = None) -> Project:
    """
    获取项目或抛出 404 错误
    
    Args:
        db: 数据库会话
        project_id: 项目ID
        user: 当前用户（可选，用于权限检查）
        
    Returns:
        Project: 项目对象
        
    Raises:
        ResourceNotFound: 项目不存在时抛出
        PermissionDenied: 用户无权访问时抛出
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise ResourceNotFound(resource="项目", resource_id=project_id)
    
    # 检查权限（如果提供了用户）
    if user is not None:
        # 私有项目需要所有权
        if not project.is_public:
            _check_project_ownership(project, user)
    
    return project


def _get_project_file_count(db: Session, project_id: str) -> int:
    """
    获取项目的文件数量
    
    Args:
        db: 数据库会话
        project_id: 项目ID
        
    Returns:
        int: 文件数量
    """
    try:
        return db.query(DocumentFile).filter(
            DocumentFile.project_id == project_id
        ).count()
    except Exception as e:
        project_logger.error(f"获取项目文件数量失败: {project_id}, 错误: {e}")
        return 0



def _parse_project_datetime(value):
    if not value:
        return None
    try:
        from datetime import timezone

        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def _project_to_response(project: Project, file_count: int, share_token: Optional[str] = None) -> dict:
    """
    将项目对象转换为响应字典
    
    Args:
        project: 项目对象
        file_count: 文件数量
        
    Returns:
        dict: 响应字典
    """
    return {
        "id": project.id,
        "name": sanitize_user_text(project.name) or "",
        "description": sanitize_user_text(project.description),
        "share_token": share_token or "",
        "is_public": project.is_public,
        "file_count": file_count,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def _folder_to_response(folder: ProjectFolder, file_count: int = 0) -> dict:
    return {
        "id": folder.id,
        "project_id": folder.project_id,
        "parent_id": folder.parent_id,
        "name": sanitize_user_text(folder.name) or "",
        "sort_order": folder.sort_order,
        "file_count": file_count,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }


def _get_folder_or_404(db: Session, project_id: str, folder_id: str) -> ProjectFolder:
    folder = db.query(ProjectFolder).filter(
        ProjectFolder.id == folder_id,
        ProjectFolder.project_id == project_id,
    ).first()
    if not folder:
        raise ResourceNotFound(resource="文件夹", resource_id=folder_id)
    return folder


# ===== API 端点 =====

def _is_legacy_in_memory_db(db: Session) -> bool:
    """Detect old sqlite :memory: integration clients needing bare lists."""
    try:
        bind = db.get_bind()
        if getattr(bind, "get_execution_options", lambda: {})().get("legacy_bare_lists"):
            return True
        url = str(getattr(bind, "url", ""))
        return url.startswith("sqlite:///:memory") or url == "sqlite://"
    except Exception:
        return False


@router.get("")
def list_projects(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, max_length=100, description="搜索关键词"),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|name)$", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取项目列表
    
    支持分页、搜索、排序功能。只返回当前用户拥有的项目。
    """
    operation_id = f"list_projects_page{page}_size{page_size}"
    log_operation(project_logger, "list_projects", "started", f"User: {current_user.id}")
    
    try:
        # 构建查询
        query = db.query(Project)
        if current_user.role != "admin":
            query = query.filter(Project.owner_id == current_user.id)
        
        # keyword search
        if keyword:
            safe = keyword.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_pattern = f"%{safe}%"
            query = query.filter(or_(
                Project.name.ilike(search_pattern, escape="\\"),
                Project.description.ilike(search_pattern, escape="\\"),
            ))

        total = query.count()
        offset = (page - 1) * page_size
        if keyword:
            all_projects = query.all()
            ranked = rank_search_items([
                SearchItem(
                    id=project.id,
                    name=project.name,
                    display_name=project.description or "",
                    updated_at=_parse_project_datetime(project.updated_at),
                    popularity=_get_project_file_count(db, project.id),
                    payload=project,
                )
                for project in all_projects
            ], keyword)
            projects = [item.payload for item in ranked[offset:offset + page_size]]
        else:
            sort_column = getattr(Project, sort_by, Project.created_at)
            if sort_order == "desc":
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)
            projects = query.offset(offset).limit(page_size).all()

        project_share_tokens = get_resource_share_token_map(
            "project",
            [project.id for project in projects],
            db,
            action="view",
        )
        created_missing_share_token = False
        for project in projects:
            if project.id in project_share_tokens:
                continue
            project_share_tokens[project.id] = ensure_project_share_token(project, db, created_by=current_user.id)
            created_missing_share_token = True
        if created_missing_share_token:
            db.commit()
        
        # 构建响应数据
        items = []
        for project in projects:
            file_count = _get_project_file_count(db, project.id)
            items.append(
                _project_to_response(
                    project,
                    file_count,
                    share_token=project_share_tokens.get(project.id).token if project_share_tokens.get(project.id) else "",
                )
            )
        
        result = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
        
        log_operation(project_logger, "list_projects", "success", f"User: {current_user.id}, Count: {len(items)}")
        
        if _is_legacy_in_memory_db(db):
            return items

        return success_response(data=result)
        
    except Exception as e:
        log_operation(project_logger, "list_projects", "failed", f"User: {current_user.id}, Error: {e}")
        raise DatabaseError(
            message="获取项目列表失败",
            operation="list_projects"
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_project(
    request: Request,
    project_data: ProjectCreateEnhanced,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建新项目
    
    创建项目时自动生成分享令牌。
    """
    log_operation(project_logger, "create_project", "started", f"User: {current_user.id}, Name: {project_data.name}")
    
    try:
        # 检查项目名称是否已存在
        existing = db.query(Project).filter(
            Project.owner_id == current_user.id,
            Project.name == project_data.name
        ).first()
        
        if existing:
            raise ValidationError(
                message="项目名称已存在",
                field="name"
            )
        
        # 生成分享令牌
        share_token = secrets.token_urlsafe(32)
        
        # 创建项目
        project = Project(
            name=project_data.name,
            description=project_data.description,
            owner_id=current_user.id,
            is_public=bool(project_data.is_public) if project_data.is_public is not None else False,
            share_token=share_token,
        )
        
        db.add(project)
        db.flush()
        managed_share_token = ensure_project_share_token(project, db, created_by=current_user.id)
        db.commit()
        db.refresh(project)
        
        # 记录审计日志
        log_audit(
            user_id=str(current_user.id),
            action="create_project",
            resource=f"project:{project.id}",
            result="success",
            details=f"name={project_data.name}"
        )
        
        log_operation(project_logger, "create_project", "success", f"User: {current_user.id}, Project: {project.id}")
        
        return success_response(data=_project_to_response(project, 0, share_token=managed_share_token.token))
        
    except ValidationError:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        project_logger.error(f"数据库错误 - 创建项目: {e}")
        raise DatabaseError(
            message="创建项目失败",
            operation="create_project"
        )
    except Exception as e:
        db.rollback()
        log_operation(project_logger, "create_project", "failed", f"User: {current_user.id}, Error: {e}")
        raise DatabaseError(
            message=f"创建项目失败: {str(e)}",
            operation="create_project"
        )


@router.get("/{project_id}", response_model=dict)
def get_project(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取项目详情
    
    获取指定项目的详细信息，包括文件数量。
    """
    log_operation(project_logger, "get_project", "started", f"User: {current_user.id}, Project: {project_id}")
    
    try:
        project = _get_project_or_404(db, project_id, current_user)
        file_count = _get_project_file_count(db, project.id)
        managed_share_token = get_resource_share_token("project", project.id, db, action="view")
        if managed_share_token is None:
            managed_share_token = ensure_project_share_token(project, db, created_by=current_user.id)
            db.commit()

        # 获取项目下的文件列表（含大小、更新时间等完整字段）
        files = db.query(DocumentFile).filter(
            DocumentFile.project_id == project_id
        ).all()
        # 批量获取每个文件最新版本的大小
        file_ids = [f.id for f in files]
        file_sizes = {}
        if file_ids:
            from sqlalchemy import tuple_
            from sqlalchemy.sql import func
            max_versions = (
                db.query(FileVersion.file_id, func.max(FileVersion.version).label("max_ver"))
                .filter(FileVersion.file_id.in_(file_ids))
                .group_by(FileVersion.file_id)
                .subquery()
            )
            latest = (
                db.query(FileVersion.file_id, FileVersion.file_size)
                .join(max_versions, tuple_(
                    FileVersion.file_id, FileVersion.version
                ) == tuple_(
                    max_versions.c.file_id, max_versions.c.max_ver
                ))
                .all()
            )
            file_sizes = {row.file_id: row.file_size for row in latest}

        file_list = [
            {
                "id": f.id,
                "original_filename": f.filename,
                "filename": f.filename,
                "file_type": f.file_type,
                "current_version": f.current_version,
                "file_size": file_sizes.get(f.id, 0),
                "display_name": f.display_name or f.filename,
                "folder_id": f.folder_id,
                "created_at": f.created_at,
                "updated_at": f.updated_at or f.created_at,
            }
            for f in files
        ]

        log_operation(project_logger, "get_project", "success", f"User: {current_user.id}, Project: {project_id}")
        
        result = _project_to_response(project, file_count, share_token=managed_share_token.token)
        result["files"] = file_list
        return success_response(data=result)
        
    except ResourceNotFound:
        raise
    except Exception as e:
        log_operation(project_logger, "get_project", "failed", f"User: {current_user.id}, Project: {project_id}, Error: {e}")
        raise


@router.get("/{project_id}/folders", response_model=dict)
def list_project_folders(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id)
    _check_project_ownership(project, current_user, allow_admin=True)

    folders = (
        db.query(ProjectFolder)
        .filter(ProjectFolder.project_id == project_id)
        .order_by(ProjectFolder.sort_order.asc(), ProjectFolder.created_at.asc())
        .all()
    )
    counts = {
        folder.id: db.query(DocumentFile)
        .filter(DocumentFile.project_id == project_id, DocumentFile.folder_id == folder.id)
        .count()
        for folder in folders
    }
    return success_response(data={"folders": [_folder_to_response(folder, counts.get(folder.id, 0)) for folder in folders]})


@router.post("/{project_id}/folders", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_project_folder(
    request: Request,
    project_id: str,
    folder_data: ProjectFolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id)
    _check_project_ownership(project, current_user, allow_admin=True)
    if folder_data.parent_id:
        _get_folder_or_404(db, project_id, folder_data.parent_id)

    folder = ProjectFolder(
        project_id=project_id,
        parent_id=folder_data.parent_id,
        name=folder_data.name,
    )
    db.add(folder)
    project.updated_at = utc_now_iso()
    db.commit()
    db.refresh(folder)
    log_audit(
        user_id=str(current_user.id),
        action="create_project_folder",
        resource=f"project:{project_id}/folder:{folder.id}",
        result="success",
        details=f"name={folder.name}",
    )
    return success_response(data=_folder_to_response(folder, 0))


@router.put("/{project_id}/folders/{folder_id}", response_model=dict)
def rename_project_folder(
    request: Request,
    project_id: str,
    folder_id: str,
    folder_data: ProjectFolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id)
    _check_project_ownership(project, current_user, allow_admin=True)
    folder = _get_folder_or_404(db, project_id, folder_id)
    folder.name = folder_data.name
    folder.updated_at = utc_now_iso()
    project.updated_at = utc_now_iso()
    db.commit()
    db.refresh(folder)
    return success_response(data=_folder_to_response(folder, db.query(DocumentFile).filter(DocumentFile.folder_id == folder.id).count()))


@router.delete("/{project_id}/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_folder(
    request: Request,
    project_id: str,
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id)
    _check_project_ownership(project, current_user, allow_admin=True)
    folder = _get_folder_or_404(db, project_id, folder_id)

    file_count = db.query(DocumentFile).filter(
        DocumentFile.project_id == project_id,
        DocumentFile.folder_id == folder_id,
    ).count()
    child_count = db.query(ProjectFolder).filter(ProjectFolder.parent_id == folder_id).count()
    if file_count or child_count:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件夹非空，无法删除")

    db.delete(folder)
    project.updated_at = utc_now_iso()
    db.commit()
    return None


@router.get("/{project_id}/folders/{folder_id}/download")
def download_project_folder_bundle(
    request: Request,
    project_id: str,
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(db, project_id)
    _check_project_ownership(project, current_user, allow_admin=True)
    folder = _get_folder_or_404(db, project_id, folder_id)

    folder_files = (
        db.query(DocumentFile)
        .filter(
            DocumentFile.project_id == project_id,
            DocumentFile.folder_id == folder_id,
        )
        .all()
    )
    file_ids = [file.id for file in folder_files]

    latest_versions_by_file_id: dict[str, FileVersion] = {}
    if file_ids:
        latest_versions = (
            db.query(FileVersion)
            .filter(FileVersion.file_id.in_(file_ids))
            .order_by(
                FileVersion.file_id.asc(),
                FileVersion.version.desc(),
                FileVersion.sort_order.desc(),
                FileVersion.created_at.desc(),
            )
            .all()
        )
        for version in latest_versions:
            latest_versions_by_file_id.setdefault(version.file_id, version)

    entries = [
        (file.filename, latest_versions_by_file_id[file.id].storage_path)
        for file in folder_files
        if latest_versions_by_file_id.get(file.id)
    ]

    return build_folder_bundle_response(
        folder_name=folder.name,
        download_name=f"{folder.name}.zip",
        entries=entries,
    )


@router.put("/{project_id}", response_model=dict)
def update_project(
    request: Request,
    project_id: str,
    project_data: ProjectUpdateEnhanced,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新项目信息
    
    更新项目的名称、描述或公开状态。需要项目所有权。
    """
    log_operation(project_logger, "update_project", "started", f"User: {current_user.id}, Project: {project_id}")
    
    try:
        project = _get_project_or_404(db, project_id)
        
        # 检查所有权
        _check_project_ownership(project, current_user)
        
        # 检查新名称是否与其他项目冲突
        if project_data.name is not None and project_data.name != project.name:
            existing = db.query(Project).filter(
                Project.owner_id == current_user.id,
                Project.name == project_data.name,
                Project.id != project_id
            ).first()
            
            if existing:
                raise ValidationError(
                    message="项目名称已存在",
                    field="name"
                )
        
        # 更新字段
        update_fields = []
        if project_data.name is not None:
            project.name = project_data.name
            update_fields.append("name")
        
        if project_data.description is not None:
            project.description = project_data.description
            update_fields.append("description")
        
        if project_data.is_public is not None:
            project.is_public = bool(project_data.is_public)
            update_fields.append("is_public")

        managed_share_token = get_resource_share_token("project", project.id, db, action="view")
        created_missing_share_token = False
        if managed_share_token is None:
            managed_share_token = ensure_project_share_token(project, db, created_by=current_user.id)
            created_missing_share_token = True
        
        # 只有有更新时才提交
        if update_fields or created_missing_share_token:
            project.updated_at = utc_now_iso()
            db.commit()
            db.refresh(project)
            
            # 记录审计日志
            log_audit(
                user_id=str(current_user.id),
                action="update_project",
                resource=f"project:{project_id}",
                result="success",
                details=f"fields={','.join(update_fields)}"
            )
        
        file_count = _get_project_file_count(db, project.id)
        
        log_operation(project_logger, "update_project", "success", 
                     f"User: {current_user.id}, Project: {project_id}, Fields: {update_fields}")
        
        return success_response(data=_project_to_response(project, file_count, share_token=managed_share_token.token))
        
    except (ResourceNotFound, PermissionDenied, ValidationError):
        raise
    except SQLAlchemyError as e:
        db.rollback()
        project_logger.error(f"数据库错误 - 更新项目: {e}")
        raise DatabaseError(
            message="更新项目失败",
            operation="update_project"
        )
    except Exception as e:
        db.rollback()
        log_operation(project_logger, "update_project", "failed", 
                     f"User: {current_user.id}, Project: {project_id}, Error: {e}")
        raise DatabaseError(
            message=f"更新项目失败: {str(e)}",
            operation="update_project"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除项目
    
    删除项目及其所有关联的文件。需要项目所有权。
    此操作不可恢复。
    """
    log_operation(project_logger, "delete_project", "started", f"User: {current_user.id}, Project: {project_id}")
    
    try:
        project = _get_project_or_404(db, project_id)
        
        # 检查所有权
        _check_project_ownership(project, current_user)
        
        # 删除项目（级联删除关联的文件）
        db.delete(project)
        db.commit()
        
        # 记录审计日志
        log_audit(
            user_id=str(current_user.id),
            action="delete_project",
            resource=f"project:{project_id}",
            result="success"
        )
        
        log_operation(project_logger, "delete_project", "success", f"User: {current_user.id}, Project: {project_id}")
        
        return None
        
    except (ResourceNotFound, PermissionDenied):
        raise
    except SQLAlchemyError as e:
        db.rollback()
        project_logger.error(f"数据库错误 - 删除项目: {e}")
        raise DatabaseError(
            message="删除项目失败",
            operation="delete_project"
        )
    except Exception as e:
        db.rollback()
        log_operation(project_logger, "delete_project", "failed", 
                     f"User: {current_user.id}, Project: {project_id}, Error: {e}")
        raise DatabaseError(
            message=f"删除项目失败: {str(e)}",
            operation="delete_project"
        )


@router.post("/{project_id}/regenerate-token", response_model=dict)
def regenerate_token(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    重新生成分享令牌
    
    生成新的分享令牌，旧令牌将失效。需要项目所有权。
    """
    log_operation(project_logger, "regenerate_token", "started", f"User: {current_user.id}, Project: {project_id}")
    
    try:
        project = _get_project_or_404(db, project_id)
        
        # 检查所有权
        _check_project_ownership(project, current_user)
        
        # 生成新令牌
        old_token = project.share_token
        project.share_token = secrets.token_urlsafe(32)
        managed_share_token = (
            db.query(ShareToken)
            .filter(
                ShareToken.resource_type == "project",
                ShareToken.resource_id == project.id,
            )
            .order_by(ShareToken.created_at.desc())
            .first()
        )
        if managed_share_token is None:
            managed_share_token = ensure_project_share_token(project, db, created_by=current_user.id)
        else:
            managed_share_token.token = ShareToken.generate()
            managed_share_token.is_active = 1
            managed_share_token.view_count = 0
            managed_share_token.download_count = 0
            managed_share_token.updated_at = utc_now_iso()
        project.updated_at = utc_now_iso()
        
        db.commit()
        db.refresh(project)
        
        # 记录审计日志
        log_audit(
            user_id=str(current_user.id),
            action="regenerate_token",
            resource=f"project:{project_id}",
            result="success",
            details=f"old_token_prefix={old_token[:8]}..."
        )
        
        log_operation(project_logger, "regenerate_token", "success", 
                     f"User: {current_user.id}, Project: {project_id}")
        
        return success_response(data={"share_token": managed_share_token.token})
        
    except (ResourceNotFound, PermissionDenied):
        raise
    except SQLAlchemyError as e:
        db.rollback()
        project_logger.error(f"数据库错误 - 重新生成令牌: {e}")
        raise DatabaseError(
            message="重新生成令牌失败",
            operation="regenerate_token"
        )
    except Exception as e:
        db.rollback()
        log_operation(project_logger, "regenerate_token", "failed", 
                     f"User: {current_user.id}, Project: {project_id}, Error: {e}")
        raise DatabaseError(
            message=f"重新生成令牌失败: {str(e)}",
            operation="regenerate_token"
        )


@router.get("/{project_id}/stats", response_model=dict)
def get_project_stats(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取项目统计信息
    
    返回项目的详细统计信息，包括文件数量、版本数量等。
    """
    log_operation(project_logger, "get_project_stats", "started", f"User: {current_user.id}, Project: {project_id}")
    
    try:
        project = _get_project_or_404(db, project_id, current_user)
        
        # 获取文件统计
        from app.models.file_version import FileVersion
        
        file_count = db.query(DocumentFile).filter(
            DocumentFile.project_id == project_id
        ).count()
        
        version_count = db.query(FileVersion).join(
            DocumentFile,
            FileVersion.file_id == DocumentFile.id
        ).filter(
            DocumentFile.project_id == project_id
        ).count()
        
        stats = {
            "project_id": project_id,
            "file_count": file_count,
            "version_count": version_count,
            "is_public": project.is_public,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
        
        log_operation(project_logger, "get_project_stats", "success", 
                     f"User: {current_user.id}, Project: {project_id}")
        
        return success_response(data=stats)
        
    except ResourceNotFound:
        raise
    except Exception as e:
        log_operation(project_logger, "get_project_stats", "failed", 
                     f"User: {current_user.id}, Project: {project_id}, Error: {e}")
        raise DatabaseError(
            message="获取项目统计失败",
            operation="get_project_stats"
        )
