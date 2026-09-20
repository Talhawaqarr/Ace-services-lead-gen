# ACE Services — Demo Completion Plan

## Goal

Turn the current ACE Services backend + review workspace into one convincing, repeatable end-to-end demo:

> **tiny real SAM.gov opportunity sample → ingestion/normalization → construction qualification → contractor candidate matching → human match approval → deterministic outreach draft → human draft approval → safe outreach queue (not sent)**

The demo should use **real SAM.gov Contract Opportunities data whenever live mode is configured**, but must remain safe: no automatic email sending, no bulk ingestion, and no uncontrolled API pagination. Contractor contact records may remain the existing clearly synthetic/demo records because they are used to exercise the matching and outreach workflow without contacting real businesses.

## Current baseline

- FastAPI + PostgreSQL + Alembic + Docker Compose are running.
- `/health/ready` reports database readiness.
- The complete Dockerized test suite is green: **153 passed**.
- Phase 52 ingestion-quality tests are green: **3 passed**.
- Live SAM.gov provider exists with bounded pagination/retries.
- Live ingestion mode exists and is wired into Compose.
- Construction relevance/qualification exists.
- Deterministic contractor matching exists with evidence and review states.
- Review workspace supports pagination, filtering, approve/reject/skip, and audit history.
- Outreach drafts support deterministic generation, approval/rejection, audit history, and a safe queued/not-sent state.
- The current UI is primarily a **review workspace**; it does not yet drive the full demo lifecycle.

## Demo completion checklist

### 1. Demo run orchestration
- [ ] Add a dedicated demo-run API operation that executes only a **tiny bounded live SAM.gov search**.
- [ ] Accept safe filters such as keyword, NAICS, state, and posted-date range.
- [ ] Enforce a hard demo record/page cap server-side regardless of caller input.
- [ ] Return a useful run summary: fetched, accepted, rejected, duplicates, errors, qualified opportunities, contractors considered, and matches generated.
- [ ] Keep the existing general ingestion endpoint intact for normal operations.

### 2. Real-data demo path
- [ ] Default the demo search toward construction opportunities (for example construction keyword / construction NAICS).
- [ ] Use a small limit and one page by default.
- [ ] Surface whether the returned records are live or fixture-backed.
- [ ] Preserve source/provenance information on ingested records.
- [ ] Make an empty qualifying result a clean, actionable demo state rather than a crash.
- [ ] Do not display or persist sensitive SAM.gov API credentials.

### 3. Demo UI controls
- [ ] Add a compact **Demo Controls** section to the existing workspace.
- [ ] Show ingestion mode/configuration and latest ingestion run.
- [ ] Add a **Run live SAM.gov demo sync** action.
- [ ] Show progress/result/error feedback in the workspace.
- [ ] Refresh the opportunity list after a successful run.
- [ ] Keep the existing review workspace behavior unchanged.

### 4. Matching → outreach → queue happy path
- [ ] Ensure the UI makes the intended sequence obvious:
  1. select qualified opportunity
  2. generate matches
  3. open a match
  4. approve the match
  5. generate outreach draft
  6. review/approve the draft
  7. queue the approved draft
- [ ] Add a visible queue action after draft approval.
- [ ] Add a small queue confirmation/state in the UI.
- [ ] Expose queued items for the demo without implying they were sent.
- [ ] Preserve the existing human-approval gates.

### 5. Demo data reliability
- [ ] Make the demo robust when live SAM.gov returns opportunities outside the synthetic contractor states/trades.
- [ ] Do not weaken the production matching rules just to make the demo look successful.
- [ ] If a live opportunity has no eligible contractor candidate, explain that state in the UI.
- [ ] Keep synthetic contractor emails clearly non-production and do not send them.

### 6. Tests and verification
- [ ] Add focused tests for the bounded demo ingestion contract.
- [ ] Add tests for demo-run response accounting.
- [ ] Add tests for queue/list behavior if new endpoints are added.
- [ ] Keep existing tests green.
- [ ] Run the full Dockerized suite before declaring the demo complete.
- [ ] Perform a manual API/UI smoke path against the Docker Compose stack.

## Definition of done

The demo is complete when a clean Docker Compose environment can demonstrate, with a tiny bounded dataset:

1. **Real public opportunity discovery** from SAM.gov (when live credentials are configured).
2. **Ingestion and normalization** into PostgreSQL.
3. **Construction qualification** with a visible reason/state.
4. **Contractor matching** with score/evidence.
5. **Human match approval** with audit history.
6. **Deterministic personalized outreach draft** generated from the approved match.
7. **Human outreach approval** with audit history.
8. **Safe queueing** with an explicit **NOT SENT** state.
9. **No uncontrolled SAM.gov requests and no email delivery.**
10. A fresh Dockerized test run remains green.

## Explicit non-goals for this demo sprint

Do not expand scope into:
- production email delivery,
- bulk SAM.gov harvesting,
- paid provider integrations,
- supervised ML,
- CRM integration,
- automated outreach,
- large-scale background-job infrastructure,
- speculative architecture cleanup unrelated to the demo path.

The objective is a credible, inspectable **happy-path product demo**, not production commercialization.
