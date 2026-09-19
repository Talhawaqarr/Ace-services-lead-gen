# Database Design — ACE Services

This document outlines the canonical PostgreSQL schema for the ACE Services MVP. It emphasizes provenance, normalization, and queries for matching and analytics.

Phase 1 note: the repository intentionally keeps the runtime migration minimal for the deterministic matching MVP. The initial migration creates only the `projects` and `contractors` tables needed to ingest synthetic fixtures, deduplicate basic records, and drive the early matching pipeline. The broader schema below represents the long-term target architecture for later phases; it is not a requirement for the initial Phase 1 implementation and should not be expanded prematurely.

Design principles
- Normalize entities where appropriate (companies, contacts, projects).
- Use JSONB for flexible fields and provenance metadata.
- Include audit and job-run tables to track ingestion and processing.
- Soft delete using `deleted_at` timestamps for recoverability.
- Provide indexes for common query patterns (state, project_deadline, match_score).

## Core tables (high level)

1. users
- id (uuid PK)
- email (unique)
- hashed_password
- name
- role (enum: admin,user)
- organization_id (FK)
- created_at, updated_at

2. organizations
- id (uuid PK)
- name
- created_at, updated_at

3. api_providers
- id (serial PK)
- provider_key (str, unique)
- name
- config (jsonb)
- created_at, updated_at

4. projects_raw
- id (uuid PK)
- source (varchar) — provider key
- source_id (varchar) — original provider project id
- raw (jsonb)
- retrieved_at
- sync_run_id (FK -> source_sync_runs)
- created_at, updated_at

5. projects
- id (uuid PK)
- canonical_id (varchar) — optional human-facing
- name
- description (text)
- source (varchar)
- source_id (varchar)
- owner
- address_raw (jsonb)
- city
- state (2-char)
- zip
- latitude
- longitude
- project_type (enum)
- construction_type (varchar)
- trades (jsonb array)
- estimated_value (numeric)
- bid_date (timestamp)
- bid_time (time)
- status (enum)
- documents (jsonb) — list of document metadata (S3 link, filename, text_extracted)
- date_discovered (timestamp)
- last_updated (timestamp)
- provenance (jsonb) — {source, confidence, retrieved_at}
- raw_project_id (FK -> projects_raw)
- created_at, updated_at, deleted_at
Indexes:
- idx_projects_state
- idx_projects_bid_date
- idx_projects_estimated_value
- GIST index on (geography(point(latitude, longitude))) for geo queries

6. contractors
- id (uuid PK)
- company_name
- normalized_name (for matching)
- website
- primary_email
- primary_phone
- address (jsonb)
- city
- state
- zip
- latitude
- longitude
- service_areas (jsonb) — list of states/metros
- trades (jsonb)
- project_types (jsonb)
- company_size (enum or int)
- description (text)
- licenses (jsonb) — list of license entries {state, number, status, source}
- source (varchar)
- source_id (varchar)
- data_confidence (numeric)
- last_verified (timestamp)
- provenance (jsonb)
- created_at, updated_at, deleted_at
Indexes:
- idx_contractors_state
- idx_contractors_trades_gin (GIN index on trades jsonb)
- fulltext index on (company_name, normalized_name)

7. contractor_contacts
- id (uuid PK)
- contractor_id (FK)
- name
- role
- email
- phone
- linkedin_url
- verification_status (enum)
- created_at, updated_at

8. matches
- id (uuid PK)
- project_id (FK)
- contractor_id (FK)
- match_score (numeric)
- model_version (varchar)
- features (jsonb) — deterministic and embedding features used
- explanation (jsonb) — list of reasons and evidence
- created_at, updated_at
Indexes:
- idx_matches_project_id
- idx_matches_score (for ranking)

9. match_feedback
- id (uuid PK)
- match_id (FK)
- user_id (FK)
- feedback (enum) — relevant, not_relevant, wrong_trade, too_far, too_small, too_large, already_contacted
- comment (text)
- created_at

10. emails
- id (uuid PK)
- match_id (FK) optional
- project_id (FK) optional
- contractor_contact_id (FK) optional
- subject
- body (text)
- variables (jsonb)
- status (enum: draft, queued, sent, delivered, bounced, opened, replied, failed)
- provider_message_id
- sending_attempts
- created_at, updated_at

11. email_events
- id (uuid PK)
- email_id (FK)
- event_type (enum)
- provider_payload (jsonb)
- received_at

12. campaigns
- id (uuid PK)
- name
- filters (jsonb)
- template_id (FK)
- daily_limit
- sending_schedule (jsonb)
- created_at, updated_at

13. suppression_list
- id (uuid PK)
- email
- reason
- added_by
- added_at

14. source_sync_runs
- id (uuid PK)
- source (varchar)
- started_at
- finished_at
- projects_imported
- errors (jsonb)

15. jobs / job_runs
- id (uuid PK)
- job_type
- status
- payload (jsonb)
- retries
- last_error
- started_at
- finished_at

16. ml_models
- id (uuid PK)
- name
- version
- metadata (jsonb)
- created_at

17. audit_logs
- id (uuid PK)
- actor_type
- actor_id
- action
- details (jsonb)
- created_at


## Keys & Constraints
- Use UUID PKs for user-visible entities to avoid leaking row counts.
- Unique constraints where appropriate (e.g., source + source_id unique for projects, contractors).
- Foreign keys enforce referential integrity.

## Performance considerations
- Matching queries will be hot: index by project_id and score.
- Geospatial queries: use PostGIS/GIST indexes on coordinate points (latitude/longitude) for nearest contractors.
- Frequent writes: source syncs may batch insert into `projects_raw` then upsert to `projects`.

## Deduplication
- Use deterministic dedupe keys: normalized address+source_id, combination of name+address+website normalized.
- Keep original source records and mapping table for merged entities.

## Provenance & Confidence
- Each canonical record stores `provenance` JSONB that includes `source`, `source_id`, `confidence`, `retrieved_at`.
- Enriched fields store nested objects: `{ value, source, confidence, last_updated }` when appropriate.

## Soft deletion
- Use `deleted_at` column to mark soft-deleted rows.

---

This schema is a strong base for MVP. Next steps: write SQLAlchemy models and Alembic migration scripts. Also create example queries for matching and operator dashboards.
