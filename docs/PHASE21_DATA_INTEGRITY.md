# Phase 21 — Canonical Data Integrity Hardening

## Goal

Make the canonical `projects` and `contractors` tables enforce the source identity already used by ingestion.

## Constraint

For both canonical entities, `(source, source_id)` is the stable external identity. The database now enforces this with unique constraints:

- `projects(source, source_id)`
- `contractors(source, source_id)`

Indexes on `source` and `source_id` also support the lookup paths used by ingestion and discovery.

## Why this matters

Application-level check-then-insert logic prevents ordinary duplicate ingestion, but it cannot by itself guarantee uniqueness under concurrent workers or requests. The database is the final integrity boundary.

This phase does not delete or merge existing records. If a deployment already contains duplicate canonical source identities, migration `0006` will fail rather than silently choosing a record.

## Runtime impact

The existing fixture pipeline and deterministic matching behavior are unchanged. Repeated ingestion remains idempotent.

The live-provider path remains disabled; this phase only hardens the canonical database contract.
