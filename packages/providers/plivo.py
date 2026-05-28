import base64
import json
import urllib.request
from packages.config.settings import settings
from packages.providers.base import MessageProvider, ProviderSendResult, ProviderWebhookEvent

class PlivoProvider(MessageProvider):
    name = "plivo"

    def send(self, *, to: str, body: str, metadata: dict | None = None) -> ProviderSendResult:
        if not settings.sms_api_key or not settings.sms_api_secret or not settings.sms_sender_id:
            raise RuntimeError("Plivo requires SMS_API_KEY, SMS_API_SECRET, and SMS_SENDER_ID.")
        payload = json.dumps({"src": settings.sms_sender_id, "dst": to, "text": body}).encode()
        auth = base64.b64encode(f"{settings.sms_api_key}:{settings.sms_api_secret}".encode()).decode()
        req = urllib.request.Request(
            f"https://api.plivo.com/v1/Account/{settings.sms_api_key}/Message/",
            data=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode())
        uuid_value = raw.get("message_uuid", [""])
        if isinstance(uuid_value, list):
            uuid_value = uuid_value[0] if uuid_value else ""
        return ProviderSendResult(uuid_value, settings.sms_sender_id, "sent", raw)

    def normalize_status_webhook(self, payload: dict) -> ProviderWebhookEvent:
        return ProviderWebhookEvent(payload.get("MessageUUID"), status=payload.get("Status"), event_type="status", raw=payload)

    def normalize_inbound_webhook(self, payload: dict) -> ProviderWebhookEvent:
        return ProviderWebhookEvent(payload.get("MessageUUID"), payload.get("From"), payload.get("To"), payload.get("Text"), event_type="inbound", raw=payload)
