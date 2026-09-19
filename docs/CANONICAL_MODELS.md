# Canonical Project and Contractor Models

This document separates the actual runtime model currently in use from future aspirational fields planned for later phases.

## CURRENT RUNTIME CANONICAL MODEL

This is the actual canonical model used by the current implementation in the repository.

### Current `Project` runtime fields

Required runtime fields:
- `id` (uuid)
- `name` (string)
- `source` (string) — provider key
- `source_id` (string) — original provider identifier
- `city` (string)
- `state` (2-char)
- `latitude` (float)
- `longitude` (float)
- `trades` (array of strings)
- `bid_date` (string)
- `estimated_value` (numeric)
- `provenance` (json)

Optional runtime fields:
- `primary_email` / contractor contact fields are not part of the active project model; they are represented only in contractor-specific runtime data where relevant.

Actual implementation source:
- [src/models/core.py](src/models/core.py)
- [alembic/versions/0001_initial_schema.py](alembic/versions/0001_initial_schema.py)
- [alembic/versions/0002_phase1_runtime_columns.py](alembic/versions/0002_phase1_runtime_columns.py)

### Current `Contractor` runtime fields

Required runtime fields:
- `id` (uuid)
- `company_name` (string)
- `normalized_name` (string)
- `source` (string)
- `source_id` (string)
- `city` (string)
- `state` (2-char)
- `trades` (array of strings)
- `primary_email` (string)
- `provenance` (json)

These are the fields that are actually available to the deterministic matcher today.

---

## FUTURE / ASPIRATIONAL MODEL

The following fields are intentionally documented as future or aspirational only. They are not currently implemented in the runtime model and must not be treated as existing fields.

### Future project fields (NOT CURRENTLY IMPLEMENTED)
- `date_discovered` (timestamp) — FUTURE
- `description` (text) — FUTURE
- `zip` (string) — FUTURE
- `project_type` (enum) — FUTURE / NOT CURRENTLY IMPLEMENTED
- `status` (enum) — FUTURE / NOT CURRENTLY IMPLEMENTED
- `owner` (string) — FUTURE
- `construction_type` (string) — FUTURE
- `documents` (jsonb) — FUTURE
- `raw` (jsonb) — FUTURE
- `normalized_fields` (jsonb) — FUTURE
- `normalized_location` (string) — FUTURE
- `distance_to_nearest_contractor` (float) — FUTURE

### Future contractor fields (NOT CURRENTLY IMPLEMENTED)
- `primary_contact_email` (string) — FUTURE only if a design expands contact normalization; this is not the current runtime field naming convention
- `service_areas` (array of strings) — FUTURE / NOT CURRENTLY IMPLEMENTED
- `website` (string) — FUTURE
- `phone` (string) — FUTURE
- `company_size` (enum or int) — FUTURE
- `licenses` (array) — FUTURE / NOT CURRENTLY IMPLEMENTED
- `previous_project_descriptions` (array of texts) — FUTURE / NOT CURRENTLY IMPLEMENTED
- `contacts` (array of contact objects) — FUTURE
- `verification_status` (verified / unverified / bounced) — FUTURE
- `data_confidence` (numeric 0-1) — FUTURE

### Future matching and dedupe concepts (NOT CURRENTLY IMPLEMENTED)
- domain-based identity matching
- phone/address hash matching
- license-number matching
- multi-signal auto-merge thresholds
- automatic merge logging and reversible merge history
- semantic similarity over historical project text
- ML scoring and supervised ranking

---

## IMPORTANT BOUNDARY

The runtime canonical model is intentionally narrower than the aspirational architecture.

Current implementation rule:
- only fields that exist in the runtime model may be used by the current matcher
- future fields are preserved as architecture intent only
- future fields must be labeled as FUTURE / NOT CURRENTLY IMPLEMENTED and must not imply active runtime support

## Provenance and source tracking

The current implementation does maintain provider/source metadata in the runtime model through fields such as:
- `source`
- `source_id`
- `provenance`

Additional provenance patterns such as per-field logging, raw payload archives, and merge-history tracking remain future design intent and are not current runtime functionality.
