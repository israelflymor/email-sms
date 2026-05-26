from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.db.session import get_db
from packages.schemas.consents import ConsentCreate
from packages.services.consents import create_consent

router = APIRouter()

@router.post("")
def create_consent_endpoint(payload: ConsentCreate, db: Session = Depends(get_db)):
    consent = create_consent(db, payload)
    return {"id": str(consent.id), "status": consent.status}
