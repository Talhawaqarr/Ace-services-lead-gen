# High-Level Cost Model — ACE Services

Purpose: provide cost categories and levers to estimate monthly spend for MVP and scale. This document now separates Development (FREE) vs Prototype/Production costs.

Cost categories
- Development (target: $0)
  - Data sources: government APIs (FREE), manually imported CSVs, synthetic datasets (FREE)
  - LLM/embeddings: deterministic templates, open-source local models, or mocked providers (FREE)
  - Geocoding: Haversine distance for MVP; OpenStreetMap/Nominatim self-hosting if needed (FREE)
  - Email: DRY_RUN mode; store generated emails locally instead of sending (FREE)
  - Hosting: local Docker + developer machine (FREE)

- Prototype / Production (post-budget)
  - Data provider subscriptions: ConstructConnect/Dodge (enterprise) — likely the largest single fixed cost if purchased.
  - LLM & embeddings: OpenAI usage billed per-token (embeddings billed per vector request). Control with batching and caching.
  - Geocoding & routing: Mapbox or Google pay-per-request (or self-hosted routing stack)
  - Email sending: Postmark/SendGrid/Mailgun/SES per-message pricing; deliverability services (IP warmup, dedicated IPs) extra.
  - Hosting & infra: managed DBs, cloud services, monitoring/logs (may incur costs)

Cost control levers (Development-focused)
- Build fully functional end-to-end flows that require no paid components.
- Use Haversine distances and deterministic matching for initial scoring.
- Use local or open-source NLP tooling (sentence-transformers CPU-friendly models) if needed, but keep optional.
- Keep `DRY_RUN` as the default for any networked or outbound action.

Example Development Targets
- Development MVP: $0/month — relies on FREE data sources, local processing, and synthetic fixtures.

Example Prototype Estimates (post-budget)
- Small MVP with paid services: see previous estimates (OpenAI, Mapbox, Email provider, Hosting).

Next steps
- Define expected volumes if/when ACE moves to paid prototype and I will produce more precise estimates and a cost spreadsheet.
