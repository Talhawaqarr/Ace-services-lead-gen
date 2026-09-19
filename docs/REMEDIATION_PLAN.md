# Remediation Plan — ACE Services

This document maps each Critical and High Priority issue from `docs/FINAL_ARCHITECTURE_AUDIT.md` to a concrete remediation plan that is documentation-only (no application code changes). Each entry includes: issue, affected component, why it matters, exact remediation, files that will eventually change, dependencies, migration requirements, tests required, and completion criteria.

## 1) Missing raw contractor table and match_features table
- Issue: `contractors_raw` and `match_features` tables are not defined.
- Affected component: Database, Ingestion pipeline, ML pipeline.
- Why it matters: Ingestion and ML pipelines require a raw contractor store and persisted features to function and to enable reproducible training.
- Exact remediation (doc/config only): Create `docs/DATABASE_MIGRATION_PLAN.md` entries that define the new tables, types, indexes, uniqueness rules, and migration strategy; define `docs/TEST_FIXTURES.md` entries for contractor ingestion and feature generation fixtures; update `docs/PIPELINE_DESIGN.md` and `docs/ML_ARCHITECTURE.md` to reference the new tables.
- Files that will eventually change: `database migrations` (SQL/Alembic), `models` (SQLAlchemy), `pipeline` code.
- Dependencies: None for docs; implementation depends on Postgres, Alembic, and a migration window.
- Migration requirements: Backfill plan for existing contractor data by reprocessing `projects_raw`/external sources into `contractors_raw` using idempotent jobs; define batch window and throttling.
- Tests required: Integration tests for ingestion producing `contractors_raw`, and unit tests for feature generation producing `match_features` rows.
- Completion criteria: `docs/DATABASE_MIGRATION_PLAN.md` contains full schema, and `docs/TEST_FIXTURES.md` includes tests for all key cases.

## 2) Vector storage strategy under-specified
- Issue: pgvector vs managed vector DB unclear; missing install/migration docs.
- Affected component: ML, Database, Deployment.
- Why it matters: Different operational profiles and index requirements cause runtime failures and performance issues.
- Exact remediation: Produce `docs/ML_VECTOR_STRATEGY.md` specifying MVP choice (`pgvector`), SQL required (`CREATE EXTENSION pgvector;`), index types, recommended parameters, fallback provider instructions, and capacity planning. Update `docs/ML_ARCHITECTURE.md` to reference the chosen strategy.
- Files that will eventually change: DB migration scripts to enable `pgvector`, configuration for vector dimension (`PGVECTOR_DIM`), and monitoring dashboards.
- Dependencies: Postgres extension installation permission on managed DB; CI integration for migration tests.
- Migration requirements: Add instructions to create extension and example migration snippets; include rollback steps to drop extension only if empty.
- Tests required: Unit tests for embedding store/lookup, integration test for ANN query correctness.
- Completion criteria: `docs/ML_VECTOR_STRATEGY.md` exists and `docs/ML_ARCHITECTURE.md` references it.

## 3) Email-sending safety controls incomplete
- Issue: No enforced human-approval gating, idempotency, suppression enforcement, or pre-send checks documented.
- Affected component: Email workflow, Security, Ops.
- Why it matters: High risk of accidental mass sends, legal/regulatory failure, and deliverability damage.
- Exact remediation: Create `docs/EMAIL_SAFETY.md` specifying pre-send checks, `emails` table extensions (`send_state`, `idempotency_key`), approval process, controlled automation mode, and manual gating. Add `docs/RUNBOOKS.md` entries for suspicious email activity and bounce spikes.
- Files that will eventually change: DB migrations, `EMAIL_WORKFLOW.md`, UI workflows.
- Dependencies: Provider webhooks (bounce handling), suppression list design.
- Migration requirements: Backfill existing `emails` rows with default `send_state=draft` and null `idempotency_key`.
- Tests required: Fixtures for suppressed email, duplicates, invalid emails, and failed sends.
- Completion criteria: `docs/EMAIL_SAFETY.md` and `docs/RUNBOOKS.md` updated with actionable steps.

## 4) Data-flow ownership and failure semantics missing
- Issue: Pipeline stages lack owners, SLAs, and detailed failure actions.
- Affected component: Pipeline, Background jobs, Operations.
- Why it matters: Ambiguous ownership causes slow incident response and unclear remediation steps.
- Exact remediation: Create `docs/OWNER_RESPONSIBILITIES.md` mapping each pipeline stage to owner roles, expected SLAs, alert conditions, and runbook links. Update `docs/PIPELINE_DESIGN.md` with per-stage failure semantics.
- Files that will eventually change: Ops runbooks, alerting configurations.
- Dependencies: Organizational assignment of roles.
- Migration requirements: None.
- Tests required: N/A (doc-only), validate runbook completeness via tabletop run.
- Completion criteria: `docs/OWNER_RESPONSIBILITIES.md` created and referenced from pipeline doc.

## 5) Feature availability for deterministic matching
- Issue: `value_compatibility` and `recent_activity_score` are assumed available but data sparse.
- Affected component: Matching engine, Database.
- Why it matters: Missing features can bias or invalidate matching.
- Exact remediation: Add feature coverage metrics to `docs/OBSERVABILITY_CONTRACT.md` and add fallback rules to `docs/MATCHING_CONTRACT.md` to handle null/missing features. Document in `docs/TEST_FIXTURES.md` test cases for missing-data matching behavior.
- Files that will eventually change: matching code, monitoring dashboards.
- Dependencies: Telemetry for feature coverage.
- Migration requirements: None.
- Tests required: Unit tests for scoring with missing features.
- Completion criteria: `docs/MATCHING_CONTRACT.md` includes fallback rules and `docs/OBSERVABILITY_CONTRACT.md` specifies coverage metrics.

