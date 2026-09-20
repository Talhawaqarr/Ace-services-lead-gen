# Phase 34: Review Audit History

## Goal

Expose the existing match-review audit trail so the review workspace/API can inspect who changed a match, from which status, to which status, and when.

## Changes

- Added `GET /matches/{match_id}/reviews`.
- Returns chronological review transitions from `MatchReviewAudit`.
- Keeps the existing review mutation and audit-write behavior unchanged.

## Validation

```bash
python -m pytest src/tests/test_phase31_review_workspace_contracts.py src/tests/test_phase32_review_workspace_error_state.py src/tests/test_phase33_review_workspace_review_actions.py src/tests/test_phase34_review_audit_history.py -q
```
