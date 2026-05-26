from datetime import datetime
from sqlalchemy.orm import Session
from packages.db.models import Consent
from packages.schemas.consents import ConsentCreate

def create_consent(db: Session, payload: ConsentCreate) -> Consent:
    consent = Consent(
        customer_id=payload.customer_id,
        phone_id=payload.phone_id,
        consent_type=payload.consent_type,
        source=payload.source,
        disclosure_text=payload.disclosure_text,
        ip_address=payload.ip_address,
        user_agent=payload.user_agent,
        collected_at=datetime.utcnow(),
        status="active",
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent
