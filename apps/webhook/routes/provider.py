from fastapi import APIRouter, Depends, HTTPException, Request
from hmac import compare_digest
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from packages.config.settings import settings
from packages.db.models import InboundMessage, MessageAttempt, Suppression
from packages.db.session import get_db
from packages.providers.router import get_message_provider

router = APIRouter()


def verify_provider_webhook(request: Request) -> None:
    configured_secret = settings.sms_webhook_secret
    if not configured_secret:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured")

    provided_secret = request.headers.get("x-webhook-secret")
    if not provided_secret or not compare_digest(provided_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


async def read_payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    return dict(await request.form())


@router.post("/status")
async def status_callback(request: Request, db: Session = Depends(get_db)):
    verify_provider_webhook(request)
    payload = await read_payload(request)
    event = get_message_provider("sms").normalize_status_webhook(payload)

    attempt = None
    if event.provider_message_id:
        if hasattr(MessageAttempt, "provider_message_id"):
            attempt = db.query(MessageAttempt).filter(
                MessageAttempt.provider_message_id == event.provider_message_id
            ).first()
        if not attempt and hasattr(MessageAttempt, "twilio_message_sid"):
            attempt = db.query(MessageAttempt).filter(
                MessageAttempt.twilio_message_sid == event.provider_message_id
            ).first()

    if attempt and event.status:
        attempt.status = event.status
        db.commit()

    return {
        "ok": True,
        "provider_message_id": event.provider_message_id,
        "status": event.status,
        "matched_attempt": bool(attempt),
    }


@router.post("/inbound")
async def inbound_callback(request: Request, db: Session = Depends(get_db)):
    verify_provider_webhook(request)
    payload = await read_payload(request)
    event = get_message_provider("sms").normalize_inbound_webhook(payload)
    body = event.body or ""
    intent = classify_inbound_intent(body)

    inbound = InboundMessage(
        twilio_message_sid=event.provider_message_id,
        from_number=event.from_number or "",
        to_number=event.to_number or "",
        body=body,
        intent=intent,
        processed=True,
    )
    db.add(inbound)

    if intent == "stop":
        exists = db.query(Suppression).filter(
            Suppression.phone_e164 == (event.from_number or ""),
            Suppression.scope == "global",
        ).first()
        if not exists:
            db.add(Suppression(phone_e164=event.from_number or "", scope="global", reason="stop"))
        db.commit()
        return PlainTextResponse("You have been unsubscribed from messages. No further messages will be sent.")

    if intent == "help":
        db.commit()
        return PlainTextResponse("For support contact support@example.com. Msg freq varies. Reply STOP to opt out.")

    db.commit()
    return PlainTextResponse("OK")


def classify_inbound_intent(body: str) -> str:
    normalized = (body or "").strip().lower()
    if normalized == "stop":
        return "stop"
    if normalized == "help":
        return "help"
    if normalized == "start":
        return "start"
    if "spam" in normalized or "complaint" in normalized:
        return "complaint"
    return "normal"
