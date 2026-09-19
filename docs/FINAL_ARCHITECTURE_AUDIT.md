# Final Architecture Audit — ACE Services

## Executive Summary

I performed a hostile, pre-production architecture audit across the `docs/` set. The system design is coherent at a high level and correctly prioritizes government data for MVP, deterministic matching first, and an adapter-based provider architecture. However, I found a set of critical and high-priority issues that must be resolved before implementation begins. These include missing database tables and indexes, incomplete data-flow ownership and failure semantics, risky ML assumptions, weak email-sending safety controls, operational gaps around migrations/backups/secrets, and several provider-dependency and cost risks.

---

## Critical Problems

1) PROBLEM: No `contractors_raw` table or `match_features` table defined even though pipeline and docs reference them.
- WHY IT MATTERS: The pipeline and dedupe/merge logic require raw contractor records and a persisted feature vector table for training/analysis. Without these tables, ingestion and ML pipelines cannot be implemented reliably.
- AFFECTED DOCUMENTS: [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md), [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md)
- RECOMMENDED FIX: Add `contractors_raw` and `match_features` (or `features`) tables, define schema, unique constraints, and indexes. Add `entity_merge_history` table to track merges and provenance. Update DB doc.
- PRIORITY: Critical

2) PROBLEM: Vector storage strategy is inconsistent and under-specified (pgvector vs managed vector DB) and missing pgvector-specific indexes and migration notes.
- WHY IT MATTERS: Vector search performance and operational requirements differ dramatically between `pgvector` and managed vector DBs. Paging, indexing, and migration steps (Postgres extension installation, vector index creation) are required to avoid runtime failures and large query latencies.
- AFFECTED DOCUMENTS: [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md), [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md)
- RECOMMENDED FIX: Commit to one vector strategy for MVP (recommended: `pgvector` for small scale), add schema snippet, `CREATE EXTENSION pgvector;`, example index (`ivfflat` or `hnsw`) and capacity planning. Document migration steps and fallbacks to Pinecone/Weaviate.
- PRIORITY: Critical

3) PROBLEM: Email-sending safety controls are incomplete — no enforced human-approval gating, no idempotent send keys, no staging sending-disable flag, and missing unsubscribe handling details.
- WHY IT MATTERS: Accidental mass sending, duplicate sends, or sending to bounced addresses can cause severe deliverability damage and legal exposure. Production emailing must be gated and idempotent.
- AFFECTED DOCUMENTS: [docs/EMAIL_WORKFLOW.md](docs/EMAIL_WORKFLOW.md), [docs/SECURITY.md](docs/SECURITY.md), [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md)
- RECOMMENDED FIX: Add explicit `emails.send_state` and `emails.idempotency_key` usage; require `feature_flag.auto_send = false` by default; add pre-send validation steps (email verification, suppression check, domain warmup status) and mandatory human approval until confidence thresholds and low-volume tests pass. Add unsubscribe templates and link injection rules for all emails.
- PRIORITY: Critical

4) PROBLEM: Data-flow ownership, failure handling, retries, and owners are not specified per pipeline stage.
- WHY IT MATTERS: Without explicit owner/responsibility per stage, incidents and on-call routing are ambiguous, making recovery slow and risky.
- AFFECTED DOCUMENTS: [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md), [docs/BACKGROUND_JOBS.md](docs/BACKGROUND_JOBS.md), [docs/OPERATIONAL_PLAN.md](docs/OPERATIONAL_PLAN.md)
- RECOMMENDED FIX: For each pipeline stage (INGEST, VALIDATE, NORMALIZE, DEDUPE, ENRICH, FEATURE_GEN, MATCH, REVIEW, OUTREACH) add: primary owner role (team or job name), failure class handling, alerts, retry policy, and expected SLAs. Add runbook links in ops doc.
- PRIORITY: Critical

---

## High Priority Problems

