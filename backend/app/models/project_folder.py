import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time import utc_now_iso


class ProjectFolder(Base):
    __tablename__ = "project_folders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    parent_id = Column(String(36), ForeignKey("project_folders.id"), nullable=True)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(
        String(30),
        nullable=False,
        default=lambda: utc_now_iso(),
        onupdate=lambda: utc_now_iso(),
    )

    project = relationship("Project", back_populates="folders")
    parent = relationship("ProjectFolder", remote_side=[id])
    files = relationship("DocumentFile", back_populates="folder")

    __table_args__ = (
        Index("idx_project_folders_project_id", "project_id"),
        Index("idx_project_folders_parent_id", "parent_id"),
    )
