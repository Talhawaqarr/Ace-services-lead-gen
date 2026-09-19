# Data Ingestion (Phase 5)

## CURRENT IMPLEMENTATION

This repository now includes the first clean ingestion pipeline for legitimate public-source project data, using a local fixture-backed provider that mirrors the public USAspending-style contract without requiring paid services or API keys.

### Architecture

Raw public source data enters through a provider adapter, then passes through:
- raw persistence
- validation
- normalization
- deduplication
- canonical project persistence
- existing matching engine
- existing review workspace

The adapter boundary is kept separate from the canonical model and matching logic; no ingestion code directly calls the matcher or the UI.

### Source selected for Phase 5

- Source: USAspending-style public federal award data (fixture-backed, reproducible)
- Access method: local fixture/provider adapter representing the public API contract
- Live verification: not performed with a real API because the repo is restricted to $0 and does not assume credentials or network access
- Credentials required: none for local development

### Phase 9 addition: SAM.gov fixture-backed contract

The repository now also includes a SAM.gov-shaped fixture provider for deterministic local use without live API access.

Current implementation notes:
- source name: `samgov`
- access method: local fixture only, no HTTP requests, no credentials
- source identity rule: prefer `solicitationNumber` when present; otherwise fall back to `source_id`
- raw payloads retain the original `reponseDeadLine` field exactly as supplied by the source
- normalized internal representation uses `response_deadline` for the derived field name
- `data.award.amount` is preserved as award metadata and is never silently treated as `estimated_value`
- construction relevance is kept as an explicit provenance field rather than a hidden classifier side effect

This keeps the current canonical `Project` model stable while still supporting locally validated SAM.gov-shaped records.

### Raw model

The raw layer stores source metadata and the original payload as JSON, along with ingestion status and any validation error details.

Fields:
- source
- source_id
- fetched_at
- raw_payload
- status
- error_detail

This keeps the original record available for debugging normalization issues without mutating the canonical schema.

### Canonical project model

The runtime canonical Project model remains the existing one used by the app today, with source/source_id provenance and matching-friendly fields.

Supported fields in the actual runtime model:
- id
- name
- source
- source_id
- city
- state
- latitude
- longitude
- trades
- bid_date
- estimated_value
- provenance

Future project fields remain outside the current runtime model and are intentionally not added here.

### Normalization behavior

Normalization is intentionally conservative:
- trim whitespace from text values
- uppercase state codes
- title-case city names
- keep date strings in their original normalized format
- convert numeric values safely when possible
- keep missing information as NULL/UNKNOWN instead of inventing defaults

### Validation behavior

A record is rejected when required identity data is invalid or absent, such as:
- missing project title
- missing source or source_id
- invalid state representation
- impossible values that do not fit the runtime model

This is recorded in the raw row status and error detail.

### Deduplication behavior

The active strategy for Phase 5 is deterministic idempotency based on:
- same source + same source_id

This prevents duplicate raw records and duplicate canonical projects during repeated ingestion.

### Idempotency behavior

Re-running the same ingestion against the same source fixture will not create a second canonical project. A repeat record is marked as duplicate and the run summary reflects that.

### Ingestion summary

The ingestion service returns a summary object with:
- source
- records_fetched
- accepted
- rejected
- duplicates
- errors
- created
- updated

This makes the pipeline observable and testable without hiding failures.

### Ingestion run tracking

The minimal ingestion-run table records:
- source
- started_at
- finished_at
- status
- records_fetched
- accepted
- rejected
- duplicates
- errors

This is intentionally minimal and does not become a large ETL monitor.

### Source adapter architecture

The provider contract is represented by the existing provider interface pattern and a local adapter implementation in [src/providers/usaspending.py](src/providers/usaspending.py).

The adapter returns raw source records. The ingestion service performs the lifecycle:
- fetch
- validate
- normalize
- deduplicate
- persist

This keeps provider logic isolated from business logic.

### Future / not implemented

The following remain FUTURE and are intentionally not added in Phase 5:
- broad contractor discovery
- AI/embeddings
- advanced entity resolution across sources
- paid commercial feeds
- public API or network access requiring credentials
- heavy ETL dashboards

### Local reproducibility

This Phase 5 pipeline can run without network access because it uses deterministic local fixtures in [docs/fixtures/phase5_usaspending_projects.json](docs/fixtures/phase5_usaspending_projects.json).

## FUTURE

- connect to a real public API when access model and credentials are available
- handle additional public sources with the same adapter contract
- build richer cross-source deduplication when the data model requires it
- add contractor enrichment once distinct project discovery is stable
