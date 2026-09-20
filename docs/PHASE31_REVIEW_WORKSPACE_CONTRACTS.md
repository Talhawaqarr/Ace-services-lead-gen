# Phase 31 — Review Workspace Pagination

The review workspace now consumes the paginated match-review API introduced in Phase 30.

## UI behavior

- Loads 10 matches per page.
- Supports filtering by review status.
- Provides Previous/Next controls.
- Displays the current page range and total filtered matches.
- Keeps the project-wide status summary visible.
- Resets pagination and status filtering when switching projects.

The backend remains the source of truth for qualification, candidate filtering, scoring, and review transitions.
