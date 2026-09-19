# Background Processing Design

Background tasks power ingestion, enrichment, matching, embeddings, and email sending. This document outlines job types, states, retry rules, and idempotency.

## Job categories
- `sync_provider` — fetch projects from a BidProvider
- `process_project_raw` — validate and normalize raw project
- `geocode_address` — geocode addresses in batches
- `enrich_contractor` — call enrichment providers
- `compute_embeddings` — request embedding generation for texts
- `generate_match_features` — deterministic feature computation
- `run_matching` — run match scoring for a project
- `generate_email` — LLM-driven personalization
- `send_email` — queue to EmailProvider adapter
- `webhook_processor` — handle provider webhooks and map to events

## Job state model
- `PENDING` — queued
- `IN_PROGRESS` — running
- `COMPLETED` — success
- `FAILED` — transient failure, eligible for retry
- `PERMANENT_FAILURE` — failed after retries; move to DLQ

## Retry rules
- Exponential backoff with capped limits (e.g., 5 attempts: 1m, 5m, 20m, 1h, 4h)
- For rate limit responses, use `Retry-After` header when present
- For auth errors (401/403), fail fast and alert (no retry)

## Idempotency
- Use `idempotency_key` for each job based on `source+source_id` or `object_type+object_id`
- Upserts must be write-safe (use database upsert semantics)

## Dead-Letter Behavior
- After max retries, mark job as `PERMANENT_FAILURE`, write to `job_runs` with error payload, and optionally notify on-call engineer.

## Concurrency
- Worker concurrency configurable via environment variables. Use rate-limited pools per provider to avoid hitting quotas.

## Timeouts
- Each job type defines a soft timeout. Longer-running jobs (document parsing, embeddings batch) may have higher timeouts.

## Observability
- Each job emits structured logs and metrics (duration, attempts, error types).
- Expose a `Jobs` admin page with job list, filters, and retry control for operators.

## Security
- Jobs that call external providers use stored credentials from environment or secret store.
- Webhook jobs verify signatures before processing.

This background job framework is implemented with Celery+Redis, task definitions in `workers/`.
