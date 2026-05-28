from datetime import datetime, timedelta
import hashlib
from redis import Redis
from rq import Queue
from packages.config.settings import settings
from packages.db.models import AlertEvent, Campaign, CustomerPhone, MessageAttempt, MessageEvent, MessageJob, MessageTemplate
from packages.schemas.messages import TransactionalMessageRequest
from packages.services.policy_engine import evaluate_message_policy
from packages.services.twilio_adapter import TwilioSmsProvider

def enqueue_transactional_message(db, payload: TransactionalMessageRequest) -> dict:
    existing = db.query(MessageEvent).filter(MessageEvent.idempotency_key == payload.idempotency_key).first()
    if existing:
        return {"status": "duplicate_ignored", "event_id": str(existing.id)}
    event = MessageEvent(event_type="transactional.send_requested", customer_id=payload.customer_id, payload_json=payload.payload, idempotency_key=payload.idempotency_key)
    db.add(event); db.flush()
    template = db.query(MessageTemplate).filter(MessageTemplate.name == payload.template_name).first()
    if not template: raise ValueError("template_not_found")
    job = MessageJob(event_id=event.id, customer_id=payload.customer_id, phone_id=payload.phone_id, template_id=template.id, category=template.category, status="queued")
    db.add(job); db.commit()
    Queue("outbound_messages", connection=Redis.from_url(settings.redis_url)).enqueue(send_message_job, str(job.id))
    return {"job_id": str(job.id), "status": "queued"}

def render_template_body(template_body: str, payload: dict) -> str:
    body = template_body
    for key, value in payload.items():
        body = body.replace("{{" + str(key) + "}}", str(value))
    return body

def create_alert(db, code: str, message: str, level: str = "warning") -> None:
    db.add(AlertEvent(code=code, message=message, level=level)); db.commit()

def _schedule_retry(job, reason: str):
    job.retry_count = (job.retry_count or 0) + 1
    if job.retry_count >= settings.retry_max_attempts:
        job.status = "rejected"; job.pause_reason = f"retry_exhausted:{reason}"; return False
    job.status = "approved_for_retry"; job.pause_reason = reason; job.batch_locked = False
    job.next_retry_at = datetime.utcnow() + timedelta(seconds=settings.retry_backoff_seconds * job.retry_count)
    return True

def send_message_job(job_id: str) -> None:
    from packages.db.session import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(MessageJob).filter(MessageJob.id == job_id).first()
        if not job: return
        if job.campaign_id:
            campaign = db.query(Campaign).filter(Campaign.id == job.campaign_id).first()
            if not campaign or campaign.status != "approved":
                job.status = "paused"; job.pause_reason = "campaign_not_approved"; job.review_status = "pending"; job.batch_locked = False
                db.commit(); create_alert(db, "campaign_not_approved", f"Job {job.id} paused because campaign is not approved."); return
        phone = db.query(CustomerPhone).filter(CustomerPhone.id == job.phone_id).first()
        template = db.query(MessageTemplate).filter(MessageTemplate.id == job.template_id).first()
        event = db.query(MessageEvent).filter(MessageEvent.id == job.event_id).first() if job.event_id else None
        if not all([phone, template]):
            job.status = "blocked"; job.pause_reason = "missing_dependencies"; job.batch_locked = False; db.commit(); return
        payload = event.payload_json if event else {}
        body = render_template_body(template.body, payload)
        decision = evaluate_message_policy(db, phone_id=str(job.phone_id), category=job.category, body_preview=body)
        if decision.action != "ALLOW":
            if decision.action == "BLOCK":
                job.status = "blocked"; job.pause_reason = decision.reason
            else:
                ok = _schedule_retry(job, decision.reason or "throttled")
                if ok: create_alert(db, "job_retry_scheduled", f"Job {job.id} scheduled for retry due to {decision.reason}.")
                else: create_alert(db, "job_retry_exhausted", f"Job {job.id} exhausted retry budget.")
            db.commit(); return
        attempt = MessageAttempt(job_id=job.id, to_number=phone.phone_e164, rendered_body_hash=hashlib.sha256(body.encode()).hexdigest(), status="created")
        db.add(attempt); db.flush()
        try:
            result = TwilioSmsProvider().send(to=phone.phone_e164, body=body)
            attempt.twilio_message_sid = result["provider_message_id"]
            attempt.messaging_service_sid = settings.twilio_messaging_service_sid
            attempt.status = "sent"
            job.status = "sent"; job.batch_locked = False; job.pause_reason = None
            db.commit()
        except Exception as exc:
            attempt.status = "failed"; attempt.error_message = str(exc); job.batch_locked = False
            ok = _schedule_retry(job, "provider_error"); db.commit()
            if ok: create_alert(db, "provider_error_retry", f"Job {job.id} scheduled for retry after provider error.")
            else: create_alert(db, "provider_error_final", f"Job {job.id} failed permanently after provider error.")
    finally:
        db.close()
