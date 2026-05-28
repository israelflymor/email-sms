from packages.providers.router import get_message_provider

class SmsProviderAdapter:
    def send(self, *, to: str, body: str, metadata: dict | None = None) -> dict:
        provider = get_message_provider("sms")
        result = provider.send(to=to, body=body, metadata=metadata or {})
        return {
            "provider": provider.name,
            "provider_message_id": result.provider_message_id,
            "provider_sender_id": result.provider_sender_id,
            "status": result.status,
            "raw": result.raw or {},
        }

class TwilioSmsProvider(SmsProviderAdapter):
    pass