5) PROBLEM: `value_compatibility`, `recent_activity_score`, and contractor historical project ranges are relied on but the sources don't reliably provide them initially.
- WHY IT MATTERS: Features required by deterministic scoring may be missing or sparse leading to unfair or meaningless scores.
- AFFECTED DOCUMENTS: [docs/MATCHING_ENGINE.md](docs/MATCHING_ENGINE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)
- RECOMMENDED FIX: Explicitly mark these features as "derived" and nullable in schema. Provide fallback rules (e.g., treat missing history as unknown and use conservative neutral weights). Add a feature-availability report and telemetry to measure coverage.
- PRIORITY: High

6) PROBLEM: Missing explicit handling for geocoding licensing constraints (Mapbox permanent storage) in data retention and provenance sections.
- WHY IT MATTERS: Storing geocodes without Mapbox permission may violate terms; production must avoid license violations.
- AFFECTED DOCUMENTS: [docs/data-sources.md](docs/data-sources.md), [docs/PROVIDER_CREDENTIALS.md](docs/PROVIDER_CREDENTIALS.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)
- RECOMMENDED FIX: Add a policy: mark geolocation provenance including provider and `licensed_for_persistent_storage` flag. If Mapbox token lacks enterprise permission, cache geocodes only for runtime use and store `geocode_provider` metadata instead of permanent lat/lon fields until license acquired.
- PRIORITY: High

7) PROBLEM: Missing deduplication/merge auditing table and reversible merge workflow
- WHY IT MATTERS: Auto-merges can silently corrupt canonical records. With mergers in place, audits and reversal must be possible.
- AFFECTED DOCUMENTS: [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md), [docs/CANONICAL_MODELS.md](docs/CANONICAL_MODELS.md)
- RECOMMENDED FIX: Add `entity_merge_history`/`merge_operations` table capturing inputs, outputs, confidence, user who triggered automated merge, and allow rollback tools. Add UI for manual review queue for low-confidence merges.
- PRIORITY: High

8) PROBLEM: No schema or storage for LLM prompt templates, prompt versioning, or generation provenance.
- WHY IT MATTERS: Without prompt/version tracking we cannot audit or reproduce generated emails, and prompt changes can cause silent behavior changes.
- AFFECTED DOCUMENTS: [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md), [docs/EMAIL_WORKFLOW.md](docs/EMAIL_WORKFLOW.md)
- RECOMMENDED FIX: Add `llm_prompts` (id, name, template, version, constraints, created_by) and record `prompt_id`, `prompt_version`, and `llm_response_metadata` with each generated email. Enforce storage of returned claim list and sources.
- PRIORITY: High

9) PROBLEM: Tests plan lacks contract tests and replay-safe fixtures for commercial provider behavior changes.
- WHY IT MATTERS: Provider APIs change; without contract tests or recorded fixtures integration will break silently.
- AFFECTED DOCUMENTS: [docs/TESTING.md](docs/TESTING.md), [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md)
- RECOMMENDED FIX: Add provider contract tests per adapter using VCR/fixture approach and a scheduled smoke test job for each provider credential. Add schema validation of provider payloads against expected minimal fields.
- PRIORITY: High

10) PROBLEM: No explicit table for campaign outcomes / conversions (award, shortlisted) to close feedback loop for supervised ML.
- WHY IT MATTERS: Supervised training requires labeled outcomes; currently `match_feedback` and `email_events` exist but no canonical `outcomes` table linking projects to awards.
- AFFECTED DOCUMENTS: [docs/MATCHING_ENGINE.md](docs/MATCHING_ENGINE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)
- RECOMMENDED FIX: Add `project_outcomes` (project_id, outcome_type, outcome_date, source, source_id, payload) and map to `matches` where appropriate.
- PRIORITY: High

---

## Medium Priority Problems

11) PROBLEM: Inconsistent naming and link references — `raw_projects` vs `projects_raw` appears in different docs.
- WHY IT MATTERS: Small but causes confusion when implementing migrations, tests, and code generation.
- AFFECTED DOCUMENTS: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)
- RECOMMENDED FIX: Standardize naming to `projects_raw` everywhere and update references.
- PRIORITY: Medium

