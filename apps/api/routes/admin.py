"""Update admin routes to use JWT authentication instead of API keys."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.auth.dependencies import require_roles, get_current_user
from packages.db.session import get_db
from packages.schemas.admin import CampaignCreate, ReviewDecisionRequest, SegmentCreate
from packages.services.admin_dashboard import (
    create_campaign, list_campaigns, update_campaign_status, dashboard_overview,
    paused_jobs_list, approve_paused_job, reject_paused_job, metrics_summary,
    alerts_summary, trigger_campaign_batch, retry_job_now,
    create_segment, list_segments, generate_segment_members, generate_campaign_members,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/campaigns")
async def create_campaign_endpoint(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator"))
):
    """Create campaign (requires admin or operator role)."""
    logger.info(f"Campaign creation requested by {current_user['username']}")
    return create_campaign(db, payload)

@router.get("/campaigns")
async def get_campaigns(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))
):
    """List campaigns (all authenticated users)."""
    return list_campaigns(db)

@router.post("/campaigns/{campaign_id}/approve")
async def approve_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "reviewer"))
):
    """Approve campaign (requires admin or reviewer role)."""
    logger.info(f"Campaign approval requested by {current_user['username']}")
    return update_campaign_status(db, campaign_id, "approved")

@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator"))
):
    """Pause campaign (requires admin or operator role)."""
    logger.info(f"Campaign pause requested by {current_user['username']}")
    return update_campaign_status(db, campaign_id, "paused")

@router.post("/campaigns/{campaign_id}/generate-members")
async def generate_members(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator"))
):
    """Generate campaign members (requires admin or operator role)."""
    return generate_campaign_members(db, campaign_id)

@router.post("/campaigns/{campaign_id}/dispatch-batch")
async def dispatch_batch(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator"))
):
    """Dispatch campaign batch (requires admin or operator role)."""
    return trigger_campaign_batch(db, campaign_id)

@router.post("/segments")
async def create_segment_endpoint(
    payload: SegmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator"))
):
    """Create segment (requires admin or operator role)."""
    return create_segment(db, payload)

@router.get("/segments")
async def get_segments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))
):
    """List segments (all authenticated users)."""
    return list_segments(db)

@router.post("/segments/{segment_id}/generate-members")
async def generate_segment(
    segment_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator"))
):
    """Generate segment members (requires admin or operator role)."""
    return generate_segment_members(db, segment_id)

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))
):
    """Get dashboard overview (all authenticated users)."""
    return dashboard_overview(db)

@router.get("/dashboard/paused-jobs")
async def get_paused_jobs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))
):
    """List paused jobs (all authenticated users)."""
    return paused_jobs_list(db)

@router.post("/reviews/jobs/{job_id}/approve")
async def approve_job(
    job_id: str,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "reviewer"))
):
    """Approve job (requires admin or reviewer role)."""
    logger.info(f"Job approval requested by {current_user['username']}")
    return approve_paused_job(db, job_id, payload)

@router.post("/reviews/jobs/{job_id}/reject")
async def reject_job(
    job_id: str,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "reviewer"))
):
    """Reject job (requires admin or reviewer role)."""
    logger.info(f"Job rejection requested by {current_user['username']}")
    return reject_paused_job(db, job_id, payload)

@router.post("/reviews/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "reviewer"))
):
    """Retry job (requires admin, operator, or reviewer role)."""
    return retry_job_now(db, job_id)

@router.get("/metrics/summary")
async def get_metrics_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))
):
    """Get metrics summary (all authenticated users)."""
    return metrics_summary(db)

@router.get("/alerts")
async def get_alerts(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_roles("admin", "operator", "viewer", "reviewer"))
):
    """Get alerts (all authenticated users)."""
    return alerts_summary(db)
