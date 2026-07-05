import uuid

from sqlalchemy import Column, ForeignKey, String, Text

from app.database import Base
from app.utils.time import utc_now_iso


class FileAnalysisRecord(Base):
    __tablename__ = "file_analysis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("document_files.id"), nullable=False)
    version_id = Column(String(36), ForeignKey("file_versions.id"), nullable=False)
    analysis_type = Column(String(32), nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="ready")
    error_message = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
