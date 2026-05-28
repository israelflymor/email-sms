from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.db.session import get_db
from packages.schemas.messages import TransactionalMessageRequest
from packages.services.messaging import enqueue_transactional_message

router = APIRouter()

@router.post("/send-transactional")
def send_transactional(payload: TransactionalMessageRequest, db: Session = Depends(get_db)):
    return enqueue_transactional_message(db, payload)
