from fastapi import APIRouter, HTTPException
from packages.schemas.auth import LoginRequest
from packages.auth.tokens import issue_token

router = APIRouter()

@router.post("/login")
def login(payload: LoginRequest):
    result = issue_token(payload.api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return result
