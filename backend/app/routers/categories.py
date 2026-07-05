"""分类与标签 API"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.category import Category, Tag
from app.deps.auth import get_current_user, get_current_admin
from app.utils.response import success_response

categories_router = APIRouter(prefix="/api/v1/categories", tags=["categories"])
tags_router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


# ── Categories ──

@categories_router.get("")
def list_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cats = db.query(Category).order_by(Category.name.asc()).all()
    return success_response(data=[{"id": c.id, "name": c.name, "description": c.description, "color": c.color} for c in cats])

@categories_router.post("", status_code=201)
def create_category(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    color: Optional[str] = Body("#6366f1"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="分类名不能为空")
    name = name.strip()
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="分类名不能超过100字符")
    if db.query(Category).filter(Category.name == name).first():
        raise HTTPException(status_code=400, detail="分类名已存在")
    cat = Category(name=name, description=description, color=color)
    db.add(cat)
    db.commit()
    return success_response(data={"id": cat.id, "name": cat.name, "color": cat.color})

@categories_router.put("/{cat_id}")
def update_category(
    cat_id: str,
    name: Optional[str] = Body(None),
    color: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    if name is not None: cat.name = name
    if color is not None: cat.color = color
    db.commit()
    return success_response(data={"id": cat.id, "name": cat.name})

@categories_router.delete("/{cat_id}", status_code=200)
def delete_category(
    cat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    db.delete(cat)
    db.commit()
    return success_response(message="已删除")


# ── Tags ──

@tags_router.get("")
def list_tags(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tags = db.query(Tag).order_by(Tag.name.asc()).all()
    return success_response(data=[{"id": t.id, "name": t.name, "color": t.color} for t in tags])

@tags_router.post("", status_code=201)
def create_tag(
    name: str = Body(...),
    color: Optional[str] = Body("#22c55e"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="标签名不能为空")
    name = name.strip()
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="标签名不能超过100字符")
    if db.query(Tag).filter(Tag.name == name).first():
        raise HTTPException(status_code=400, detail="标签名已存在")
    t = Tag(name=name, color=color)
    db.add(t)
    db.commit()
    return success_response(data={"id": t.id, "name": t.name, "color": t.color})

@tags_router.put("/{tag_id}")
def update_tag(
    tag_id: str,
    name: Optional[str] = Body(None),
    color: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    t = db.query(Tag).filter(Tag.id == tag_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="标签不存在")
    if name is not None: t.name = name
    if color is not None: t.color = color
    db.commit()
    return success_response(data={"id": t.id, "name": t.name})
