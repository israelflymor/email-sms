from pydantic import BaseModel
from uuid import UUID

class CampaignCreate(BaseModel):
    name: str
    template_id: UUID | None = None
    category: str = "promotional"
    audience_segment: str | None = None
    segment_id: UUID | None = None
    daily_cap: int = 1000
    hourly_cap: int = 100
    created_by: str | None = "system_admin"

class ReviewDecisionRequest(BaseModel):
    reviewer: str = "system_admin"
    note: str | None = None

class SegmentCreate(BaseModel):
    name: str
    description: str | None = None
    category_filter: str | None = None
    country_code: str | None = None
    requires_marketing_consent: bool = True
