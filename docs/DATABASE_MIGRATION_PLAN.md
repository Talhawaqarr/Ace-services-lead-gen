# Database Migration Plan — ACE Services

Purpose: Document required schema changes and migration strategy to address the Final Architecture Audit. This is documentation-only; do NOT execute migrations from these notes without formal change control.

## Summary of required schema changes
1. New tables
- `contractors_raw` — store original contractor provider payloads
  - id UUID PK
  - source VARCHAR
  - source_id VARCHAR
  - raw JSONB
  - retrieved_at TIMESTAMP
  - sync_run_id UUID FK -> source_sync_runs
  - created_at, updated_at
  - unique constraint: (source, source_id)

- `match_features` — store computed features used for matching and training
  - id UUID PK
  - match_id UUID FK -> matches (nullable if feature precomputed before match)
  - project_id UUID FK
  - contractor_id UUID FK
  - features JSONB
  - embedding_vector vector (pgvector) nullable
  - vector_dim INT
  - created_at, updated_at
  - indexes: idx_match_features_project_id, idx_match_features_contractor_id, vector index (ivfflat/hnsw) as appropriate

- `entity_merge_history` — auditable record of merges
  - id UUID PK
  - entity_type VARCHAR
  - primary_entity_id UUID
  - merged_entity_ids JSONB array
  - merge_confidence NUMERIC
  - merge_rules JSONB
  - initiated_by VARCHAR (system|user)
  - initiated_at TIMESTAMP
  - reversed_at TIMESTAMP NULLABLE
  - reversal_payload JSONB NULLABLE

- `project_outcomes` — canonical outcome labels for projects
  - id UUID PK
  - project_id UUID FK
  - outcome_type ENUM (shortlisted, awarded, lost, withdrawn, other)
  - outcome_date TIMESTAMP
  - source VARCHAR
  - source_id VARCHAR
  - payload JSONB
  - created_at, created_by
  - unique constraint: (project_id, outcome_type, source, source_id)

- `llm_prompts` and `llm_responses`
  - `llm_prompts`: id UUID, name, template TEXT, metadata JSONB, version INT, created_by, created_at
  - `llm_responses`: id UUID, prompt_id FK, prompt_version INT, request_payload JSONB, response_payload JSONB, provider_metadata JSONB, created_at

2. Altered tables
- `emails` table additions
  - add `send_state` ENUM (draft, approved, queued, sent, cancelled)
  - add `idempotency_key` VARCHAR NULLABLE
  - add index on `idempotency_key`

- `projects` / `contractors` add `geocode_provider` and `geocode_license_ok` boolean flag

3. Indexes & Extensions
- Ensure PostGIS present and GIST index on geography(point(latitude, longitude)).
- Enable `pgvector` extension for `match_features.embedding_vector`.
- Add ANN index per chosen method (e.g., `ivfflat` or `hnsw`) with tuning parameters documented.

4. Enums
- Define canonical enums centrally (see `docs/DOMAIN_STATES.md`). Migrations must create enums before using them in columns.

## Data migration concerns
- Backfilling `contractors_raw`: re-ingest existing contractor sources in batches; use idempotent `source+source_id` upsert keys.
- Backfilling embeddings: generate embeddings in batches with rate-limited worker and monitor cost; store vector_dim in `match_features`.
- Backfilling project outcomes: ingest from USAspending where available; allow manual operator input to seed outcomes.

## Rollback strategy
- Use transactional migrations where possible.
- For extension installs (pgvector), ensure empty or non-critical state before dropping extension.
- For table additions, rollbacks are safe (DROP TABLE) but only after ensuring no dependent data exists; provide scripts to export/import data.

## Migration window & safety
- Perform migrations in a maintenance window with read-only mode for ingestion if needed.
- Validate migrations on staging with production snapshot (anonymized) prior to production.

## Migration checklist (pre-implementation)
- Create and review migration SQL / Alembic scripts and generate reversible steps.
- Add integration tests exercising migrations and rollback on a CI-managed Postgres container.
- Notify stakeholders and prepare backups (DB snapshot) before applying.

---

This migration plan documents the schema changes required to remediate audit findings. Implementation must follow change-control processes and tests.