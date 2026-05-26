from datetime import datetime
from redis import Redis
from rq import Queue
from sqlalchemy import func
from sqlalchemy.orm import Session

from packages.config.settings import settings
from packages.db.models import (
    AlertEvent, Campaign, CampaignMember, Consent, Customer, CustomerPhone,
    MessageAttempt, MessageJob, ReviewAction, Segment, SegmentMember,
)

def create_campaign(db: Session, payload):
    campaign = Campaign(
        name=payload.name, template_id=payload.template_id, category=payload.category,
        audience_segment=payload.audience_segment, segment_id=payload.segment_id,
        daily_cap=payload.daily_cap, hourly_cap=payload.hourly_cap,
        created_by=payload.created_by, status="draft"
    )
    db.add(campaign); db.commit(); db.refresh(campaign)
    return {"id": str(campaign.id), "status": campaign.status}

def list_campaigns(db: Session):
    rows = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return {"items": [{
        "id": str(r.id), "name": r.name, "status": r.status, "category": r.category,
        "daily_cap": r.daily_cap, "hourly_cap": r.hourly_cap,
        "segment_id": str(r.segment_id) if r.segment_id else None,
    } for r in rows]}

def update_campaign_status(db: Session, campaign_id: str, status: str):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign: return {"error": "campaign_not_found"}
    campaign.status = status; db.commit()
    return {"id": str(campaign.id), "status": campaign.status}

def create_segment(db: Session, payload):
    segment = Segment(
        name=payload.name, description=payload.description,
        category_filter=payload.category_filter, country_code=payload.country_code,
        requires_marketing_consent=payload.requires_marketing_consent, is_active=True,
    )
    db.add(segment); db.commit(); db.refresh(segment)
    return {"id": str(segment.id), "name": segment.name}

def list_segments(db: Session):
    rows = db.query(Segment).order_by(Segment.created_at.desc()).all()
    return {"items": [{
        "id": str(r.id), "name": r.name, "country_code": r.country_code,
        "category_filter": r.category_filter, "requires_marketing_consent": r.requires_marketing_consent,
    } for r in rows]}

def generate_segment_members(db: Session, segment_id: str):
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment: return {"error": "segment_not_found"}
    db.query(SegmentMember).filter(SegmentMember.segment_id == segment.id).delete()
    query = db.query(Customer, CustomerPhone).join(CustomerPhone, CustomerPhone.customer_id == Customer.id)
    if segment.country_code:
        query = query.filter(Customer.country_code == segment.country_code)
    count = 0
    for customer, phone in query.all():
        if segment.requires_marketing_consent:
            consent = db.query(Consent).filter(
                Consent.customer_id == customer.id,
                Consent.phone_id == phone.id,
                Consent.consent_type.in_(["marketing", "transactional"]),
                Consent.status == "active",
            ).first()
            if not consent:
                continue
        db.add(SegmentMember(segment_id=segment.id, customer_id=customer.id, phone_id=phone.id))
        count += 1
    db.commit()
    return {"segment_id": str(segment.id), "members_generated": count}

def generate_campaign_members(db: Session, campaign_id: str):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign: return {"error": "campaign_not_found"}
    if not campaign.segment_id: return {"error": "campaign_missing_segment"}
    db.query(CampaignMember).filter(CampaignMember.campaign_id == campaign.id).delete()
    db.query(MessageJob).filter(MessageJob.campaign_id == campaign.id).delete()
    segment_members = db.query(SegmentMember).filter(SegmentMember.segment_id == campaign.segment_id).all()
    count = 0
    for sm in segment_members:
        db.add(CampaignMember(campaign_id=campaign.id, customer_id=sm.customer_id, phone_id=sm.phone_id, status="pending"))
        db.add(MessageJob(customer_id=sm.customer_id, phone_id=sm.phone_id, template_id=campaign.template_id,
                          campaign_id=campaign.id, category=campaign.category, status="queued"))
        count += 1
    db.commit()
    return {"campaign_id": str(campaign.id), "members_generated": count, "jobs_created": count}

