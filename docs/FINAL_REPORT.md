# ACE Services — Final Architecture & Product-Definition Report

This final report collects the architecture decisions, MVP choices, required credentials, and next steps so ACE can approve an implementation plan.

1. Executive summary
- Purpose: Discover construction bid opportunities, match contractors, generate personalized outreach, and track outreach pipeline.
- MVP approach: Prioritize public federal sources (SAM.gov + USAspending) plus OpenCorporates for company normalization; use free/local fallbacks for geocoding and LLM/embedding functionality during $0 development. Paid services (Mapbox, Postmark, OpenAI) are optional POST-MVP.

2. MVP provider selections (confirmed)
- Projects: SAM.gov (primary), USAspending (enrichment)
- Contractor/company enrichment: OpenCorporates
- Geocoding: Mapbox
- Email: Postmark (primary) — alternative: SendGrid/Mailgun/SES
- LLM/Embeddings: OpenAI (primary) — fall back: Cohere or local sentence-transformers

3. System architecture (summary)
- Modular monolith backend (Python + FastAPI), Postgres (JSONB + PostGIS), Celery + Redis for background jobs, vector-capable storage (pgvector) for embeddings, S3-compatible document storage, React/Next.js + TypeScript frontend.
- See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) and [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md) for diagrams and dataflow.

4. Data sources & provider classification
- See [docs/data-sources.md](docs/data-sources.md) and [docs/PROVIDER_CLASSIFICATION.md](docs/PROVIDER_CLASSIFICATION.md). Commercial feeds (ConstructConnect, Dodge) are high quality but require paid contracts and are listed as B (requires account).

5. Canonical data model & DB design
- Postgres canonical models for `projects`, `contractors`, `matches`, `emails`, and provenance JSONB; PostGIS for geospatial queries; UUID PKs; soft-delete semantics.
- See [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) and [docs/CANONICAL_MODELS.md](docs/CANONICAL_MODELS.md).

6. Matching engine design
- Phased plan: Deterministic scoring (MVP) → Hybrid semantic (embeddings) → Supervised ranking (LightGBM/XGBoost).
- Store `matches` with `features`, `explanation`, and `model_version` for auditability.
- See [docs/MATCHING_ENGINE.md](docs/MATCHING_ENGINE.md).

7. ML architecture & storage
- Embeddings via OpenAI stored in `pgvector` (pgvector) or managed vector DB; offline training pipeline for supervised ranking; model registry via `ml_models` table.
- See [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md).

8. Ingestion & pipeline
- Provider adapters write to `projects_raw` then normalize/deduplicate/enrich; pipeline stages implemented as Celery tasks with job_runs tracking.
- See [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md).

9. Email workflow & adapter pattern
- LLM-driven `generate_email` job creates drafts; user review; `send_email` job uses provider adapters; webhooks update `email_events` and `emails.status`.
- See [docs/EMAIL_WORKFLOW.md](docs/EMAIL_WORKFLOW.md).

10. Security posture
- Secrets in vault/ENV; OAuth2/JWT for API; RBAC; webhook verification; prompt-injection mitigations for LLMs.
- See [docs/SECURITY.md](docs/SECURITY.md).

11. Testing & QA
- Unit tests with `pytest`, integration tests using Testcontainers, contract tests for provider adapters, CI gating for all merges.
- See [docs/TESTING.md](docs/TESTING.md).

12. Observability & operations
- Metrics: job rates, match counts, email sends, bounce rates, embedding costs; logs: structured JSON; traces for long-running jobs; alerts for provider auth errors and high failure rates.
- See [docs/OPERATIONAL_PLAN.md](docs/OPERATIONAL_PLAN.md) and [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md).

13. Cost model (high-level)
- Major costs: commercial feed subscriptions (ConstructConnect/Dodge), OpenAI embeddings, Mapbox geocoding, email provider sends, hosting (DB, Redis, S3), operational monitoring. See [docs/COST_MODEL.md](docs/COST_MODEL.md) for details and cost control suggestions.

14. Risk register & mitigations
- Top risks: paywalled data feeds, licensing/redistribution limits, email deliverability, data quality, PII regulations, LLM hallucination. Mitigations include legal review, suppression lists, domain verification, provenance, and staged gating.
- See [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md).

15. Required credentials & `.env` variables
- See [docs/PROVIDER_CREDENTIALS.md](docs/PROVIDER_CREDENTIALS.md) for the enumerated ENV variables and notes about which ones are required for MVP development vs optional.

16. Implementation sequence & timeline (next steps)
- Short-term (weeks): Provision keys (OpenAI, Mapbox, Postmark), implement provider adapters for SAM.gov + OpenCorporates, build ingestion pipeline, deterministic matching, basic UI for review and email send.
- Mid-term (months): Add embeddings/semantic matching, contractor enrichment, supervised model training, campaign automation, paid commercial feeds.
- See [docs/ROADMAP.md](docs/ROADMAP.md).

17. Approvals & dependencies
- ACE must confirm: (a) whether to purchase ConstructConnect/Dodge now or postpone to later phases, (b) primary email domain and Postmark/SendGrid account for deliverability setup, (c) OpenAI account for embeddings.

18. Deliverables included
- This report plus the following docs added/updated in `docs/`: `SYSTEM_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `MATCHING_ENGINE.md`, `PIPELINE_DESIGN.md`, `EMAIL_WORKFLOW.md`, `ML_ARCHITECTURE.md`, `SECURITY.md`, `TESTING.md`, `OPERATIONAL_PLAN.md`, `ROADMAP.md`, and the supporting files created alongside this report.

---

Sign-off: Reply with confirmation of MVP provider choices and which commercial feed (if any) ACE will subscribe to, and whether you want me to scaffold the provider-adapter skeletons and `.env.example` next.
