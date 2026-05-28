from fastapi import FastAPI
from apps.api.routes import health, consents, messages, admin, auth

app = FastAPI(title="Messaging API", version="0.8.0")
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(consents.router, prefix="/consents", tags=["consents"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