def trigger_campaign_batch(db: Session, campaign_id: str):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign: return {"error": "campaign_not_found"}
    if campaign.status != "approved": return {"error": "campaign_not_approved"}
    jobs = db.query(MessageJob).filter(
        MessageJob.campaign_id == campaign.id,
        MessageJob.status.in_(["queued", "approved_for_retry"]),
        MessageJob.batch_locked == False,
    ).limit(settings.campaign_batch_size).all()
    q = Queue("outbound_messages", connection=Redis.from_url(settings.redis_url))
    for job in jobs:
        job.batch_locked = True
        q.enqueue("packages.services.messaging.send_message_job", str(job.id))
    db.commit()
    return {"campaign_id": str(campaign.id), "dispatched_jobs": len(jobs)}

def dashboard_overview(db: Session):
    return {
        "total_campaigns": db.query(func.count(Campaign.id)).scalar() or 0,
        "total_segments": db.query(func.count(Segment.id)).scalar() or 0,
        "paused_jobs": db.query(func.count(MessageJob.id)).filter(MessageJob.status == "paused").scalar() or 0,
        "sent_jobs": db.query(func.count(MessageJob.id)).filter(MessageJob.status == "sent").scalar() or 0,
        "open_alerts": db.query(func.count(AlertEvent.id)).filter(AlertEvent.is_open == True).scalar() or 0,
    }

def paused_jobs_list(db: Session):
    rows = db.query(MessageJob).filter(MessageJob.status == "paused").all()
    return {"items": [{
        "job_id": str(r.id), "campaign_id": str(r.campaign_id) if r.campaign_id else None,
        "pause_reason": r.pause_reason, "review_status": r.review_status, "retry_count": r.retry_count,
    } for r in rows]}

def approve_paused_job(db: Session, job_id: str, payload):
    job = db.query(MessageJob).filter(MessageJob.id == job_id).first()
    if not job: return {"error": "job_not_found"}
    job.review_status = "approved"; job.reviewed_by = payload.reviewer; job.reviewed_at = datetime.utcnow()
    job.status = "approved_for_retry"; job.batch_locked = False
    db.add(ReviewAction(job_id=job.id, action="approve", reviewer=payload.reviewer, note=payload.note))
    db.commit()
    return {"job_id": str(job.id), "status": job.status, "review_status": job.review_status}

def reject_paused_job(db: Session, job_id: str, payload):
    job = db.query(MessageJob).filter(MessageJob.id == job_id).first()
    if not job: return {"error": "job_not_found"}
    job.review_status = "rejected"; job.reviewed_by = payload.reviewer; job.reviewed_at = datetime.utcnow()
    job.status = "rejected"
    db.add(ReviewAction(job_id=job.id, action="reject", reviewer=payload.reviewer, note=payload.note))
    db.commit()
    return {"job_id": str(job.id), "status": job.status, "review_status": job.review_status}

def retry_job_now(db: Session, job_id: str):
    job = db.query(MessageJob).filter(MessageJob.id == job_id).first()
    if not job: return {"error": "job_not_found"}
    job.status = "approved_for_retry"; job.batch_locked = False; job.next_retry_at = None
    db.commit()
    Queue("outbound_messages", connection=Redis.from_url(settings.redis_url)).enqueue("packages.services.messaging.send_message_job", str(job.id))
    return {"job_id": str(job.id), "status": job.status}

def metrics_summary(db: Session):
    return {
        "attempts_total": db.query(func.count(MessageAttempt.id)).scalar() or 0,
        "sent_total": db.query(func.count(MessageAttempt.id)).filter(MessageAttempt.status.in_(["sent", "delivered"])).scalar() or 0,
        "failed_total": db.query(func.count(MessageAttempt.id)).filter(MessageAttempt.status.in_(["failed", "undelivered"])).scalar() or 0,
        "queued_jobs": db.query(func.count(MessageJob.id)).filter(MessageJob.status == "queued").scalar() or 0,
        "paused_jobs": db.query(func.count(MessageJob.id)).filter(MessageJob.status == "paused").scalar() or 0,
        "retry_ready_jobs": db.query(func.count(MessageJob.id)).filter(MessageJob.status == "approved_for_retry").scalar() or 0,
        "campaign_members": db.query(func.count(CampaignMember.id)).scalar() or 0,
    }

def alerts_summary(db: Session):
    rows = db.query(AlertEvent).filter(AlertEvent.is_open == True).order_by(AlertEvent.created_at.desc()).all()
    return {"items": [{"id": str(a.id), "level": a.level, "code": a.code, "message": a.message, "is_open": a.is_open} for a in rows]}
