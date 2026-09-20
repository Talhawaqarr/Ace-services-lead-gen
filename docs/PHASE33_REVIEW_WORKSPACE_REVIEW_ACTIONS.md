# Phase 33: Review Action Feedback

## Goal

Ensure review actions provide visible success feedback after the match list is refreshed.

## Changes

- Refresh the match list first after a successful review transition.
- Show the success message after the refresh so it is not immediately cleared.
- Preserve the existing API error-detail handling for failed review actions.

## Validation

```bash
python -m pytest src/tests/test_phase31_review_workspace_contracts.py src/tests/test_phase32_review_workspace_error_state.py src/tests/test_phase33_review_workspace_review_actions.py -q
```
