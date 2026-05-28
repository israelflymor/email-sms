from packages.providers.local_mock import LocalMockProvider

class SmppGatewayProvider(LocalMockProvider):
    name = "smpp_gateway_placeholder"

    def send(self, *, to: str, body: str, metadata: dict | None = None):
        result = super().send(to=to, body=body, metadata=metadata)
        result.raw["note"] = "SMPP gateway placeholder. Requires upstream SMPP/carrier access."
        return result
