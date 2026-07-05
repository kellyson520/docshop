import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.utils.time import utc_now, utc_now_iso
from app.database import Base


class DiffRecord(Base):
    __tablename__ = "diff_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    old_version_id = Column(
        String(36), ForeignKey("file_versions.id", ondelete="CASCADE"), nullable=False
    )
    new_version_id = Column(
        String(36), ForeignKey("file_versions.id", ondelete="CASCADE"), nullable=False
    )
    diff_type = Column(String(20), nullable=False)  # text / cell / visual
    diff_data = Column(Text, nullable=False)  # JSON string
    summary = Column(Text, nullable=True)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: utc_now_iso(),
    )

    # relationships
    old_version = relationship("FileVersion", foreign_keys=[old_version_id])
    new_version = relationship(
        "FileVersion", foreign_keys=[new_version_id], back_populates="diffs_as_new"
    )

    __table_args__ = (
        Index("idx_diff_old_version", "old_version_id"),
        Index("idx_diff_new_version", "new_version_id"),
    )
