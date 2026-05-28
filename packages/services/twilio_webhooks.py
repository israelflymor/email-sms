from urllib.parse import parse_qsl
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator

from packages.config.settings import settings
from packages.db.models import InboundMessage, MessageAttempt, Suppression

def validate_twilio_request(request, auth_token: str, form_data: dict) -> None:
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    valid = validator.validate(url, form_data, signature)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

def handle_status_callback(db: Session, payload: dict):
    sid = payload.get("MessageSid")
    status = payload.get("MessageStatus")
    attempt = db.query(MessageAttempt).filter(MessageAttempt.twilio_message_sid == sid).first()
    if attempt:
        attempt.status = status or attempt.status
        db.commit()
    return {"ok": True}

def classify_inbound_intent(body: str) -> str:
    val = (body or "").strip().lower()
    if val == "stop":
        return "stop"
    if val == "help":
        return "help"
    if val == "start":
        return "start"
    if "spam" in val or "complaint" in val:
        return "complaint"
    return "normal"

def handle_inbound_message(db: Session, payload: dict):
    from_number = payload.get("From")
    to_number = payload.get("To")
    body = payload.get("Body", "")
    sid = payload.get("MessageSid")
    intent = classify_inbound_intent(body)

    inbound = InboundMessage(
        twilio_message_sid=sid,
        from_number=from_number,
        to_number=to_number,
        body=body,
        intent=intent,
        processed=True,
    )
    db.add(inbound)

    if intent == "stop":
        existing = db.query(Suppression).filter(Suppression.phone_e164 == from_number, Suppression.scope == "global").first()
        if not existing:
            db.add(Suppression(phone_e164=from_number, scope="global", reason="stop"))
        db.commit()
        return PlainTextResponse("You have been unsubscribed from messages. No further messages will be sent.")
    if intent == "help":
        db.commit()
        return PlainTextResponse("For support contact support@example.com. Msg freq varies. Reply STOP to opt out.")
    if intent == "start":
        db.commit()
        return PlainTextResponse("You have replied START. Complete your explicit re-subscription flow in-app before messaging resumes.")

    db.commit()
    return PlainTextResponse("OK")
