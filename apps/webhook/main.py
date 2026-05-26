from fastapi import FastAPI
from apps.webhook.routes import provider, twilio

app = FastAPI(title="email-sms Provider Webhooks", version="0.10.0")

# New provider-neutral webhook endpoints.
app.include_router(provider.router, prefix="/webhooks/provider", tags=["provider-webhooks"])

# Backward-compatible legacy endpoints. Do not remove during stabilization.
app.include_router(twilio.router, prefix="/webhooks/twilio", tags=["legacy-twilio-webhooks"])
