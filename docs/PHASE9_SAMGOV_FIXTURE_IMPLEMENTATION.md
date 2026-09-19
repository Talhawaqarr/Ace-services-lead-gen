# Phase 9 — SAM.gov Fixture Provider + Canonical Opportunity Contract

## CURRENT IMPLEMENTATION

This repository now includes a deterministic local SAM.gov-shaped opportunity provider for offline development and validation.

### Scope

This implementation is intentionally limited to:
- local-only fixture data
- raw source preservation
- ingestion validation and normalization
- source identity handling
- duplicate detection and idempotency
- canonical project mapping only for already-supported fields
- explicit separation between source ingestion and construction relevance heuristics

### Not included

This implementation does not include:
- live SAM.gov API calls
- API-key handling
- real credential storage
- scraping or bypassing access controls
- paid services
- AI/LLM/embedding enrichment
- matching algorithm redesign

## FUTURE LIVE SAM.GOV INTEGRATION

A future live provider would need:
- approved SAM.gov account setup
- secure credential configuration
- provider selection behind the same interface boundary
- a validation path for required fields and error handling
- a separate source contract for live API responses and auth behavior
- explicit review of rate limits, quotas, and account restrictions

This implementation does not claim to have any of that. It is a fixture-backed local contract only.

## Source identity rule

The identity rule used in this phase is:
- if the source is `samgov`, prefer `solicitationNumber`
- otherwise fall back to `source_id`
- never treat title as the stable identity key

This rule is intentionally conservative and deterministic.

## Raw contract

The provider returns the original official SAM.gov-shaped payload, preserving field names exactly as present in the source fixture, including:
- `reponseDeadLine`
- `pointOfContact`
- `resourceLinks`
- `data.award.amount`
- `organizationName`
- `fullParentPathName`
- `naicsCode`
- `classificationCode`
- `source_id`
- `solicitationNumber`

The raw record is stored in `RawProject.raw_payload` as-is without mutation, preserving auditability and debugging value.

## Normalized contract

The ingestion layer normalizes what the repo already supports, while keeping richer SAM.gov fields in `provenance` rather than forcing them into the runtime `Project` schema.

Supported internal normalization fields include:
- `name` from `title`
- `source` from source string
- `source_id` from selected SAM identity
- `city` from `placeOfPerformance.city`
- `state` from `placeOfPerformance.state`
- `response_deadline` from `reponseDeadLine`
- `source_url` from `uiLink`
- `description` from the opportunity description
- `procurement_type` from `type`
- `naics_code` from `naicsCode`
- `classification_code` from `classificationCode`
- `organization_name` and `full_parent_path_name`
- `resource_links`
- `point_of_contact`
- `construction_relevance`

Important: these are stored in raw/provenance metadata unless they already map cleanly to the existing canonical schema.

## Response deadline typo handling

The official SAM.gov docs use `reponseDeadLine` as the source field name. The repo preserves this name in the raw payload.

The internal normalized value is named `response_deadline` to avoid the typo leaking into downstream logic. This is the one-liner rule:
- raw payload retains `reponseDeadLine`
- normalized internal field is `response_deadline`

This is tested directly in the Phase 9 test suite.

## Award amount semantics

The source field `data.award.amount` is preserved as award metadata under provenance.

It is not mapped to the canonical `Project.estimated_value` unless a future source contract explicitly establishes semantic equivalence.

This matches the Phase 8 decision: award amounts are not automatically the same as a live opportunity estimate.

## Construction relevance boundary

The repo deliberately separates:
- SOURCE INGESTION: preserve records and their metadata
- CONSTRUCTION RELEVANCE: record whether a source item appears likely to be construction-related, using deterministic checks on documented fields such as `naicsCode`, `classificationCode`, `type`, and title/description text

This does not constitute ML, LLM, or external enrichment. It is simply a deterministic heuristic stored in provenance metadata.

## Canonical mapping

The canonical `Project` model remains narrow and intentionally unchanged for this phase.

It safely accepts:
- `name` from source title
- `source` set to `samgov`
- `source_id` set to the SAM identity rule
- `city` from source location
- `state` from source location
- `provenance` metadata including source URL, document metadata, and award metadata

It intentionally does not force fields like:
- `response_deadline` into `bid_date`
- `data.award.amount` into `estimated_value`
- additional source-specific schema into the runtime model

Any richer field remains in raw/normalized provenance until a future schema decision justifies a canonical expansion.

## Idempotency and duplicate behavior

Duplicate detection remains deterministic and based on the same rule already used in the repo:
- same `source` + same `source_id` => duplicate

This prevents repeated fixture ingestion from creating duplicate canonical projects.

## Security handling

The fixture data is synthetic and intentionally excludes real personal data or real contact details.

The implementation does not:
- execute HTML or script content
- follow arbitrary URLs on ingestion
- store credentials in the repo
- log sensitive contact details unnecessarily

The provider simply loads local JSON and stores it as data.

## Files introduced

- [docs/fixtures/phase9_samgov_opportunities.json](../docs/fixtures/phase9_samgov_opportunities.json)
- [src/providers/samgov.py](../src/providers/samgov.py)
- [src/tests/test_phase9_samgov_fixture.py](../src/tests/test_phase9_samgov_fixture.py)

## Files updated

- [src/ingestion/service.py](../src/ingestion/service.py)
- [src/api.py](../src/api.py)
- [docs/DATA_INGESTION.md](../docs/DATA_INGESTION.md)
- [docs/DATA_SOURCES_PHASE5.md](../docs/DATA_SOURCES_PHASE5.md)
- [docs/PHASE8_SAMGOV_ACCESS_AND_SCHEMA_VALIDATION.md](../docs/PHASE8_SAMGOV_ACCESS_AND_SCHEMA_VALIDATION.md)

## Verification

This implementation has been validated with the repo test suite and compile check.

Fresh verification evidence:
- Phase 9 fixture tests: 6 passed
- full suite: 31 passed, 0 failed, 0 skipped
- compileall: passed

No live network calls were made; no API keys were added; no paid services were used.

## Remaining blockers for Phase 10

- live SAM.gov integration remains intentionally disabled
- official account and credential handling must be designed before any real API provider is added
- broader canonical schema expansion still requires a verified business need and explicit contract review
- richer construction filtering remains future work and is not implied by the local fixture provider

This completes the Phase 9 implementation while preserving the clean seam for a later live SAM.gov integration.
