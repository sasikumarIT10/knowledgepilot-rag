"""Authentication schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Registration request schema."""
    
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = Field(None, max_length=255)


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    
    token: str
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str


class UserResponse(BaseModel):
    """User response schema."""
    
    id: str
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User update schema."""
    
    full_name: str | None = None
    email: EmailStr | None = None
