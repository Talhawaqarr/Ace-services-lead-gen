# Environment & Secrets — ACE Services

This document outlines environment variables, secret handling, and `.env.example` for local/dev use. Do not store secrets in repository.

## Secret management
- Use a secrets manager in production: AWS Secrets Manager / HashiCorp Vault / Azure Key Vault.
- Local dev can use `.env` files; never commit secrets.
- CI should use encrypted variables per provider.

## `.env.example`
- Provide non-secret placeholders for development. See below.

## Required ENV variables (examples)
- `DATABASE_URL` — Postgres connection string
- `REDIS_URL` — Redis connection
- `S3_ENDPOINT` — S3-compatible endpoint
- `EMAIL_PROVIDER` — e.g., `postmark`
- `LLM_PROVIDER` — e.g., `openai`
- `MAPBOX_TOKEN` — geocoding (if used)
- `OPENAI_API_KEY` — LLM provider key
- `SENDGRID_API_KEY` — if using SendGrid fallback
- `PGVECTOR_EXTENSION` — `true`/`false` for embedding storage
- `MAX_EMAILS_PER_HOUR` — throttling

## Access controls
- Service accounts for background jobs with least privilege.
- DB roles: `app_readonly`, `app_writer`, `migrations`.

## Example `.env.example` content
- The file below is safe to commit and non-sensitive.

DATABASE_URL=postgresql://localhost/ace_dev
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
# Development defaults (do not require keys)
EMAIL_PROVIDER=mock
LLM_PROVIDER=mock
MAPBOX_TOKEN=
OPENAI_API_KEY=
PGVECTOR_EXTENSION=false
MAX_EMAILS_PER_HOUR=100

# DRY_RUN flag: when true, no external sends or paid APIs are called.
# Default for development: DRY_RUN=true
DRY_RUN=true

---

Add per-provider optional vars in `PROVIDER_CREDENTIALS.md`.