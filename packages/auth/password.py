"""Secure password hashing and verification."""
import logging
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Use bcrypt with strong parameters
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Computational cost factor
)

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    if not password or len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def get_password_strength_score(password: str) -> int:
    """Calculate password strength score (0-100)."""
    score = 0
    
    if len(password) >= 12:
        score += 20
    if len(password) >= 16:
        score += 10
    if any(c.isupper() for c in password):
        score += 20
    if any(c.islower() for c in password):
        score += 20
    if any(c.isdigit() for c in password):
        score += 15
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 15
    
    return min(score, 100)

def is_password_strong(password: str, min_score: int = 60) -> tuple[bool, str]:
    """Check if password meets strength requirements."""
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    score = get_password_strength_score(password)
    if score < min_score:
        return False, f"Password is too weak (strength: {score}/100). Use uppercase, lowercase, numbers, and special characters."
    
    return True, "Password is strong"
