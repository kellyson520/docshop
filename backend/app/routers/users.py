import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import get_current_admin, get_password_hash
from app.models.user import User
from app.services.security_settings import is_registration_enabled, set_registration_enabled
from app.utils.logger import log_audit
from app.utils.response import success_response

router = APIRouter(prefix="/api/v1/users", tags=["users"])

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")
VALID_ROLES = {"admin", "user", "viewer"}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user")


class UserUpdate(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _validate_role(role: str) -> str:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    return role


def _validate_password(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters and include letters and numbers")


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin").count()


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return success_response(data={
        "items": [_user_to_dict(user) for user in users],
        "stats": {
            "total": len(users),
            "admins": sum(1 for user in users if user.role == "admin"),
            "users": sum(1 for user in users if user.role == "user"),
            "viewers": sum(1 for user in users if user.role == "viewer"),
        },
    })


@router.post("")
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    role = _validate_role(body.role)
    _validate_password(body.password)

    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(user_id=current_user.id, action="create_user", resource=f"user:{user.id}", result="success")
    return success_response(data=_user_to_dict(user))


@router.put("/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        role = _validate_role(body.role)
        if user.role == "admin" and role != "admin" and _admin_count(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")
        user.role = role

    if body.password:
        _validate_password(body.password)
        user.password_hash = get_password_hash(body.password)

    user.updated_at = datetime.utcnow().isoformat() + "Z"
    db.commit()
    db.refresh(user)
    log_audit(user_id=current_user.id, action="update_user", resource=f"user:{user.id}", result="success")
    return success_response(data=_user_to_dict(user))


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete current user")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin" and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    try:
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User has related data and cannot be deleted")

    log_audit(user_id=current_user.id, action="delete_user", resource=f"user:{user_id}", result="success")
    return success_response(data={"id": user_id})


@router.get("/settings/registration")
def get_security_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    return success_response(data={"registration_enabled": is_registration_enabled()})


@router.put("/settings/registration")
def update_security_settings(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    enabled = bool(body.get("registration_enabled", False))
    set_registration_enabled(enabled)
    log_audit(user_id=current_user.id, action="update_registration_enabled", resource="security", result="success")
    return success_response(data={"registration_enabled": enabled})
