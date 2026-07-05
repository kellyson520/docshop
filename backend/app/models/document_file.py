import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.utils.time import utc_now, utc_now_iso
from app.database import Base


class DocumentFile(Base):
    __tablename__ = "document_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf / docx / xlsx
    file_category = Column(String(20), nullable=False, default="binary")
    mime_type = Column(String(255), nullable=True)
    current_version = Column(Integer, nullable=False, default=1)
    preview_status = Column(String(20), nullable=False, default="pending")
    preview_error = Column(Text, nullable=True)
    analysis_status = Column(String(20), nullable=False, default="pending")
    analysis_error = Column(Text, nullable=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    folder_id = Column(String(36), ForeignKey("project_folders.id"), nullable=True)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: utc_now_iso(),
    )
    
    # 卡片式文档管理新增字段
    cover_image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    display_name = Column(String(255), nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    visit_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        String(30),
        nullable=True,
        default=lambda: utc_now_iso(),
        onupdate=lambda: utc_now_iso(),  # 自动更新
    )

    # relationships
    project = relationship("Project", back_populates="files")
    folder = relationship("ProjectFolder", back_populates="files")

    __table_args__ = (
        Index("idx_df_project_id", "project_id"),
        Index("idx_df_folder_id", "folder_id"),
    )
    versions = relationship(
        "FileVersion",
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="FileVersion.sort_order.asc()",
    )

    # 分类与标签
    category = relationship("Category", back_populates="documents")
    tags = relationship("Tag", secondary="document_tags", back_populates="documents")
