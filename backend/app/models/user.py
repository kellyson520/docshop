import uuid
from datetime import datetime
from sqlalchemy import Column, String
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")  # admin / viewer
    avatar_url = Column(String(512), nullable=True)
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
