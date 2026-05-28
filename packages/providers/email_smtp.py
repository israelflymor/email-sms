import smtplib
import uuid
from email.message import EmailMessage
from packages.config.settings import settings
from packages.providers.base import MessageProvider, ProviderSendResult

class EmailSmtpProvider(MessageProvider):
    name = "email_smtp"

    def send(self, *, to: str, body: str, metadata: dict | None = None) -> ProviderSendResult:
        metadata = metadata or {}
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = metadata.get("subject", "Notification")
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, int(settings.smtp_port), timeout=15) as smtp:
            if settings.smtp_username and settings.smtp_password:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)

        return ProviderSendResult(
            provider_message_id=f"email_{uuid.uuid4().hex}",
            provider_sender_id=settings.smtp_from,
            status="sent",
            raw={"provider": self.name, "to": to},
        )
