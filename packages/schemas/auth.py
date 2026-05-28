"""Authentication request/response schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID

class LoginRequest(BaseModel):
    """User login request."""
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=12)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username must contain only alphanumeric characters and underscores')
        return v.lower()

class LoginResponse(BaseModel):
    """Successful login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    role: str
    username: str

class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., min_length=10)

class TokenRefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str = Field(..., min_length=12)
    new_password: str = Field(..., min_length=12)
    confirm_password: str = Field(..., min_length=12)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 12:
            raise ValueError('New password must be at least 12 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('New password must contain uppercase letters')
        if not any(c.islower() for c in v):
            raise ValueError('New password must contain lowercase letters')
        if not any(c.isdigit() for c in v):
            raise ValueError('New password must contain digits')
        return v

class ChangePasswordResponse(BaseModel):
    """Change password response."""
    message: str = "Password changed successfully"

class LogoutRequest(BaseModel):
    """Logout request."""
    all_sessions: bool = False  # If True, revoke all sessions

class LogoutResponse(BaseModel):
    """Logout response."""
    message: str = "Logged out successfully"
