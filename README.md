# Twilio US SMS Compliance Scaffold — Phase 5

This package adds:
- Alembic migration setup + initial migration
- audience segmentation tables and services
- campaign member generation
- executable frontend actions
- more deploy-oriented guidance

## Included
- FastAPI API app
- Twilio webhook app
- RQ worker
- scheduler service
- admin frontend scaffold
- Redis-backed throttling
- campaign approval flow
- paused-job review and retry flow
- segment generation and campaign population
- Alembic migration files

## Quick start
```bash
cp .env.example .env
docker compose up --build
```

## Important
This is a strong internal-tool scaffold, not a public SaaS-ready product yet. Replace API-key auth with JWT/session auth before internet exposure.