12) PROBLEM: Observability lacks concrete retention and alert thresholds, and no log sampling strategy.
- WHY IT MATTERS: Without retention/cost planning logs and metrics can balloon costs or get purged too early for audits.
- AFFECTED DOCUMENTS: [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md), [docs/OPERATIONAL_PLAN.md](docs/OPERATIONAL_PLAN.md)
- RECOMMENDED FIX: Define retention windows per data class (logs, traces, metrics), set alert thresholds (job-failure rate %, bounce spikes), and add log sampling/rollups for high-volume events.
- PRIORITY: Medium

13) PROBLEM: No explicit health-check endpoints or readiness/liveness probe guidance for containers.
- WHY IT MATTERS: Kubernetes or other orchestrators rely on readiness/liveness probes to manage traffic and restarts.
- AFFECTED DOCUMENTS: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md), [docs/OPERATIONAL_PLAN.md](docs/OPERATIONAL_PLAN.md)
- RECOMMENDED FIX: Add endpoint specs (`/health`, `/ready`) and recommended probe checks (DB connectivity, Redis, S3). Document grace periods and restart policy.
- PRIORITY: Medium

14) PROBLEM: Cost model underestimates vector-search implications at scale and embedding costs for incremental updates.
- WHY IT MATTERS: Embeddings and vector search are a dominant cost driver as contractor/project corpus grows.
- AFFECTED DOCUMENTS: [docs/COST_MODEL.md](docs/COST_MODEL.md), [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md)
- RECOMMENDED FIX: Add a cost sensitivity table showing cost vs volumes and estimated break-even points for self-hosting embeddings (GPU) vs managed embedding costs. Add caching and precomputation policies.
- PRIORITY: Medium

15) PROBLEM: Provider fallback strategies are present but not documented as automated failover (e.g., if OpenAI fails, what happens to generate_email?).
- WHY IT MATTERS: Without automated fallbacks, a single provider outage can block key flows.
- AFFECTED DOCUMENTS: [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md), [docs/EMAIL_WORKFLOW.md](docs/EMAIL_WORKFLOW.md)
- RECOMMENDED FIX: Define clearly: primary provider, warm standby provider, retry/backoff, and deterministic fallback (static templates) for critical paths. Implement feature flag switch-over plan.
- PRIORITY: Medium

---

## Minor Problems

16) PROBLEM: `SYSTEM_ARCHITECTURE.md` references `./scripts/bootstrap.sh` but no script exists in repo (not checked) — document may be aspirational.
- WHY IT MATTERS: Missing developer scripts slow onboarding.
- AFFECTED DOCUMENTS: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)
- RECOMMENDED FIX: Add `scripts/bootstrap.sh` in repo or remove reference until implemented.
- PRIORITY: Minor

17) PROBLEM: Some documents referenced in `SYSTEM_ARCHITECTURE.md` list (e.g., `docs/IMPLEMENTATION_ROADMAP.md`) do not exist (file name mismatch with `docs/ROADMAP.md`).
- WHY IT MATTERS: Broken cross-links cause confusion.
- AFFECTED DOCUMENTS: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md), [docs/ROADMAP.md](docs/ROADMAP.md)
- RECOMMENDED FIX: Normalize filenames and update links.
- PRIORITY: Minor

18) PROBLEM: Minor inconsistency in enum naming conventions across docs (e.g., `status` values in `projects` vs `emails.status`).
- WHY IT MATTERS: Causes friction when codifying enums and building UIs.
- AFFECTED DOCUMENTS: [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md), [docs/CANONICAL_MODELS.md](docs/CANONICAL_MODELS.md)
- RECOMMENDED FIX: Publish a single `enums.md` listing canonical enum values.
- PRIORITY: Minor

---

## Contradictions Between Documents

