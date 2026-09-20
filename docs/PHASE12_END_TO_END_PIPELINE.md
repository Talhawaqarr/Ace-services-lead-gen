# Phase 12 — Offline End-to-End Pipeline

## Goal

Prove one complete local workflow from an opportunity fixture through contractor discovery, deterministic matching, persisted review state, and audit logging.

## Flow

```
SAM.gov-shaped opportunity fixture
        ↓
opportunity ingestion
        ↓
canonical Project
        ↓
SAM.gov-shaped contractor fixture
        ↓
canonical Contractor
        ↓
candidate discovery
        ↓
deterministic matcher
        ↓
MatchRecord
        ↓
human review
        ↓
MatchReviewAudit
```

## Current implementation

`src/pipeline/service.py` provides:

- `discover_contractors()`
- `run_local_fixture_pipeline()`

Discovery is intentionally non-scoring. It returns canonical contractor candidates; the existing deterministic matcher owns ranking, score, confidence, and evidence.

The orchestration uses the existing ingestion and review services rather than duplicating their logic.

## Idempotency

Re-running the same fixture pipeline must not create duplicate:

- canonical Projects
- canonical Contractors
- MatchRecords for the same matcher version

Existing ingestion and matching identity rules remain authoritative.

## Review

Generated matches begin as `UNREVIEWED`. The existing review service can transition a match to `APPROVED`, `REJECTED`, or `SKIPPED`, with every change recorded in `MatchReviewAudit`.

Approval does not send email or trigger an external action.

## Development constraints

This phase is offline and $0:

- no live SAM.gov calls
- no API keys
- no paid provider
- no email
- no LLM
- no embeddings
- no external contractor scraping

The fixture data is synthetic and remains explicitly labeled as such.

## Scope boundary

This phase does not claim that contractor discovery is a production-grade external search engine. It proves the local pipeline contract and isolates the place where a future ContractorProvider can supply external candidates.

Future work can replace or augment the fixture provider without changing the matching/review contracts.
