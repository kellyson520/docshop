import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String

from app.database import Base


class ShareTabGrant(Base):
    __tablename__ = "share_tab_grants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_token = Column(String(255), nullable=False, index=True)
    tab_id = Column(String(120), nullable=False, index=True)
    grant_hash = Column(String(128), nullable=False, index=True)
    issued_at = Column(DateTime, nullable=False, default=datetime.now)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    released_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_share_tab_grants_lookup", "share_token", "tab_id", "grant_hash"),
    )
