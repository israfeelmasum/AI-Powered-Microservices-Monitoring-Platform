

# monitoring-core/app/auth/auth.py
import secrets
import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from ..config.settings import settings

logger = logging.getLogger(__name__)
security = HTTPBasic()

def logout_user():
    """Force logout by returning 401 with WWW-Authenticate header"""
    raise HTTPException(
        status_code=401,
        detail="Logged out",
        headers={"WWW-Authenticate": 'Basic realm="Please login again"'},
    )

def authenticate(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Basic authentication for admin access"""
    is_username_correct = secrets.compare_digest(
        credentials.username, settings.ADMIN_USERNAME
    )
    is_password_correct = secrets.compare_digest(
        credentials.password, settings.ADMIN_PASSWORD
    )

    if not (is_username_correct and is_password_correct):
        logger.warning(f"Failed authentication attempt for user: {credentials.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    logger.info(f"Successful authentication for user: {credentials.username}")
    return credentials.username


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Get current authenticated user"""
    return authenticate(credentials)


def validate_service_secret(service_name: str, secret: str) -> bool:
    """Validate service secret key"""
    return settings.SERVICE_SECRETS.get(service_name) == secret


# monitoring-core/app/auth/models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserBase):
    id: int
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    username: Optional[str] = None
    service_name: Optional[str] = None