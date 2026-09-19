# ACE Services — System Architecture (High Level)

This document describes the proposed modular architecture for the ACE Services Bid Intelligence platform. It is designed to be production-ready, modular, and maintainable while remaining simple enough for early-stage development (modular monolith) and to be incrementally extended.

## Architectural Principles
- Modularity: clear separation of concerns into layers and provider adapters.
- Incremental delivery: start as a modular monolith; split into services only when necessary.
- Replaceability: external providers are behind interfaces/adapters.
- Observability and reliability: robust logging, metrics, retry/backoff and idempotency.
- Data provenance: every imported/enriched field stores source, confidence, and timestamps.
- Security-first: secrets in env or vault, strict input validation, audited webhooks.

## High-level components
- Frontend: Next.js + React + TypeScript (server-side rendering for SEO, auth pages, and initial dashboard). Tailwind CSS + shadcn/ui components.
- API: FastAPI (Python) serving REST endpoints and OpenAPI docs.
- Business layer: Python domain services (project ingestion, matching, enrichment).
- Database: PostgreSQL (relational, ACID) with SQLAlchemy + Alembic migrations.
- Background jobs: Celery with Redis (or RQ) for asynchronous tasks.
- ML: Python packages (pandas, scikit-learn, sentence-transformers for embeddings). Store serialized models (joblib) and model metadata in DB.
- Email: provider adapters (Postmark/SendGrid/Mailgun/SES) for sending and webhook handling.
- Provider adapters: ``providers/`` package with classes implementing unified interfaces (BidProvider, ContractorProvider, EnrichmentProvider, Geocoder, EmailProvider, LLMProvider, EmbeddingProvider).
- Storage for files: S3-compatible object store (minio for local dev, AWS S3 for prod).
- Deployment: Docker + docker-compose for local; containerized for cloud deployment.

## Why these choices
- Next.js: standard for modern web apps, good for SEO, incremental adoption of SSR and static pages.
- FastAPI: async-first, automatic OpenAPI docs, high performance, Python compatibility with ML tooling.
- PostgreSQL: robust relational features, JSONB for semi-structured provenance fields.
- Celery + Redis: battle-tested for background jobs and workflows.
- Sentence-transformers / OpenAI: hybrid approach; embeddings via OpenAI during MVP, with local fallback.

## Data flow (simplified)
1. Scheduled job triggers provider sync (Celery beat).
2. Provider adapter fetches raw projects → stores raw data & provenance in `raw_projects` table (DB + S3 for documents).
3. Normalization pipeline runs (async job) → canonical `projects` table populated, with dedup keys.
4. Contractor discovery/enrichment jobs run → `contractors` canonical table populated.
5. Feature generation & matching runs → `matches` created with `match_features` and `explanation` stored.
6. UI displays matches; user marks feedback → `match_feedback` saved and optionally used for retraining.
7. Email generation (LLM) creates drafts stored in `emails` table; sending is queued to EmailProvider adapter when approved.

## Interfaces / Adapters (examples)
- BidProvider: fetch_projects(filters), get_project_details(id), health_check()
- ContractorProvider: search_companies(query), get_company_details(id), health_check()
- EnrichmentProvider: enrich_company(company_id), verify_email(email)
- Geocoder: geocode(address), batch_geocode(addresses), reverse(lat,lon)
- EmailProvider: send_email(email_id), get_status(message_id), verify_webhook(request)
- LLMProvider: generate(prompt, params), embed(texts)

Adapters must:
- Implement standardized return schemas
- Be resilient (retries, rate-limit handling)
- Tag every field with `source`, `confidence`, and `retrieved_at`

## Operational considerations
- Use feature flags for turning on auto-sending.
- Domain authentication and sending limits enforced at configuration level.
- Per-provider rate limiting and exponential backoff.
- Activity logging for all automated actions.

## Development ergonomics
- Local development via `docker-compose` for Postgres, Redis, and the app containers.
- `./scripts/bootstrap.sh` to create DB, run migrations, and seed demo data for local testing.

## Next docs to produce
- `docs/DATABASE_DESIGN.md` (detailed schema)
- `docs/ML_ARCHITECTURE.md` (matching engine details)
- `docs/SECURITY.md`, `docs/TESTING_STRATEGY.md`, `docs/OBSERVABILITY.md`, `docs/COST_MODEL.md`, `docs/RISK_REGISTER.md`, and `docs/IMPLEMENTATION_ROADMAP.md`.
