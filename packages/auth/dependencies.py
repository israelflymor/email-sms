"""FastAPI dependencies for JWT authentication."""
import logging
from typing import Optional
from fastapi import HTTPException, Header, Request, Depends
from sqlalchemy.orm import Session
from packages.auth.jwt_handler import verify_token, extract_token_from_header
from packages.db.session import get_db
from packages.db.models import AdminUser
from packages.db.session import SessionLocal

logger = logging.getLogger(__name__)

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """Get current authenticated user from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")
    jti = payload.get("jti")
    
    if not all([user_id, username, role, jti]):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    
    # Verify session exists and is active
    from packages.db.models import UserSession
    session = db.query(UserSession).filter(
        UserSession.token_jti == jti,
        UserSession.is_active == True
    ).first()
    
    if not session:
        logger.warning(f"No active session found for token JTI: {jti}")
        raise HTTPException(status_code=401, detail="Session not found or revoked")
    
    return {
        "user_id": user_id,
        "username": username,
        "role": role,
        "jti": jti,
    }

def require_roles(*allowed_roles: str):
    """Dependency to require specific roles."""
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            logger.warning(f"Access denied for user {current_user.get('username')} with role {user_role}")
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of: {', '.join(allowed_roles)}"
            )
        return current_user
    return dependency

async def get_request_context(request: Request) -> dict:
    """Extract request context for audit logging."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
