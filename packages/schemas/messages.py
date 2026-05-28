from pydantic import BaseModel
from uuid import UUID

class TransactionalMessageRequest(BaseModel):
    customer_id: UUID
    phone_id: UUID
    template_name: str
    payload: dict
    idempotency_key: str
