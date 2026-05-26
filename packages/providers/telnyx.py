import json
import urllib.request
from packages.config.settings import settings
from packages.providers.base import MessageProvider, ProviderSendResult, ProviderWebhookEvent

class TelnyxProvider(MessageProvider):
    name = "telnyx"

    def send(self, *, to: str, body: str, metadata: dict | None = None) -> ProviderSendResult:
        if not settings.sms_api_key or not settings.sms_sender_id:
            raise RuntimeError("Telnyx requires SMS_API_KEY and SMS_SENDER_ID.")
        data = json.dumps({"from": settings.sms_sender_id, "to": to, "text": body}).encode()
        req = urllib.request.Request(
            "https://api.telnyx.com/v2/messages",
            data=data,
            headers={"Authorization": f"Bearer {settings.sms_api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode())
        msg = raw.get("data", {})
        return ProviderSendResult(msg.get("id", ""), settings.sms_sender_id, "sent", raw)

    def normalize_status_webhook(self, payload: dict) -> ProviderWebhookEvent:
        data = payload.get("data", {}).get("payload", {})
        return ProviderWebhookEvent(data.get("id"), status=payload.get("event_type"), event_type="status", raw=payload)

    def normalize_inbound_webhook(self, payload: dict) -> ProviderWebhookEvent:
        data = payload.get("data", {}).get("payload", {})
        return ProviderWebhookEvent(
            provider_message_id=data.get("id"),
            from_number=(data.get("from") or {}).get("phone_number"),
            to_number=(data.get("to") or [{}])[0].get("phone_number") if data.get("to") else None,
            body=data.get("text"),
            event_type="inbound",
            raw=payload,
        )
