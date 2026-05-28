"""Audit logging for authentication events."""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from packages.auth.models import AuthAuditLog
import uuid

logger = logging.getLogger(__name__)

class AuthAudit:
    """Audit logger for authentication events."""
    
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        status: str,
        user_id: Optional[uuid.UUID] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Log authentication event."""
        try:
            audit_log = AuthAuditLog(
                event_type=event_type,
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                reason=reason,
            )
            db.add(audit_log)
            db.commit()
            logger.info(f"Auth audit: {event_type} - {status} - {username or 'unknown'}")
        except Exception as e:
            logger.error(f"Error logging auth event: {e}")
            db.rollback()

    @staticmethod
    def log_login(db: Session, username: str, success: bool, **context) -> None:
        """Log login attempt."""
        AuthAudit.log_event(
            db,
            event_type="login",
            status="success" if success else "failure",
            username=username,
            **context
        )
    
    @staticmethod
    def log_logout(db: Session, user_id: uuid.UUID, username: str, **context) -> None:
        """Log logout event."""
        AuthAudit.log_event(
            db,
            event_type="logout",
            status="success",
            user_id=user_id,
            username=username,
            **context
        )
    
    @staticmethod
    def log_token_refresh(db: Session, user_id: uuid.UUID, username: str, **context) -> None:
        """Log token refresh event."""
        AuthAudit.log_event(
            db,
            event_type="token_refresh",
            status="success",
            user_id=user_id,
            username=username,
            **context
        )
    
    @staticmethod
    def log_password_change(db: Session, user_id: uuid.UUID, username: str, success: bool, **context) -> None:
        """Log password change event."""
        AuthAudit.log_event(
            db,
            event_type="password_change",
            status="success" if success else "failure",
            user_id=user_id,
            username=username,
            **context
        )