- `projects_raw` vs `raw_projects`: inconsistent naming ([docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) vs [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)).
- `IMPLEMENTATION_ROADMAP.md` referenced but actual file is `ROADMAP.md` ([docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)).
- Vector DB strategy ambiguous: `pgvector` recommended in some places, while others list Pinecone/Weaviate without migration guidance ([docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)).
- Email provider choices: `FINAL_REPORT.md` recommends Postmark, but `PROVIDER_CREDENTIALS.md` lists Postmark as required; `EMAIL_WORKFLOW.md` is provider-agnostic. These are not direct contradictions but need alignment of ops responsibilities ([docs/FINAL_REPORT.md](docs/FINAL_REPORT.md), [docs/PROVIDER_CREDENTIALS.md](docs/PROVIDER_CREDENTIALS.md)).

---

## Missing Components

- `contractors_raw` table and `match_features` table (see Critical #1)
- `entity_merge_history`/`merge_operations` table and manual review queue
- `project_outcomes` table to capture award/shortlist/won labels for supervised ML
- `llm_prompts` table and `llm_response_metadata` storage
- `provider_events` generic table for non-email webhooks (or extend `email_events`) to centralize provider webhooks
- Explicit healthcheck/readiness probe specs
- `.env.example` file scaffold (not a code change, doc-only) referenced but not created

---

## Provider Risks

- OpenAI: critical for embeddings and email generation — must budget costs and implement detection for rate limits and spend caps. Provide deterministic fallback templates. ([docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md))
- Mapbox: geocoding licensing for persistent storage. Ensure Mapbox token has rights or avoid persistent storage of raw geocodes. ([docs/data-sources.md](docs/data-sources.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md))
- ConstructConnect / Dodge: high quality but require contracts — architecture currently lists them for post-MVP; ensure blocking dependencies are not accidentally scheduled into MVP work. ([docs/PROVIDER_CLASSIFICATION.md](docs/PROVIDER_CLASSIFICATION.md))
- Email provider: choose one and document deliverability plan, DKIM/SPF, and warmup steps before large sends. ([docs/EMAIL_WORKFLOW.md](docs/EMAIL_WORKFLOW.md), [docs/PROVIDER_CREDENTIALS.md](docs/PROVIDER_CREDENTIALS.md))

Fallbacks: Documented but must be operationalized (automated failover, rate-limit backoff, warm standby). ([docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md))

---

## Data Risks

- Sparse enrichment data: contractor historical projects and license completeness vary by source — many features will be low-coverage initially. ([docs/data-sources.md](docs/data-sources.md))
- Provenance and share-alike license issues: OpenCorporates free keys may require share-alike; legal review required before storing or using commercial data. ([docs/PROVIDER_CLASSIFICATION.md](docs/PROVIDER_CLASSIFICATION.md))
- Address normalization & geocoding accuracy: inconsistent addresses across sources may cause incorrect dedupe or distance calculations. Need normalization and confidence scores.

---

## ML Risks

- Assumes label data for supervised training exists — it does not. Training requires thousands of labeled match→conversion events; do not attempt supervised ranking until adequate labels collected and validated. ([docs/MATCHING_ENGINE.md](docs/MATCHING_ENGINE.md), [docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md))
- Semantic features depend on textual examples of previous contractor projects which may be missing or noisy.

Recommended minimal labeled-data requirements before Phase 3: 2k–5k positive events distributed across trades and geographies; more if imbalance exists.

---

## AI / Security Risks

- Prompt injection and hallucination mitigations are described but not enforced by schema or pipeline. Must add automated validation of claims produced by LLM (source existence, exact phrase matching) and store the claim→source mapping for audit. ([docs/SECURITY.md](docs/SECURITY.md), [docs/EMAIL_WORKFLOW.md](docs/EMAIL_WORKFLOW.md))
- LLM outputs should be subject to a mandatory human approval gate for email sending until validated by staged A/B tests.
- Secrets handling suggests env vars or vault — mandate production vault and rotation policy, and enforce role-based access.

---

## Email Risks

- Duplicate sends: no explicit idempotency semantics in `send_email` jobs.
- Bounced addresses: bounce handling exists but need automated suppression enforcement before send.
- Rate limits & provider errors: background job retry rules exist but need provider-specific throttling and circuit-breaker logic.

Recommended: `emails.idempotency_key`, `emails.sent_attempts`, pre-send checks, and circuit-breaker on provider errors.

---

## Performance Risks

- Embedding generation: high QPS and cost if performed per-candidate in real-time. Precompute and cache contractor embeddings; batch project embedding generation. ([docs/ML_ARCHITECTURE.md](docs/ML_ARCHITECTURE.md))
- Vector search on `pgvector`: fine for small corpus; at scale requires ANN indexes and tuning or migration to managed vector DB.
- Geocoding: batch geocoding with rate-limited pools needed to avoid provider throttling and cost spikes.

---

## Cost Risks

- Main cost drivers: commercial feed subscriptions, OpenAI embedding calls, and email volume. Without caps and batching embedding calls will consume budget quickly.
- Recommend conservative default caps, precomputing embeddings for the contractor corpus only, and measuring real volumes before adding commercial feeds.

---

## MVP Scope Corrections

Remove from MVP:
- Supervised ranking training & production serving
- Paid commercial feeds (ConstructConnect/Dodge) unless ACE procures account prior to development
- Full email campaign automation (keep manual approval and single-send flows)
- Advanced analytics and CRM integrations

Keep in MVP:
- SAM.gov ingestion + USAspending enrichment
- OpenCorporates contractor enrichment
- Deterministic matching and an operator UI for review
- Postmark (or chosen email provider) for manual/approved sends
- Mapbox for geocoding with licensing checks

---

## Recommended Architecture Changes

1. Add missing DB tables: `contractors_raw`, `match_features`, `entity_merge_history`, `project_outcomes`, and `llm_prompts`.
2. Standardize naming and enums in a single `docs/ENUMS.md` and regenerate docs references.
3. Commit to `pgvector` for MVP with concrete migration/install notes and an indexing plan; include fallback to managed vector DB and migration guide.
4. Implement strict email-safety controls: idempotency keys, suppression enforcement, human-approval default, and staging flags.
5. Add per-stage ownership, failure semantics, and runbook links to pipeline design and ops docs.
6. Add prompt/version tracking and require storage of LLM claim lists and sources for each generated email.
7. Add provider contract tests, scheduled smoke tests, and provider-credential health checks.
8. Add cost-control telemetry with hard caps and daily budgets for embeddings and email sends.

---

## Recommended Implementation Order (smallest vertical slices)

1. Core infra: Postgres + extensions (PostGIS, pgvector), Redis, S3; baseline CI pipeline and migrations tool (Alembic) + health/readiness endpoints.
2. Provider adapters (read-only): SAM.gov adapter + `projects_raw` ingestion and `projects` normalization; store provenance.
3. Contractors: OpenCorporates adapter + `contractors_raw` ingestion and canonicalization.
4. Deterministic matching: feature generation, `match_features` persistence, `matches` creation, and UI to review matches.
5. Email drafts: `generate_email` using deterministic templates (no LLM), UI review, manual `send_email` via trusted provider (disabled by default). Implement idempotency/suppression.
6. Observability & runbooks: metrics, alerts, backup and restore, smoke tests for provider adapters.
7. Embeddings & semantic stage: enable OpenAI embeddings, pgvector indexing, and hybrid scoring once coverage and budgets are validated.
8. Supervised ML & automation only after sufficient labeled outcomes (`project_outcomes`) collected.

---

## Final Go/No-Go Assessment

- GO for documentation-driven implementation readiness: The docs form a solid foundation but several critical holes must be addressed before coding.
- HARD NO for beginning automated emailing and supervised ML training until the critical issues above are resolved (DB schema gaps, email safety, explicit runbooks, prompt provenance, and vector strategy).

---

For each remediation above I can produce concrete patches: DB migration SQL, `docs/ENUMS.md`, `docs/OWNER_RESPONSIBILITIES.md`, `docs/LLM_PROMPTS_SPEC.md`, and an initial `.env.example`. Confirm which remediation artifacts you want me to scaffold next; I will not write application code but can produce migration and doc artifacts on request.
