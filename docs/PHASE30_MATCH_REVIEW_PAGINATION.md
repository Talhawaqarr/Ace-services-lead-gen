# Phase 30 — Match Review Pagination

## Goal

Make the project match-review endpoint usable as the number of candidate matches grows without loading every match into memory.

## Changes

`GET /projects/{project_id}/matches` now supports:

- `limit`: 1–100, default 50
- `offset`: 0+, default 0
- `review_status`: optional `UNREVIEWED`, `APPROVED`, `REJECTED`, or `SKIPPED`

The response includes:

- `matches`: only the requested page/filter
- `total`: number of matches after the requested status filter
- `limit` / `offset`: applied page parameters
- `summary`: project-wide review-status counts, independent of pagination/filtering

Ordering remains deterministic by ranking, then match ID.

## Scope

This is an API/workspace scalability improvement. It does not change matcher scoring, qualification, candidate discovery, or review-transition rules.

## Verification

```powershell
python -m pytest src/tests/test_phase30_match_review_pagination.py -q
```

The regression tests cover pagination, status filtering, project-wide summary counts, and invalid status rejection.
