from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import sys
import uuid

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.security import get_password_hash, create_access_token

security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    auth_token: Optional[str] = Query(None),
    access_token: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
) -> User:
    """Resolve the current user from Bearer auth or a query JWT.

    Browser-native preview requests (iframe/PDF/img) cannot attach an
    Authorization header, so preview URLs may pass the same JWT via
    ?auth_token=... or ?access_token=....
    """
    jwt_token = credentials.credentials if credentials else next(
        (value for value in (auth_token, access_token, token) if isinstance(value, str) and value),
        None,
    )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not jwt_token:
        raise credentials_exception
    try:
        payload = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not getattr(user, 'is_active', True):
        raise credentials_exception
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
    auth_token: Optional[str] = Query(None),
    access_token: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
) -> Optional[User]:
    jwt_token = credentials.credentials if credentials else next(
        (value for value in (auth_token, access_token, token) if isinstance(value, str) and value),
        None,
    )
    if not jwt_token:
        return None
    return get_current_user(
        credentials=credentials,
        db=db,
        auth_token=auth_token,
        access_token=access_token,
        token=token,
    )


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
