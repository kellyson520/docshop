import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, TypeDecorator
from sqlalchemy.orm import synonym
from app.database import Base
from app.utils.time import utc_now


class DateTimeString(TypeDecorator):
    """Store timestamps as strings for schema compatibility, return datetime objects."""

    impl = String(30)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, datetime):
            return value
        text = str(value)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    hashed_password = synonym("password_hash")
    role = Column(String(20), nullable=False, default="viewer")  # admin / viewer
    is_active = Column(Boolean, nullable=False, default=True)
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTimeString, nullable=False, default=utc_now)
    updated_at = Column(DateTimeString, nullable=False, default=utc_now, onupdate=utc_now)
