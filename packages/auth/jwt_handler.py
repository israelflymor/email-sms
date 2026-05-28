"""JWT token generation and validation with security best practices."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from pydantic import ValidationError
from packages.config.settings import settings

logger = logging.getLogger(__name__)

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Longer-lived refresh tokens

def get_jwt_secret() -> str:
    """Get JWT secret from settings."""
    secret = getattr(settings, "jwt_secret_key", None)
    if not secret:
        raise ValueError("JWT_SECRET_KEY environment variable not configured")
    if len(secret) < 32:
        raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
    return secret

def create_access_token(
    user_id: uuid.UUID,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> str:
    """Create JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    jti = jti or str(uuid.uuid4())
    
    payload = {
        "sub": str(user_id),  # Subject (user ID)
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),  # Issued at
        "exp": int(expire.timestamp()),  # Expiration
        "jti": jti,  # JWT ID (unique token identifier)
        "type": "access",  # Token type
    }
    
    try:
        encoded_jwt = jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise

def create_refresh_token(
    user_id: uuid.UUID,
    username: str,
    jti: Optional[str] = None,
) -> str:
    """Create JWT refresh token."""
    jti = jti or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
        "type": "refresh",
    }
    
    try:
        encoded_jwt = jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        
        # Validate token type
        if payload.get("type") != token_type:
            logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
            return None
        
        # Validate required claims
        if not all(k in payload for k in ["sub", "username", "jti", "exp"]):
            logger.warning("Missing required token claims")
            return None
        
        return payload
    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None

def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]
