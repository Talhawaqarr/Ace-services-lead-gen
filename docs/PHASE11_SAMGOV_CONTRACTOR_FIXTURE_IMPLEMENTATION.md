# Phase 11 — SAM.gov Contractor Fixture + Minimal Contractor Ingestion

## CURRENT IMPLEMENTATION

This implementation adds a fixture-backed SAM.gov-shaped contractor source to the existing local ingestion pattern without introducing a new backend architecture or a speculative production schema.

### Scope

This phase intentionally stays narrow:
- local-only fixture data
- raw contractor payload preservation
- deterministic normalization for the current canonical Contractor model
- source identity tracking by `source + source_id`
- duplicate detection and idempotent ingestion
- canonical contractor mapping for currently supported fields only
- matching integration with the existing deterministic engine

### Not included

This phase does not include:
- live SAM.gov contractor API access
- API keys or credentials
- scraping or bypassing SAM.gov auth
- paid contractor databases
- cross-source entity resolution
- ML / embeddings / LLM classification
- new runtime fields for website, phone, zip, NAICS, license status, service area, or contractor capacity

## CURRENT CONTRACTOR MODEL

The current runtime canonical model remains deliberately small and is the only model used in this phase.

Supported canonical fields:
- `id`
- `company_name`
- `normalized_name`
- `source`
- `source_id`
- `city`
- `state`
- `trades`
- `primary_email`
- `provenance`

Any richer SAM.gov contractor metadata remains either:
- in the raw payload
- in provenance metadata
- deferred to future schema decisions

## SOURCE IDENTITY RULE

The active identity rule is:
- stable identity is `source + source_id`
- `company_name` is never a universal identity key
- duplicate detection is based on source identity, not company name

This is critical because the same company can legitimately appear under different source IDs or different source-specific records.

## Fixture contract

The synthetic fixture file is:
- [docs/fixtures/phase11_samgov_contractors.json](fixtures/phase11_samgov_contractors.json)

It includes deterministic cases for:
- normal construction contractor
- multiple-trade contractor
- missing optional data
- non-construction entity
- duplicate source identity
- invalid record with missing required identity
- same company name with different source IDs

All records are explicitly synthetic and contain a `notes` field with `SYNTHETIC TEST DATA`.

## Provider behavior

The provider is:
- [src/providers/samgov_contractors.py](../src/providers/samgov_contractors.py)

It performs no network requests and returns only local fixture records. It keeps:
- source as `samgov`
- `source_id` as a stable value
- raw payload preserved
- `fetched_at` / provenance preserved
- future metadata separate from canonical fields

## Normalization behavior

Normalization remains conservative and applies only to the current supported runtime model:
- trim company name and email whitespace
- lower-case email before storage
- uppercase state values to 2-letter codes
- title-case city names where available
- normalize trade list values to the repo’s existing lower-case names
- keep missing values as `NULL` / missing rather than inventing defaults

This matches the repo’s existing ingestion semantics.

## Raw payload preservation

The raw payload is kept intact in `RawProject.raw_payload` and also copied into contractor `provenance["raw_payload"]` for auditability.

This preserves:
- legal entity metadata
- registration status
- source URL
- business classification
- NAICS metadata
- website and other source-shape fields

These fields are not mapped into the canonical runtime `Contractor` table unless that schema already supports them.

## Canonical mapping

The canonical mapping is intentionally limited to:
- `company_name`
- `normalized_name`
- `source`
- `source_id`
- `city`
- `state`
- `trades`
- `primary_email`
- `provenance`

Unsupported data remains deferred as:
- `DEFERRED — FUTURE CONTRACTOR SCHEMA`

Examples of deferred fields:
- website
- phone
- ZIP
- license_number
- license_status
- business_status
- capacity
- NAICS
- service area
- project history
- confidence score
- aliases / entity merge history

## Duplicate and idempotency behavior

The repo’s duplicate detection remains deterministic:
- same `source` + same `source_id` => duplicate

This means repeated ingestion from the same fixture record does not create duplicate canonical `Contractor` rows.

## Matching integration

The current deterministic matcher already supports:
- trade overlap
- geography by city/state and distance

The Phase 11 contractor fixtures populate these fields when available. The matcher is not modified.

This proves that SAM-shaped contractor records can flow into the existing review and matching workflow without adding speculative matching features.

## Security and trust model

This implementation treats contractor source data as untrusted input and preserves it as raw data. It does not:
- execute HTML or scripts
- follow arbitrary URLs
- store credentials
- make network calls
- scrape protected pages
- bypass auth or bots
- send automated outreach

## Files created

- [docs/fixtures/phase11_samgov_contractors.json](fixtures/phase11_samgov_contractors.json)
- [src/providers/samgov_contractors.py](../src/providers/samgov_contractors.py)
- [src/tests/test_phase11_samgov_contractors.py](../src/tests/test_phase11_samgov_contractors.py)
- [docs/PHASE11_SAMGOV_CONTRACTOR_FIXTURE_IMPLEMENTATION.md](PHASE11_SAMGOV_CONTRACTOR_FIXTURE_IMPLEMENTATION.md)

## Files updated

- [src/ingestion/service.py](../src/ingestion/service.py)
- [src/api.py](../src/api.py)
- [docs/CANONICAL_MODELS.md](CANONICAL_MODELS.md)
- [docs/DATA_INGESTION.md](DATA_INGESTION.md)

## Verification

Fresh verification is required for this phase and will be completed through the repository’s full test suite and compile checks.

No live network calls are performed. No API keys or credentials are introduced. No paid providers are used.

## FUTURE LIVE SAM.GOV INTEGRATION

A later live contractor provider would require:
- explicit SAM.gov contractor access validation
- approved account and auth flow
- a source-specific contract review
- a separate business decision on which contractor fields become canonical
- explicit permission review for any contact data and outreach automation

This phase intentionally does not claim any of that is implemented.
