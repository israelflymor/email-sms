import base64
import hashlib
import hmac
import json
import time
from packages.auth.service import get_role_for_api_key

SECRET = "phase8_internal_auth_secret"

def issue_token(api_key: str):
    role = get_role_for_api_key(api_key)
    if not role:
        return None
    payload = {
        "api_key": api_key,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60 * 8,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(raw).decode() + "." + sig
    return {"token": token, "role": role}

def verify_token(token: str):
    try:
        encoded, sig = token.split(".", 1)
        raw = base64.urlsafe_b64decode(encoded.encode())
        expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(raw.decode())
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
