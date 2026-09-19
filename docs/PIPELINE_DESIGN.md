# Data Pipeline Design

This document specifies the staged data pipeline for project and contractor data ingestion, normalization, deduplication, enrichment, and feature generation.

Stages:
1. INGEST (provider adapters)
   - Input: external API responses, webhooks
   - Output: `projects_raw` / `contractors_raw` entries and S3-stored documents
   - Failure handling: log and mark `source_sync_runs` with partial failures; retry according to provider-specific rate limits
   - Idempotency: use `source+source_id` dedupe keys

2. RAW STORAGE
   - Store original provider payload and document blobs separately.
   - Retain raw for audits and reprocessing.

3. VALIDATE
   - Basic schema checks (required: name, location, date)
   - Normalize date formats, address fields
   - Mark invalid records and push to `source_sync_runs.errors`

4. NORMALIZE
   - Map provider fields to canonical fields
   - Extract trades, project_type using rule-based mapping and ML classifier when configured
   - Geocode addresses (batch via geocoder adapter)
   - Output: `projects` canonical records

5. DEDUPLICATE / ENTITY RESOLUTION
   - Compute dedupe keys (normalized name, address hash, domain)
   - Merge duplicates cautiously with confidence thresholds
   - Keep provenance chains linking merged records

6. ENRICH
   - Enrichment tasks: OpenCorporates lookup, Google Places, state license checks
   - Store enriched fields with source & confidence
   - Email verification (e.g., mailbox validation) optional

7. CANONICAL DB
   - Insert/update canonical `projects`, `contractors`
   - For changed records, write audit entries

8. FEATURE GENERATION
   - Compute deterministic features for matching (distance, trade overlap)
   - Generate embeddings for text fields via LLM/embedding provider
   - Persist features to `match_features`

9. MATCH
   - Run matching algorithm (deterministic/hybrid)
   - Write `matches` and `explanations`

10. REVIEW / FEEDBACK
   - Expose to UI for human review; store `match_feedback`
   - Feedback used for model training (Phase 3)

Logging & Observability
- Each stage emits structured logs and metrics (processing time, input counts, failures).
- Pipeline orchestrator writes `job_runs` entries with statuses.

Retries & Backoff
- Use exponential backoff for provider API calls.
- Use job DLQ (dead-letter queue) for persistent failures and alerting.

Idempotency
- Jobs must use `source+source_id` as idempotency key for upserts.
- Document-processing should generate deterministic text extraction IDs to avoid reprocessing duplicates.

Security
- External data treated as untrusted; sanitize all inputs before storing or processing.
- Document storage in S3 with restricted access (signed URLs).

This pipeline is implemented as Celery tasks orchestrated by a scheduler (Celery beat) and monitored by job_runs and metrics.
