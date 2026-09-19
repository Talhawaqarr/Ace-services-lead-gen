# Domain States — ACE Services

Canonical enums and state machines for core domain entities. Use these values across all docs and code to avoid ambiguity.

## Projects (`project.status`)
- Values: `draft`, `discovered`, `open_for_bid`, `closed`, `awarded`, `cancelled`, `archived`
- Meaning & transitions:
  - `draft` -> created by ingestion but missing required data; can transition to `discovered` when validated.
  - `discovered` -> normalized and available for review; can transition to `open_for_bid` if bid_date present.
  - `open_for_bid` -> active bidding window; can transition to `closed` after bid_date passes.
  - `closed` -> outcome pending; can transition to `awarded` or `cancelled` based on outcome.
  - `awarded` -> project awarded to contractor(s); terminal state unless historical corrections needed.
  - `cancelled` -> project cancelled; terminal.
  - `archived` -> administrative archival of old records.
- Who/what triggers transitions: ingestion service, normalization job, manual operator, outcome ingestion adapter.
- Invalid transitions: cannot go from `archived` to `open_for_bid` without manual unarchive.

## Contractors (`contractor.status`)
- Values: `raw`, `normalized`, `verified`, `blacklisted`, `archived`
- Meaning & transitions:
  - `raw` -> initial ingestion from provider; can transition to `normalized` after normalization.
  - `normalized` -> canonical record available; can transition to `verified` after data confidence checks or manual verification.
  - `verified` -> high-confidence record; used preferentially in matching.
  - `blacklisted` -> excluded from matching/outreach for policy reasons.
  - `archived` -> removed from active search results.
- Triggers: ingestion, enrichment, manual verification actions.

## Matches (`match.status`)
- Values: `candidate`, `reviewed`, `selected`, `contacted`, `rejected`
- Meaning & transitions:
  - `candidate` -> created by matching engine.
  - `reviewed` -> viewed by operator and acknowledged.
  - `selected` -> chosen for outreach/campaign.
  - `contacted` -> outreach sent to associated contact.
  - `rejected` -> rejected by operator or by feedback.
- Notes: status moves are audited and captured in `match_feedback`.

## Emails (`email.send_state`)
- Values: `draft`, `approved`, `queued`, `sent`, `delivered`, `bounced`, `replied`, `failed`, `cancelled`
- Meaning & transitions:
  - `draft` -> initial composition (LLM or manual).
  - `approved` -> validated ready for sending.
  - `queued` -> queued for provider send job.
  - `sent` -> provider accepted send request.
  - `delivered` -> delivery webhook confirmed.
  - `bounced` -> bounce webhook recorded.
  - `replied` -> reply webhook or manual entry.
  - `failed` -> send failed permanently.
  - `cancelled` -> user cancelled before sending.
- Who/what triggers transitions: UI actions, `send_email` job, provider webhooks, manual operator.

## Campaigns (`campaign.status`)
- Values: `draft`, `active`, `paused`, `completed`, `cancelled`

## Jobs (`job.status`)
- Values: `pending`, `in_progress`, `completed`, `failed`, `permanent_failure` (matches background job doc)

## Providers (`provider.status`)
- Values: `unverified`, `healthy`, `degraded`, `unavailable`, `requires_credentials`
- Use for provider health tracking and onboarding flows.

---

These canonical enums should be implemented as centralized `enums` in the codebase and referenced by migrations and Pydantic models.