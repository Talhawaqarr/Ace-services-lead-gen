# Provider Classification (A/B/C/D)

This file classifies providers discovered during the initial research and explains why.

Legend
- A — VERIFIED AND SUITABLE: official API exists, commercial use allowed or clear path, fields useful for MVP.
- B — POTENTIALLY SUITABLE / NEEDS ACCOUNT OR CONTRACT: API exists but requires paid account, limited docs, or contract negotiation.
- C — UNSUITABLE FOR MVP: not appropriate for MVP (no API, limited coverage, or legal/technical issues).
- D — REQUIRES FURTHER VERIFICATION: ambiguous or inconsistent documentation; needs more investigation.

---

## Federal / Public

- SAM.gov — A
  - Rationale: Official US government contracting portal; searchable; programmatic Data Services exist. Suitable for federal bid ingestion for MVP. Confirm exact API endpoints and paging during integration.

- USAspending / FPDS — A
  - Rationale: Public federal award/awardee data; good for enrichment and historical projects. Not a primary bid source for new opportunities.

## Commercial Project Feeds / Plan Rooms

- ConstructConnect — B
  - Rationale: Enterprise product with project intelligence and leads. API/data feeds available under commercial contract. High-quality but requires ACE subscription.
  - Dependency: paid account / contract required for real ingestion.

- Dodge (Dodge Construction Network / Construction.com) — B
  - Rationale: Market-leading construction data; enterprise APIs. Requires contract/subscription.

- PlanHub, iSqFt, The Blue Book, BidClerk — B / D
  - Rationale: Each is a real vendor. Availability of an open API and licensing differs per vendor; treat as B until ACE confirms subscription plans.

## Contractor / Company Enrichment

- OpenCorporates — A
  - Rationale: Public company registry aggregator with API, provenance, and clear account tiers. Licensing requires care for commercial redistribution; paid plans remove share-alike restrictions.

- State contractor license boards (per-state) — A / B
  - Rationale: Many states provide searchable license registries. Availability varies; some provide APIs (A), many are web pages (must not be scraped without permission — those are D).

- Google Places / Maps Business Data — B
  - Rationale: Rich place metadata (website, phone). Requires API key and billing; Terms of Service apply (pay-as-you-go). Acceptable for enrichment but not for unsanctioned scraping.

- Hunter.io, Clearbit, ZoomInfo, Dun & Bradstreet — B / D
  - Rationale: Commercial enrichment for contacts and firmographics. Paid and restrictive licensing (often forbid resale). Use only after legal review and subscription.

## Geocoding & Routing

- Mapbox Geocoding — A
  - Rationale: Full geocoding API, batch geocoding, clear pricing and license; permanent storage requires billing/enterprise consent (documented).

- Google Maps Geocoding / Directions — A
  - Rationale: Well-documented; requires billing and obeying Maps Platform terms (may mandate map display for certain uses).

- OpenCage, HERE, OSM/Nominatim — B / D
  - Rationale: Viable alternatives. OSM public Nominatim is not suitable for heavy/commercial use; use third-party or self-hosting.

## Embeddings / LLMs

- OpenAI — A
  - Rationale: Embeddings + generative models, mature API and clear commercial terms. Good for MVP.

- Cohere / Anthropic / Hugging Face Inference — B
  - Rationale: Alternatives with paid tiers or self-hosted options. Good fallbacks.

- Local Sentence-Transformers — B (self-host) / D (if not available infra)
  - Rationale: Allows private embeddings without external API costs but requires GPU and ops overhead.

## Transactional Email Providers

- Postmark — A
  - Rationale: Transactional email, webhooks for delivery/bounce/opens, strong developer docs. Good for transactional sending.

- SendGrid (Twilio SendGrid) — A
  - Rationale: Widely used, feature-rich webhooks and suppression lists; free tier available.

- Mailgun — A
  - Rationale: Another widely-used provider with robust APIs and webhooks.

- Amazon SES — A
  - Rationale: Cost-effective at scale; integrates with SNS for events; requires domain verification.

---

## Summary
- Verified and Suitable (A): SAM.gov, USAspending, OpenCorporates, OpenStreetMap (self-hosted), Postmark (optional for production), SendGrid (optional), Mailgun (optional).
- Potentially Suitable (B): ConstructConnect (PAID/CONTRACT), Dodge (PAID/CONTRACT), Google Places (FREE TIER but billing required), Mapbox (FREE TIER but licensing caveat for permanent storage), Cohere/Anthropic/HF (FREE TIER / PAID), OpenCage/HERE (FREE TIER / PAID).
- Requires further verification (D): PlanHub, iSqFt, The Blue Book — depends on contracted access.
- Unsuitable for MVP (C): paid feeds that ACE cannot access without purchase, or any provider requiring contract/subscription for basic functionality.

Note: For the $0 MVP, treat PAID/CONTRACT providers as POST-MVP. Implement mock/local adapters and synthetic data for development and testing. OpenStreetMap (OSM) and government sources are the primary FREE data sources recommended for development.

Notes: Every commercial provider must be validated against its terms-of-service and licensing for storing and using data in ACE's product. If ACE intends to resell or redistribute third-party data, paid commercial licensing is usually required.
