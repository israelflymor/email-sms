"""Authentication routes with JWT and session-based auth."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from packages.db.session import get_db
from packages.auth.models import AdminUser, UserSession
from packages.schemas.auth import (
    LoginRequest, LoginResponse, TokenRefreshRequest, TokenRefreshResponse,
    ChangePasswordRequest, ChangePasswordResponse, LogoutRequest, LogoutResponse
)
from packages.auth.password import hash_password, verify_password, is_password_strong
from packages.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from packages.auth.security import rate_limiter, BruteForceProtection
from packages.auth.audit import AuthAudit
from packages.auth.dependencies import get_current_user, get_request_context
from packages.config.settings import settings
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

LOGIN_RATE_LIMIT_KEY_PREFIX = "login_attempt:"
PASSWORD_RESET_RATE_LIMIT_KEY_PREFIX = "password_reset:"

@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    context: dict = Depends(get_request_context),
) -> LoginResponse:
    """
    User login endpoint.
    
    Returns JWT access and refresh tokens for authenticated users.
    """
    ip_address = context.get("ip_address")
    user_agent = context.get("user_agent")
    
    # Rate limiting
    rate_limit_key = f"{LOGIN_RATE_LIMIT_KEY_PREFIX}{ip_address}"
    if rate_limiter.is_rate_limited(rate_limit_key, max_attempts=5, window_seconds=300):
        logger.warning(f"Login rate limit exceeded from IP: {ip_address}")
        AuthAudit.log_login(
            db, payload.username, False,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="Rate limit exceeded"
        )
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    
    # Find user
    user = db.query(AdminUser).filter(
        AdminUser.username == payload.username.lower()
    ).first()
    
    if not user:
        logger.warning(f"Login failed: user not found - {payload.username}")
        AuthAudit.log_login(
            db, payload.username, False,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="User not found"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if account is locked
    if BruteForceProtection.is_account_locked(user):
        logger.warning(f"Login attempt on locked account: {user.username}")
        AuthAudit.log_login(
            db, user.username, False,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="Account locked"
        )
        raise HTTPException(status_code=423, detail="Account is locked due to too many failed login attempts")
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt on inactive user: {user.username}")
        AuthAudit.log_login(
            db, user.username, False,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="Account inactive"
        )
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        BruteForceProtection.record_failed_login(db, user)
        logger.warning(f"Login failed: invalid password - {user.username}")
        AuthAudit.log_login(
            db, user.username, False,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            reason="Invalid password"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Reset failed attempts and update last login
    BruteForceProtection.reset_failed_attempts(db, user)
    rate_limiter.reset_rate_limit(rate_limit_key)
    
    # Create tokens
    access_token_jti = str(uuid.uuid4())
    refresh_token_jti = str(uuid.uuid4())

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        jti=access_token_jti,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        username=user.username,
        jti=refresh_token_jti,
    )
    
    # Create session records for access and refresh tokens
    access_expires_at = datetime.now(timezone.utc) + __import__('datetime').timedelta(minutes=settings.jwt_expiration_minutes)
    refresh_expires_at = datetime.now(timezone.utc) + __import__('datetime').timedelta(days=settings.jwt_refresh_expiration_days)
    sessions = [
        UserSession(
            user_id=user.id,
            token_jti=access_token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=access_expires_at,
        ),
        UserSession(
            user_id=user.id,
            token_jti=refresh_token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=refresh_expires_at,
        ),
    ]
    db.add_all(sessions)
    
    # Log successful login
    AuthAudit.log_login(
        db, user.username, True,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    logger.info(f"Successful login: {user.username}")
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expiration_minutes * 60,
        role=user.role,
        username=user.username,
    )

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    payload: TokenRefreshRequest,
    db: Session = Depends(get_db),
    context: dict = Depends(get_request_context),
) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.
    """
    ip_address = context.get("ip_address")
    user_agent = context.get("user_agent")
    
    # Verify refresh token
    token_payload = verify_token(payload.refresh_token, token_type="refresh")
    if not token_payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_id = token_payload.get("sub")
    refresh_jti = token_payload.get("jti")
    
    # Validate refresh session has not been revoked
    refresh_session = db.query(UserSession).filter(
        UserSession.token_jti == refresh_jti,
        UserSession.is_active == True,
    ).first()
    if not refresh_session:
        raise HTTPException(status_code=401, detail="Refresh session not found or revoked")

    # Get user
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Create new access token
    access_token_jti = str(uuid.uuid4())
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        jti=access_token_jti,
    )
    
    # Create session record for new token
    expires_at = datetime.now(timezone.utc) + __import__('datetime').timedelta(minutes=settings.jwt_expiration_minutes)
    session = UserSession(
        user_id=user.id,
        token_jti=access_token_jti,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)
    
    AuthAudit.log_token_refresh(
        db, user.id, user.username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    logger.info(f"Token refreshed for user: {user.username}")
    
    return TokenRefreshResponse(
        access_token=access_token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    context: dict = Depends(get_request_context),
) -> LogoutResponse:
    """
    User logout endpoint.
    """
    user_id = current_user.get("user_id")
    username = current_user.get("username")
    jti = current_user.get("jti")
    ip_address = context.get("ip_address")
    user_agent = context.get("user_agent")
    
    # Revoke current session
    session = db.query(UserSession).filter(
        UserSession.token_jti == jti
    ).first()
    
    if session:
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
    
    # Optionally revoke all sessions
    if payload.all_sessions:
        db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
        ).update({"is_active": False, "revoked_at": datetime.now(timezone.utc)})
        logger.info(f"All sessions revoked for user: {username}")
    
    AuthAudit.log_logout(
        db, user_id, username,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return LogoutResponse()

@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ChangePasswordResponse:
    """
    Change user password.
    """
    user_id = current_user.get("user_id")
    username = current_user.get("username")
    
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(payload.current_password, user.hashed_password):
        AuthAudit.log_password_change(db, user.id, username, False, reason="Invalid current password")
        raise HTTPException(status_code=401, detail="Invalid current password")
    
    # Validate new password strength
    is_strong, message = is_password_strong(payload.new_password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=message)
    
    # Passwords must match
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Cannot reuse current password
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="New password cannot be the same as current password")
    
    # Hash and save new password
    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    
    # Revoke all existing sessions for security
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True,
    ).update({"is_active": False, "revoked_at": datetime.now(timezone.utc)})
    
    AuthAudit.log_password_change(db, user.id, username, True)
    logger.info(f"Password changed for user: {username}")
    
    return ChangePasswordResponse()
