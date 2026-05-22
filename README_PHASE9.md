# Phase 9 — Provider-Agnostic Messaging Layer

This package changes the project from Twilio-specific delivery to provider-agnostic delivery.

## What changed

- Added provider adapter interface.
- Added local mock SMS provider.
- Added SMTP/Mailpit email provider.
- Added Telnyx and Plivo adapters.
- Added placeholders for Vonage, AWS SMS, and SMPP.
- Added provider-neutral config.
- Preserved legacy Twilio-compatible imports for safe transition.

## Run locally without Twilio

```bash
cp .env.example .env
docker compose -f docker-compose.phase9.yml up --build
```

Use:

```env
SMS_PROVIDER=local_mock
EMAIL_PROVIDER=mailpit
```

Mailpit UI:

```text
http://localhost:8025
```

## Important

This removes the need for Twilio during development and internal testing.

For real US SMS delivery, you still need a compliant SMS provider such as Telnyx, Plivo, Vonage, AWS End User Messaging/SNS, or an SMPP aggregator.
