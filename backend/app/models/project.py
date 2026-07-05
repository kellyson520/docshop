import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.utils.time import utc_now, utc_now_iso
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    share_token = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: utc_now_iso(),
    )
    updated_at = Column(
        String(30),
        nullable=False,
        default=lambda: utc_now_iso(),
    )

    # relationships
    files = relationship(
        "DocumentFile", back_populates="project", cascade="all, delete-orphan"
    )
    folders = relationship(
        "ProjectFolder", back_populates="project", cascade="all, delete-orphan"
    )
    exams = relationship(
        "ExamSchedule", back_populates="project", cascade="all, delete-orphan"
    )
    owner = relationship("User")
