# Phase 32: Review Workspace Error State

## Goal

Harden the review workspace around project/match loading failures and preserve the selected match when a refresh or review action reloads the current page.

## Changes

- `/projects` load failures now surface the existing workspace error state instead of failing silently.
- Match loading continues to report request failures in the workspace.
- Refreshing matches preserves the selected match when it remains visible on the current page.
- If the selected match is no longer visible because of pagination or filtering, the first visible match is selected.
- Successful match refreshes clear stale error/success messages.

## Validation

Run:

```bash
python -m pytest src/tests/test_phase31_review_workspace_contracts.py src/tests/test_phase32_review_workspace_error_state.py -q
```
