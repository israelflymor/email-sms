from packages.providers.local_mock import LocalMockProvider

class VonageProvider(LocalMockProvider):
    name = "vonage_placeholder"

    def send(self, *, to: str, body: str, metadata: dict | None = None):
        result = super().send(to=to, body=body, metadata=metadata)
        result.raw["note"] = "Vonage adapter placeholder. Implement API call before production."
        return result
