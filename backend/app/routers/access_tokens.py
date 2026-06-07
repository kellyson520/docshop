"""
访问令牌管理路由

管理员管理主页门禁令牌，主页验证令牌。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.access_token import AccessToken
from app.deps.auth import get_current_admin
from app.utils.response import success_response
from app.utils.logger import get_logger, log_audit

router = APIRouter(prefix="/api/v1/access-tokens", tags=["access-tokens"])
logger = get_logger("routers.access_tokens")


@router.get("/validate")
def validate_token(token: str = Query(...), db: Session = Depends(get_db)):
    """公开接口：验证访问令牌是否有效"""
    t = db.query(AccessToken).filter(AccessToken.token == token, AccessToken.is_active == 1).first()
    return success_response(data={"valid": t is not None})


@router.get("")
def list_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """管理员列表"""
    tokens = db.query(AccessToken).order_by(AccessToken.created_at.desc()).all()
    return success_response(data={"items": [t.to_dict() for t in tokens]})


@router.post("")
def create_token(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """创建新令牌"""
    t = AccessToken(
        token=AccessToken.generate(),
        name=body.get("name", "未命名"),
        created_by=current_user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    log_audit(user_id=current_user.id, action="create_access_token", resource=f"token:{t.id}", result="success")
    return success_response(data=t.to_dict())


@router.put("/{token_id}")
def update_token(
    token_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """更新令牌（重命名/启禁用/重新生成）"""
    t = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    if "name" in body:
        t.name = body["name"]
    if "is_active" in body:
        t.is_active = body["is_active"]
    if body.get("regenerate"):
        t.token = AccessToken.generate()
    db.commit()
    db.refresh(t)
    return success_response(data=t.to_dict())


@router.delete("/{token_id}")
def delete_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """删除令牌"""
    t = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="令牌不存在")
    db.delete(t)
    db.commit()
    log_audit(user_id=current_user.id, action="delete_access_token", resource=f"token:{token_id}", result="success")
    return None
