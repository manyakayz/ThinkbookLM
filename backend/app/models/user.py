from __future__ import annotations
from datetime import datetime
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    """Public user model (safe to return in API responses)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    created_at: datetime
    updated_at: datetime


class UserInDB(User):
    """Internal user model including the password hash."""
    password_hash: str


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Full name cannot be empty.")
        if len(clean) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        # Basic standard email regex validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email address format.")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v

    def validate_passwords_match(self) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserResponse
    csrf_token: str
