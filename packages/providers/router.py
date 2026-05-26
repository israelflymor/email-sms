from packages.config.settings import settings
from packages.providers.local_mock import LocalMockProvider
from packages.providers.email_smtp import EmailSmtpProvider
from packages.providers.mailpit import MailpitProvider
from packages.providers.telnyx import TelnyxProvider
from packages.providers.plivo import PlivoProvider
from packages.providers.vonage import VonageProvider
from packages.providers.aws_sms import AwsSmsProvider
from packages.providers.smpp_gateway import SmppGatewayProvider

def get_message_provider(channel: str = "sms"):
    provider = settings.email_provider if channel == "email" else (settings.sms_provider or settings.message_provider)
    provider = (provider or "local_mock").lower()

    mapping = {
        "local_mock": LocalMockProvider,
        "email_smtp": EmailSmtpProvider,
        "mailpit": MailpitProvider,
        "telnyx": TelnyxProvider,
        "plivo": PlivoProvider,
        "vonage": VonageProvider,
        "aws": AwsSmsProvider,
        "aws_sms": AwsSmsProvider,
        "sns": AwsSmsProvider,
        "smpp": SmppGatewayProvider,
        "smpp_gateway": SmppGatewayProvider,
    }
    if provider not in mapping:
        raise RuntimeError(f"Unsupported message provider: {provider}")
    return mapping[provider]()
