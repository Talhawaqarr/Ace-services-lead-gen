# Match Review Workflow

## Current status

This document describes the Phase 3 review workflow for the existing deterministic matcher. It does not redesign the Phase 1 runtime model or the Phase 2 scoring engine.

## Lifecycle

A persisted match is created from a project + contractor candidate pair using the current deterministic matcher. The initial state is `UNREVIEWED`.

### States

- `UNREVIEWED`: the match has been generated and is awaiting a human review decision.
- `APPROVED`: the reviewer considers the project/contractor pairing suitable for the next workflow stage.
- `REJECTED`: the reviewer does not consider the pairing suitable.
- `SKIPPED`: the reviewer chooses to defer action without rejecting the pairing.

### Allowed transitions

The smallest sensible transition model is:

- `UNREVIEWED -> APPROVED`
- `UNREVIEWED -> REJECTED`
- `UNREVIEWED -> SKIPPED`
- `APPROVED -> REJECTED`
- `APPROVED -> SKIPPED`
- `REJECTED -> APPROVED`
- `REJECTED -> SKIPPED`
- `SKIPPED -> APPROVED`
- `SKIPPED -> REJECTED`

A decision may be changed, but every change must be recorded in the audit log.

### Decision semantics

Approval means the reviewer considers the project/contractor match suitable for the next workflow stage. It does not automatically send any email or trigger external actions.

## Persistence

Persisted match records store the actual deterministic matcher result at generation time so the reasoning remains auditable without re-running the older matcher logic later.

Each persisted match record includes:

- project_id
- contractor_id
- match_score
- raw_score
- max_available_score
- feature_completeness
- confidence
- matcher_version
- ranking
- positive_factors
- negative_factors
- unknown_factors
- components
- review_status
- reviewed_at
- created_at
- updated_at

## Idempotency

Generation is idempotent per project + contractor + matcher_version. Re-running generation for the same deterministic matching inputs must not create duplicate persisted results.

If the matcher version changes, a new persisted record is allowed for the same project/contractor pairing.

## Audit trail

Every review status change must be recorded with:

- match_id
- previous_status
- new_status
- timestamp
- actor/source

This is a development-safe audit representation. There is no production authentication layer in this phase, so the actor/source uses a local-safe value such as `local-dev` or `manual-review`.

## Review requirements

A reviewer must be able to see:

- project identity
- contractor identity
- match score
- confidence
- ranking
- positive factors
- negative factors
- unknown factors
- evidence
- matcher version
- review status

Unsupported or future fields are not shown as if they are currently implemented.

## Scope boundary

The workflow layer is intentionally limited to:

- persisting match results
- reviewing those results
- recording the review history
- exposing a local/service-level workflow for operator review

It does not include:

- ML ranking
- embeddings
- LLM-based outreach
- external discovery
- external API-based bid ingestion
- automated email sending
- production authentication
