"""Security utilities including rate limiting and brute-force protection."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import redis
from packages.config.settings import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter using Redis."""
    
    def __init__(self, redis_url: str):
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting disabled.")
            self.redis_client = None
    
    def is_rate_limited(self, key: str, max_attempts: int = 5, window_seconds: int = 300) -> bool:
        """Check if key has exceeded rate limit."""
        if not self.redis_client:
            return False
        
        try:
            current = self.redis_client.get(key)
            if current is None:
                self.redis_client.setex(key, window_seconds, 1)
                return False
            
            attempts = int(current)
            if attempts >= max_attempts:
                return True
            
            self.redis_client.incr(key)
            return False
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False
    
    def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for key."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Error resetting rate limit: {e}")

class BruteForceProtection:
    """Brute-force attack protection."""
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    @staticmethod
    def is_account_locked(user: any) -> bool:
        """Check if account is locked due to failed attempts."""
        if not user.is_locked:
            return False
        
        if user.locked_until is None:
            return True
        
        if datetime.now(timezone.utc) > user.locked_until:
            return False
        
        return True
    
    @staticmethod
    def record_failed_login(db: any, user: any) -> None:
        """Record failed login attempt."""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= BruteForceProtection.MAX_FAILED_ATTEMPTS:
            user.is_locked = True
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=BruteForceProtection.LOCKOUT_DURATION_MINUTES
            )
            logger.warning(f"Account locked: {user.username}")
        
        db.commit()
    
    @staticmethod
    def reset_failed_attempts(db: any, user: any) -> None:
        """Reset failed login attempts after successful login."""
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

rate_limiter = RateLimiter(settings.redis_url)
