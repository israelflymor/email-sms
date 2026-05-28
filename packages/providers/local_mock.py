import uuid
from packages.providers.base import MessageProvider, ProviderSendResult

class LocalMockProvider(MessageProvider):
    name = "local_mock"

    def send(self, *, to: str, body: str, metadata: dict | None = None) -> ProviderSendResult:
        return ProviderSendResult(
            provider_message_id=f"mock_{uuid.uuid4().hex}",
            provider_sender_id="local_mock",
            status="simulated",
            raw={"to": to, "body": body, "metadata": metadata or {}, "note": "No real SMS delivered."},
        )
