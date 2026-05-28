from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ProviderSendResult:
    provider_message_id: str
    provider_sender_id: str | None = None
    status: str = "sent"
    raw: dict[str, Any] | None = None

@dataclass
class ProviderWebhookEvent:
    provider_message_id: str | None
    from_number: str | None = None
    to_number: str | None = None
    body: str | None = None
    status: str | None = None
    event_type: str = "status"
    raw: dict[str, Any] | None = None

class MessageProvider(ABC):
    name = "base"

    @abstractmethod
    def send(self, *, to: str, body: str, metadata: dict | None = None) -> ProviderSendResult:
        raise NotImplementedError

    def normalize_status_webhook(self, payload: dict) -> ProviderWebhookEvent:
        return ProviderWebhookEvent(
            provider_message_id=payload.get("provider_message_id") or payload.get("message_id"),
            status=payload.get("status"),
            event_type="status",
            raw=payload,
        )

    def normalize_inbound_webhook(self, payload: dict) -> ProviderWebhookEvent:
        return ProviderWebhookEvent(
            provider_message_id=payload.get("provider_message_id") or payload.get("message_id"),
            from_number=payload.get("from") or payload.get("From"),
            to_number=payload.get("to") or payload.get("To"),
            body=payload.get("body") or payload.get("Body"),
            event_type="inbound",
            raw=payload,
        )
