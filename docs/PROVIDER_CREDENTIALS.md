# Provider Credentials & `.env` Variables

This file enumerates required environment variables and configuration entries for the chosen MVP providers. Replace placeholders with real keys during deployment.

## Required for MVP (primary)
- `OPENAI_API_KEY` — API key for embeddings and LLM prompts
- `MAPBOX_ACCESS_TOKEN` — Mapbox geocoding and routing
- `POSTMARK_API_KEY` — Postmark server token (or `SENDGRID_API_KEY` / `MAILGUN_API_KEY` / `AWS_SES_SMTP_USER` & `AWS_SES_SMTP_PASSWORD` if using alternatives)
- `OPENCORPORATES_API_KEY` — OpenCorporates token for company enrichment (optional but recommended)

## Database & infra
- `DATABASE_URL` — Postgres connection URL (prefer `postgres://` or `postgresql://` with SSL parameters)
- `REDIS_URL` — Redis connection for Celery
- `S3_ENDPOINT` — S3-compatible endpoint (minio or AWS S3)
- `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET`

## Optional / Provider-specific
- `SAM_API_KEY` — if required by downstream SAM services (often not required)
- `USA_SPENDING_API_KEY` — optional for rate-limited endpoints
- `CONSTRUCTCONNECT_API_KEY` — only if ACE purchases a subscription
- `DODGE_API_KEY` — only if subscribed

## Email deliverability / domain configuration
- `MAIL_FROM` — default from address (e.g., ops@yourdomain.com)
- `DKIM_SELECTOR` / `DKIM_PRIVATE_KEY` — if managing DKIM in-app (recommended to configure at DNS)

## Security & Secrets
- `JWT_SECRET_KEY` — signing key for JWTs
- `ADMIN_USERS` — comma-separated admin emails or an external identity provider config

## Misc
- `DEFAULT_TIMEZONE` — app timezone
- `PGVECTOR_DIM` — embedding vector dimension (set after choosing the embedding model)

Notes
- Do not commit `.env` to git. Create `.env.example` with keys but no values.
- Prefer a secrets manager (Vault, AWS Secrets Manager) for production.
