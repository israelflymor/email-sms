from packages.providers.local_mock import LocalMockProvider

class AwsSmsProvider(LocalMockProvider):
    name = "aws_sms_placeholder"

    def send(self, *, to: str, body: str, metadata: dict | None = None):
        result = super().send(to=to, body=body, metadata=metadata)
        result.raw["note"] = "AWS SMS adapter placeholder. Implement AWS End User Messaging/SNS before production."
        return result
