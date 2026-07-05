import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base
from app.utils.time import utc_now_iso


class FilePreviewAsset(Base):
    __tablename__ = "file_preview_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("document_files.id"), nullable=False)
    version_id = Column(String(36), ForeignKey("file_versions.id"), nullable=False)
    asset_type = Column(String(32), nullable=False)
    storage_path = Column(String(500), nullable=False)
    page_number = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="ready")
    error_message = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