## 6) Geocoding licensing constraints
- Issue: Mapbox permanent storage licensing not enforced in docs.
- Affected component: Data storage, Legal/Compliance.
- Why it matters: Potential license violation if geocodes stored without permission.
- Exact remediation: Update `docs/PROVIDER_CONTRACTS.md` and `docs/PROVIDER_CREDENTIALS.md` to include `geocode_persistent_storage_allowed` flag; add `docs/DATABASE_MIGRATION_PLAN.md` note to conditionally populate `latitude/longitude` only when provider license allows. Document checklists in `docs/ENVIRONMENT.md` for Mapbox account type.
- Files that will eventually change: ingestion pipeline and DB population logic.
- Dependencies: Legal/contract confirmation from Mapbox account.
- Migration requirements: If later enabling persistent storage, run idempotent geocode backfill job.
- Tests required: Tests ensuring geocode storage respects flag.
- Completion criteria: `docs/PROVIDER_CONTRACTS.md` and `docs/DATABASE_MIGRATION_PLAN.md` updated.

## 7) Deduplication/merge auditability
- Issue: No `entity_merge_history` table or reversible workflow.
- Affected component: Database, UI, Pipeline.
- Why it matters: Auto-merges risk data loss; audits and reversals needed.
- Exact remediation: Add `entity_merge_history` schema to `docs/DATABASE_MIGRATION_PLAN.md` and define `docs/RUNBOOKS.md` procedures for manual reversal. Update `docs/CANONICAL_MODELS.md` with merge logging expectations.
- Files that will eventually change: DB migrations and admin UI.
- Dependencies: DB schema changes.
- Migration requirements: None immediate; implement when merge logic added.
- Tests required: Fixtures for merge scenarios and reversal.
- Completion criteria: `docs/DATABASE_MIGRATION_PLAN.md` defines table and `docs/RUNBOOKS.md` describes reversal steps.

## 8) LLM prompt/version tracking missing
- Issue: No `llm_prompts` table or prompt-version tracking.
- Affected component: ML, Email generation, Audit.
- Why it matters: Cannot reproduce or audit generated emails or prompt drift.
- Exact remediation: Define `llm_prompts` and `llm_responses` schemas in `docs/DATABASE_MIGRATION_PLAN.md`, create `docs/LLM_CONTRACT.md` defining required metadata, and update `docs/EMAIL_WORKFLOW.md` to record prompt_id and prompt_version with generated emails.
- Files that will eventually change: DB migrations, email generation jobs.
- Dependencies: None for docs; implementation will depend on LLM provider SDK.
- Migration requirements: None.
- Tests required: Unit tests ensuring prompt storage and retrieval.
- Completion criteria: `docs/LLM_CONTRACT.md` and migration plan updated.

## 9) Contract tests for provider adapters
- Issue: No provider contract tests or smoke checks defined.
- Affected component: Provider adapters, CI.
- Why it matters: Provider API changes can silently break ingestion and enrichment.
- Exact remediation: Add `docs/TEST_FIXTURES.md` entries for provider contract tests, add `docs/PROVIDER_CONTRACTS.md` specifying expected minimal fields and health-check endpoints, and add `docs/RUNBOOKS.md` for adapter failures.
- Files that will eventually change: Test suites and CI configuration.
- Dependencies: Provider API specs.
- Migration requirements: None.
- Tests required: Contract tests for SAM.gov, OpenCorporates, Mapbox, email provider webhooks.
- Completion criteria: `docs/PROVIDER_CONTRACTS.md` and `docs/TEST_FIXTURES.md` updated.

## 10) Missing project outcomes table
- Issue: No canonical `project_outcomes` table to record award/shortlist/won events.
- Affected component: Database, ML training pipeline.
- Why it matters: Supervised models need labeled outcomes; without them training is impossible.
- Exact remediation: Add `project_outcomes` schema to `docs/DATABASE_MIGRATION_PLAN.md` and document sources for outcomes (USAspending, state registries, manual input) in `docs/PIPELINE_DESIGN.md`.
- Files that will eventually change: DB migrations, data ingestion adapters.
- Dependencies: Availability of reliable outcome sources.
- Migration requirements: Backfill strategy and manual entry UI.
- Tests required: Fixtures for outcome ingestion, linking to matches.
- Completion criteria: Migration plan includes table and backfill approach.

---

## Roadmap alignment
Each remediation will be inserted into `docs/ROADMAP.md` before the implementation phases they affect. See `docs/ROADMAP.md` updates scheduled in the remediation TODOs.

---

This document maps each critical and high-priority item to an actionable doc-only remediation. After you confirm, I'll scaffold the following files next (docs-only):
- `docs/DATABASE_MIGRATION_PLAN.md`
- `docs/DOMAIN_STATES.md`
- `docs/PROVIDER_CONTRACTS.md`
- `docs/LLM_CONTRACT.md`
- `docs/MATCHING_CONTRACT.md`
- `docs/EMAIL_SAFETY.md`
- `docs/ENVIRONMENT.md` and `.env.example`
- `docs/SECURITY_CONTROLS.md`
- `docs/OBSERVABILITY_CONTRACT.md`
- `docs/TEST_FIXTURES.md`
- `docs/RUNBOOKS.md`
- Update `docs/ROADMAP.md` to include remediation milestones
- `docs/CLAUDE.md` (policy doc)

I will not create migrations or application code yet. Confirm to proceed with scaffolding these documents.