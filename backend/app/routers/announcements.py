"""
公告管理路由模块

提供公告 CRUD 和公开查询 API。
"""

import asyncio
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import get_current_admin
from app.models.announcement import Announcement
from app.models.user import User
from app.services.event_bus import publish_announcement_event
from app.utils.logger import get_logger, log_audit
from app.utils.response import success_response
from app.utils.sanitization import sanitize_user_text
from app.utils.time import utc_now_iso

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])
logger = get_logger("routers.announcements")


class AnnouncementBlock(BaseModel):
    type: str = Field(..., min_length=1, max_length=32)
    text: Optional[str] = None
    language: Optional[str] = None
    content: Optional[str] = None
    file_id: Optional[str] = None
    caption: Optional[str] = None
    label: Optional[str] = None
    url: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=255)
    content: str = Field(..., min_length=1)
    content_blocks: list[AnnouncementBlock] = Field(default_factory=list)
    popup_config: dict[str, Any] = Field(default_factory=dict)
    display_mode: str = Field("scroll", pattern="^(scroll|popup|sidebar|bottom)$")
    push_method: str = Field("all", pattern="^(all|timed|single)$")
    target_user_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_active: int = Field(1, ge=0, le=1)
    priority: int = Field(0, ge=0, le=100)


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    content_blocks: Optional[list[AnnouncementBlock]] = None
    popup_config: Optional[dict[str, Any]] = None
    display_mode: Optional[str] = Field(None, pattern="^(scroll|popup|sidebar|bottom)$")
    push_method: Optional[str] = Field(None, pattern="^(all|timed|single)$")
    target_user_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_active: Optional[int] = Field(None, ge=0, le=1)
    priority: Optional[int] = Field(None, ge=0, le=100)


def _sanitize_block_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return sanitize_user_text(value)


def _sanitize_popup_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in config.items():
        clean_key = sanitize_user_text(str(key)) or ""
        if not clean_key:
            continue

        if isinstance(value, str):
            sanitized[clean_key] = sanitize_user_text(value)
        elif isinstance(value, (int, float, bool)) or value is None:
            sanitized[clean_key] = value
        else:
            sanitized[clean_key] = sanitize_user_text(json.dumps(value, ensure_ascii=False))
    return sanitized


def _sanitize_blocks(blocks: list[AnnouncementBlock]) -> list[dict[str, Any]]:
    sanitized_blocks: list[dict[str, Any]] = []

    for block in blocks:
        block_type = sanitize_user_text(block.type or "") or ""
        if not block_type:
            continue

        item: dict[str, Any] = {"type": block_type}
        if block.text is not None:
            item["text"] = _sanitize_block_text(block.text)
        if block.language is not None:
            item["language"] = _sanitize_block_text(block.language)
        if block.content is not None:
            item["content"] = _sanitize_block_text(block.content)
        if block.file_id is not None:
            item["file_id"] = _sanitize_block_text(block.file_id)
        if block.caption is not None:
            item["caption"] = _sanitize_block_text(block.caption)
        if block.label is not None:
            item["label"] = _sanitize_block_text(block.label)
        if block.url is not None:
            item["url"] = _sanitize_block_text(block.url)

        sanitized_blocks.append(item)

    return sanitized_blocks


def _apply_timing_fields(target: Announcement, push_method: str, start_time: Optional[str], end_time: Optional[str], target_user_id: Optional[str]) -> None:
    target.push_method = push_method
    target.start_time = start_time if push_method == "timed" else None
    target.end_time = end_time if push_method == "timed" else None
    target.target_user_id = target_user_id if push_method == "single" else None


def _notify_announcement_event(event_type: str, payload: dict[str, Any]) -> None:
    announcement_id = str(payload.get("announcement_id") or "").strip()
    if not announcement_id:
        return

    async def _publish() -> None:
        await publish_announcement_event(event_type, announcement_id)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.run(_publish())
        except Exception as exc:
            logger.warning(f"Failed to publish announcement event: {exc}", exc_info=True)
    else:
        loop.create_task(_publish())


