from datetime import datetime
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session
from packages.config.settings import settings
from packages.db.models import Campaign, MessageJob

def enqueue_job(job_id: str):
    Queue("outbound_messages", connection=Redis.from_url(settings.redis_url)).enqueue("packages.services.messaging.send_message_job", str(job_id))

def run_scheduler_tick(db: Session):
    for campaign in db.query(Campaign).filter(Campaign.status == "approved").all():
        jobs = db.query(MessageJob).filter(
            MessageJob.campaign_id == campaign.id,
            MessageJob.status.in_(["queued", "approved_for_retry"]),
            MessageJob.batch_locked == False,
        ).limit(settings.campaign_batch_size).all()
        for job in jobs:
            job.batch_locked = True
            enqueue_job(str(job.id))
    for job in db.query(MessageJob).filter(MessageJob.status == "approved_for_retry").limit(settings.campaign_batch_size).all():
        if job.next_retry_at and job.next_retry_at > datetime.utcnow():
            continue
        job.batch_locked = True
        enqueue_job(str(job.id))
    db.commit()
