# Email Workflow & Provider Adapter Pattern

This document defines the email sending workflow and the adapter interface for integrating with Postmark, SendGrid, Mailgun, or SES.

Workflow
1. Compose: `generate_email` job uses LLM templates and project/contractor data to produce `emails` in `draft` status.
2. Review: UI allows user to edit or approve emails.
3. Queue: approved emails set to `queued` and `send_email` job created.
4. Send: `send_email` job calls provider adapter and records `provider_message_id`.
5. Events: provider webhook posts bounces/deliveries to `email_events`.
6. Update: use `email_events` to update `emails.status` and `campaign` metrics.

Adapter interface (Python)
- `class EmailProviderAdapter:`
  - `send_email(self, to_email, subject, body, variables, **kwargs) -> dict` — returns `{message_id, status, provider_response}`
  - `verify_webhook(self, request) -> bool`
  - `parse_event(self, request_payload) -> list[EmailEvent]`
  - `get_delivery_status(self, message_id) -> dict`

Implementation notes
- Wrap provider SDKs in adapters that adhere to this interface
- Support batch sending and rate-limited sending pools
- Use signed webhooks and verify signatures
- Support domain verification checks (DKIM, SPF) in admin UI

Bounces & Suppressions
- On bounce events, add to `suppression_list`
- Respect global suppression and per-campaign daily limits

This adapter pattern ensures we can switch providers with minimal code changes.
