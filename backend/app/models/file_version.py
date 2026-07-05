import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.utils.time import utc_now, utc_now_iso
from app.database import Base


class FileVersion(Base):
    __tablename__ = "file_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("document_files.id"), nullable=False)
    version = Column(Integer, nullable=False)                     # display V-number (auto-renumbered)
    sort_order = Column(Float, nullable=False, default=0.0)       # insertion order, independent of version
    storage_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)                # SHA-256
    file_size = Column(Integer, nullable=False)
    changelog = Column(Text, nullable=True)
    storage_mode = Column(String(10), nullable=False, default="full")  # full / delta
    preview_status = Column(String(20), nullable=False, default="pending")
    preview_error = Column(Text, nullable=True)
    analysis_status = Column(String(20), nullable=False, default="pending")
    analysis_error = Column(Text, nullable=True)
    preview_refresh_token = Column(String(36), nullable=True)
    derived_asset_version = Column(Integer, nullable=False, default=1)
    base_version_id = Column(String(36), ForeignKey("file_versions.id"), nullable=True)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: utc_now_iso(),
    )

    # relationships
    file = relationship("DocumentFile", back_populates="versions")
    diffs_as_new = relationship(
        "DiffRecord",
        foreign_keys="DiffRecord.new_version_id",
        back_populates="new_version",
    )

    __table_args__ = (
        Index("idx_fv_file_version", "file_id", "version"),
        Index("idx_fv_file_sort", "file_id", "sort_order"),
    )
