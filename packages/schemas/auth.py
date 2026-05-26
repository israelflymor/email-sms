from pydantic import BaseModel

class LoginRequest(BaseModel):
    api_key: str

class LoginResponse(BaseModel):
    role: str
    token: str
