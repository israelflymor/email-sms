from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from packages.config.settings import settings
from packages.db.session import get_db
from packages.services.twilio_webhooks import validate_twilio_request, handle_status_callback, handle_inbound_message

router = APIRouter()

@router.post("/status")
async def status_callback(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    if settings.twilio_validate_signature:
        validate_twilio_request(request, settings.twilio_auth_token, form)
    return handle_status_callback(db, form)

@router.post("/inbound")
async def inbound_callback(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    if settings.twilio_validate_signature:
        validate_twilio_request(request, settings.twilio_auth_token, form)
    return handle_inbound_message(db, form)
