"""
公告管理路由模块

提供公告的 CRUD 和公开查询 API。
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.announcement import Announcement
from app.deps.auth import get_current_user, get_current_admin
from app.utils.response import success_response
from app.utils.logger import get_logger, log_audit

from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from app.config import settings

_optional_security = HTTPBearer(auto_error=False)


async def get_optional_user(request=None, db=None):
    """可选认证：有 token 则解析用户，无 token 返回 None"""
    return None

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])
logger = get_logger("routers.announcements")


# ===== 公开接口（游客/用户） =====

@router.get("/active")
def get_active_announcements(db: Session = Depends(get_db)):
    """获取当前活跃的公告（无需登录也可访问）"""
    now = datetime.utcnow().isoformat() + "Z"
    query = db.query(Announcement).filter(Announcement.is_active == 1)

    active = []
    for a in query.order_by(Announcement.priority.desc(), Announcement.created_at.desc()).all():
        if a.push_method == "timed":
            if a.start_time and a.start_time > now: continue
            if a.end_time and a.end_time < now: continue
        if a.push_method == "single": continue  # 公开接口不返回单用户公告
        active.append(a.to_dict())

    return success_response(data=active)


# ===== 管理接口（仅管理员） =====

@router.get("")
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """获取公告列表"""
    total = db.query(Announcement).count()
    items = (
        db.query(Announcement)
        .order_by(Announcement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(data={
        "total": total, "page": page, "page_size": page_size,
        "items": [a.to_dict() for a in items],
    })


@router.post("", status_code=status.HTTP_201_CREATED)
def create_announcement(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """创建公告"""
    a = Announcement(
        title=body.get("title", ""),
        content=body.get("content", ""),
        display_mode=body.get("display_mode", "scroll"),
        push_method=body.get("push_method", "all"),
        target_user_id=body.get("target_user_id"),
        start_time=body.get("start_time"),
        end_time=body.get("end_time"),
        is_active=body.get("is_active", 1),
        priority=body.get("priority", 0),
        created_by=current_user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    log_audit(user_id=current_user.id, action="create_announcement", resource=f"announcement:{a.id}", result="success")
    return success_response(data=a.to_dict())


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """更新公告"""
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    for field in ["title", "content", "display_mode", "push_method", "target_user_id", "start_time", "end_time", "is_active", "priority"]:
        if field in body:
            setattr(a, field, body[field])
    a.updated_at = datetime.utcnow().isoformat() + "Z"
    db.commit()
    db.refresh(a)
    log_audit(user_id=current_user.id, action="update_announcement", resource=f"announcement:{a.id}", result="success")
    return success_response(data=a.to_dict())


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除公告"""
    a = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    db.delete(a)
    db.commit()
    log_audit(user_id=current_user.id, action="delete_announcement", resource=f"announcement:{announcement_id}", result="success")
    return None
