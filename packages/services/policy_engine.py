from dataclasses import dataclass
from sqlalchemy.orm import Session

from packages.db.models import Consent, CustomerPhone, Suppression
from packages.services.rate_limits import (
    check_duplicate_window,
    check_global_caps,
    check_user_frequency,
    quiet_hours_violation,
)

@dataclass
class PolicyDecision:
    action: str
    reason: str | None = None
    retry_at: str | None = None

def evaluate_message_policy(db: Session, *, phone_id: str, category: str, body_preview: str) -> PolicyDecision:
    phone = db.query(CustomerPhone).filter(CustomerPhone.id == phone_id).first()
    if not phone:
        return PolicyDecision(action="BLOCK", reason="phone_not_found")

    suppression = db.query(Suppression).filter(Suppression.phone_e164 == phone.phone_e164).first()
    if suppression:
        return PolicyDecision(action="BLOCK", reason=f"suppressed:{suppression.reason}")

    consent = db.query(Consent).filter(Consent.phone_id == phone_id, Consent.status == "active").first()
    if not consent and category != "otp":
        return PolicyDecision(action="BLOCK", reason="missing_consent")

    quiet_hours = quiet_hours_violation(None, category)
    if not quiet_hours.ok:
        return PolicyDecision(action="THROTTLE", reason=quiet_hours.reason, retry_at=quiet_hours.retry_at)

    global_caps = check_global_caps(category)
    if not global_caps.ok:
        return PolicyDecision(action="THROTTLE", reason=global_caps.reason, retry_at=global_caps.retry_at)

    user_caps = check_user_frequency(phone.phone_e164, category)
    if not user_caps.ok:
        return PolicyDecision(action="THROTTLE", reason=user_caps.reason, retry_at=user_caps.retry_at)

    duplicate = check_duplicate_window(phone.phone_e164, body_preview)
    if not duplicate.ok:
        return PolicyDecision(action="THROTTLE", reason=duplicate.reason, retry_at=duplicate.retry_at)

    return PolicyDecision(action="ALLOW")
