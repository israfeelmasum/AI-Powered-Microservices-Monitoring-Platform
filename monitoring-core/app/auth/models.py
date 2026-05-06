# monitoring-core/app/auth/models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
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