from fastapi import Header, HTTPException
from packages.auth.tokens import verify_token

def require_roles(*allowed_roles: str):
    def dependency(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        payload = verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        role = payload.get("role")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    return dependency
