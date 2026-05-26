from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.auth.dependencies import require_roles
from packages.db.session import get_db
from packages.schemas.admin import CampaignCreate, ReviewDecisionRequest, SegmentCreate
from packages.services.admin_dashboard import (
    create_campaign, list_campaigns, update_campaign_status, dashboard_overview,
    paused_jobs_list, approve_paused_job, reject_paused_job, metrics_summary,
    alerts_summary, trigger_campaign_batch, retry_job_now,
    create_segment, list_segments, generate_segment_members, generate_campaign_members,
)

router = APIRouter()

@router.post("/campaigns")
def create_campaign_endpoint(payload: CampaignCreate, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator"))):
    return create_campaign(db, payload)

@router.get("/campaigns")
def get_campaigns(db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))):
    return list_campaigns(db)

@router.post("/campaigns/{campaign_id}/approve")
def approve_campaign(campaign_id: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "reviewer"))):
    return update_campaign_status(db, campaign_id, "approved")

@router.post("/campaigns/{campaign_id}/pause")
def pause_campaign(campaign_id: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator"))):
    return update_campaign_status(db, campaign_id, "paused")

@router.post("/campaigns/{campaign_id}/generate-members")
def generate_members(campaign_id: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator"))):
    return generate_campaign_members(db, campaign_id)

@router.post("/campaigns/{campaign_id}/dispatch-batch")
def dispatch_batch(campaign_id: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator"))):
    return trigger_campaign_batch(db, campaign_id)

@router.post("/segments")
def create_segment_endpoint(payload: SegmentCreate, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator"))):
    return create_segment(db, payload)

@router.get("/segments")
def get_segments(db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))):
    return list_segments(db)

@router.post("/segments/{segment_id}/generate-members")
def generate_segment(segment_id: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator"))):
    return generate_segment_members(db, segment_id)

@router.get("/dashboard/overview")
def get_dashboard_overview(db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))):
    return dashboard_overview(db)

@router.get("/dashboard/paused-jobs")
def get_paused_jobs(db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))):
    return paused_jobs_list(db)

@router.post("/reviews/jobs/{job_id}/approve")
def approve_job(job_id: str, payload: ReviewDecisionRequest, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "reviewer"))):
    return approve_paused_job(db, job_id, payload)

@router.post("/reviews/jobs/{job_id}/reject")
def reject_job(job_id: str, payload: ReviewDecisionRequest, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "reviewer"))):
    return reject_paused_job(db, job_id, payload)

@router.post("/reviews/jobs/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "reviewer"))):
    return retry_job_now(db, job_id)

@router.get("/metrics/summary")
def get_metrics_summary(db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))):
    return metrics_summary(db)

@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db), _: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))):
    return alerts_summary(db)
