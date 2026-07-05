"""文档分类与标签模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.utils.time import utc_now, utc_now_iso
from app.database import Base

# 文档-标签多对多关联表
document_tags = Table(
    "document_tags", Base.metadata,
    Column("document_id", String(36), ForeignKey("document_files.id"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True, default="#6366f1")
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    documents = relationship("DocumentFile", back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True)
    color = Column(String(20), nullable=True, default="#22c55e")
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

    documents = relationship("DocumentFile", secondary=document_tags, back_populates="tags")
