from pydantic import BaseModel
from uuid import UUID

class ConsentCreate(BaseModel):
    customer_id: UUID
    phone_id: UUID
    consent_type: str
    source: str
    disclosure_text: str
    ip_address: str | None = None
    user_agent: str | None = None
