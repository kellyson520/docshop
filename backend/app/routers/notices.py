"""
通知路由模块

提供用户通知相关的 API 端点。
"""

from fastapi import APIRouter, Depends
from app.deps.auth import get_current_user
from app.models.user import User
from app.utils.response import success_response

router = APIRouter(prefix="/api/v1/notices", tags=["notices"])


@router.get("")
def get_notices(current_user: User = Depends(get_current_user)):
    return success_response(data=[])


@router.put("/{notice_id}/read")
def mark_read(notice_id: str, current_user: User = Depends(get_current_user)):
    return success_response(data={"id": notice_id, "is_read": True})


@router.put("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user)):
    return success_response(data={"message": "ok"})