@router.get("/active")
def get_active_announcements(db: Session = Depends(get_db)):
    """获取当前激活公告（公开接口）。"""
    now = utc_now_iso()
    query = db.query(Announcement).filter(Announcement.is_active == 1)

    active = []
    for announcement in query.order_by(Announcement.priority.desc(), Announcement.created_at.desc()).all():
        if announcement.push_method == "timed":
            if announcement.start_time and announcement.start_time > now:
                continue
            if announcement.end_time and announcement.end_time < now:
                continue
        if announcement.push_method == "single":
            continue
        active.append(announcement.to_dict())

    return success_response(data=active)


@router.get("")
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """获取公告列表。"""
    total = db.query(Announcement).count()
    items = (
        db.query(Announcement)
        .order_by(Announcement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.to_dict() for item in items],
    })


@router.post("", status_code=status.HTTP_201_CREATED)
def create_announcement(
    body: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """创建公告。"""
    sanitized_blocks = _sanitize_blocks(body.content_blocks)
    sanitized_popup_config = _sanitize_popup_config(body.popup_config)

    announcement = Announcement(
        title=sanitize_user_text(body.title),
        summary=sanitize_user_text(body.summary),
        content=sanitize_user_text(body.content),
        content_blocks_json=json.dumps(sanitized_blocks, ensure_ascii=False),
        popup_config_json=json.dumps(sanitized_popup_config, ensure_ascii=False),
        display_mode=body.display_mode,
        is_active=body.is_active,
        priority=body.priority,
        created_by=current_user.id,
    )
    _apply_timing_fields(
        announcement,
        body.push_method,
        body.start_time,
        body.end_time,
        body.target_user_id,
    )

    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    log_audit(
        user_id=current_user.id,
        action="create_announcement",
        resource=f"announcement:{announcement.id}",
        result="success",
    )
    _notify_announcement_event("announcement.created", {"announcement_id": announcement.id})
    return success_response(data=announcement.to_dict())


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    body: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """更新公告。"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "title" in update_data:
        announcement.title = sanitize_user_text(update_data["title"])
    if "summary" in update_data:
        announcement.summary = sanitize_user_text(update_data["summary"])
    if "content" in update_data:
        announcement.content = sanitize_user_text(update_data["content"])
    if "content_blocks" in update_data:
        announcement.content_blocks_json = json.dumps(
            _sanitize_blocks(body.content_blocks or []),
            ensure_ascii=False,
        )
    if "popup_config" in update_data:
        announcement.popup_config_json = json.dumps(
            _sanitize_popup_config(body.popup_config or {}),
            ensure_ascii=False,
        )
    if "display_mode" in update_data:
        announcement.display_mode = update_data["display_mode"]
    if "push_method" in update_data:
        _apply_timing_fields(
            announcement,
            update_data["push_method"],
            update_data.get("start_time", announcement.start_time),
            update_data.get("end_time", announcement.end_time),
            update_data.get("target_user_id", announcement.target_user_id),
        )
    else:
        if "start_time" in update_data and announcement.push_method == "timed":
            announcement.start_time = update_data["start_time"]
        if "end_time" in update_data and announcement.push_method == "timed":
            announcement.end_time = update_data["end_time"]
        if "target_user_id" in update_data and announcement.push_method == "single":
            announcement.target_user_id = update_data["target_user_id"]
    if "is_active" in update_data:
        announcement.is_active = update_data["is_active"]
    if "priority" in update_data:
        announcement.priority = update_data["priority"]

    sanitize_user_text(announcement.title)
    announcement.updated_at = utc_now_iso()
    db.commit()
    db.refresh(announcement)

    log_audit(
        user_id=current_user.id,
        action="update_announcement",
        resource=f"announcement:{announcement.id}",
        result="success",
    )
    event_type = "announcement.visibility.changed" if "is_active" in update_data else "announcement.updated"
    _notify_announcement_event(event_type, {"announcement_id": announcement.id})
    return success_response(data=announcement.to_dict())


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除公告。"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="公告不存在")

    db.delete(announcement)
    db.commit()
    log_audit(
        user_id=current_user.id,
        action="delete_announcement",
        resource=f"announcement:{announcement_id}",
        result="success",
    )
    _notify_announcement_event("announcement.deleted", {"announcement_id": announcement_id})
    return None
