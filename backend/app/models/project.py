import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
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
    is_public = Column(Integer, nullable=False, default=0)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.utcnow().isoformat() + "Z",
    )
    updated_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.utcnow().isoformat() + "Z",
    )

    # relationships
    files = relationship(
        "DocumentFile", back_populates="project", cascade="all, delete-orphan"
    )
    exams = relationship(
        "ExamSchedule", back_populates="project", cascade="all, delete-orphan"
    )
    owner = relationship("User")
