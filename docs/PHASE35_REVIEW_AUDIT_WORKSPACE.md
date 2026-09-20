# Phase 35: Review Audit Workspace

## Goal

Surface the existing match-review audit history directly in the human review workspace.

## Changes

- Added client-side review-audit state.
- Opening a match fetches `GET /matches/{match_id}/reviews`.
- The match detail panel displays chronological status transitions, actor, source, and timestamp.
- Audit-history loading failures are shown inline without breaking the rest of the workspace.

## Validation

```bash
python -m pytest src/tests/test_phase31_review_workspace_contracts.py src/tests/test_phase32_review_workspace_error_state.py src/tests/test_phase33_review_workspace_review_actions.py src/tests/test_phase34_review_audit_history.py src/tests/test_phase35_review_audit_workspace.py -q
```