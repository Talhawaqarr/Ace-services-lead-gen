# ACE Services — Data Sources Research

This document summarizes authoritative APIs and data sources for U.S. construction projects, contractor/company enrichment, geocoding/routing, LLM/embedding providers, and transactional email providers. It records authentication, pricing, commercial-use notes, pagination/rate limits, and implementation status. This is an initial, non-exhaustive audit — each provider will need account verification and legal review before production use.

---

## Notes on methodology
- I prioritized official vendor documentation and government sources.
- I did not attempt to bypass any paywalls, CAPTCHAs, or protections.
- Where a vendor requires a paid subscription or account approval, I recorded that fact and linked to the vendor's signup/contact page.

---

## Federal / Government Sources

### SAM.gov (Contract Opportunities)
- Website: https://sam.gov/
- API / Data services: SAM's site includes Data Services and search; the site links to data and reports. (See https://sam.gov/ and its Data Services / Search pages.)
- Authentication: user accounts (login.gov) for some features; public searching is available; programmatic access details should be confirmed with the GSA data services pages.
- Pricing: free (government data).
- Commercial use: government data generally public, but check SAM.gov Terms of Use.
- Rate limits / pagination: documented on SAM.gov's Data Services pages — confirm before integration.
- Available fields: opportunities, award metadata, entity information (owner/agency, locations, NAICS/PSC codes). Bid-document availability varies by notice.
- Implementation status: candidate provider for federal opportunities; will implement adapter and verify endpoints.

### USAspending / FPDS (Federal contracting awards)
- Website / API: https://api.usaspending.gov/ (USAspending provides APIs for awarded contract data; FPDS is the underlying awards system)
- Authentication: most endpoints public; API key may be used for rate-limiting/analytics.
- Data: award/awardee data (post-award), useful for contractor history/enrichment but not necessarily new bid opportunities.
- Commercial use: public federal data; check site terms.
- Implementation status: include as enrichment/award-history source (post-award).

---

## Commercial Construction Project Providers (usually paid)

These vendors provide high-quality, frequently updated construction project leads but almost all require paid subscriptions / enterprise licensing for API/data feed access.

### ConstructConnect
- Website: https://www.constructconnect.com/
- API / Data feeds: ConstructConnect offers Project Intelligence and data feeds; documentation and API access require a commercial account / demo request.
- Authentication: account + API/subscription.
- Pricing/licensing: paid; contact sales for API access.
- Commercial use: subject to contract; data licensing typically forbids re-distribution.
- Available fields: project name, location, trades, documents, estimated value, contacts (depending on plan).
- Implementation status: plan provider adapter; requires ACE subscription or partnership.

### Dodge / Dodge Construction Network (Dodge Data & Analytics)
- Website: https://www.construction.com/
- API / Data feeds: Dodge provides APIs and data feeds (enterprise). Access generally requires a paid subscription and contract.
- Pricing/licensing: paid; enterprise agreements.
- Available fields: planning-stage signals, project specs, contacts, documents — enterprise feature set.
- Implementation status: commercial provider; adapter will be implemented after credential/contract acquisition.

### The Blue Book, iSqFt, PlanHub, BidClerk, etc.
- Many specialized bid boards/plan rooms exist (The Blue Book, PlanHub, iSqFt, BidClerk). All are typically commercial and may provide partner APIs or data feeds under contract.
- Implementation status: treat these as provider adapters in codebase; integrate once subscription/API access is obtained.

---

## Contractor / Company Enrichment APIs

### OpenCorporates (public company records)
- API docs: https://api.opencorporates.com/documentation/API-Reference
- Authentication: API token required; free accounts exist for "open data" projects, paid plans for commercial use that remove share-alike restrictions.
- License: OpenCorporates uses open data licensing for many sources but enforces share-alike for "open data" API keys; commercial plans remove those restrictions.
- Rate limits: documented per account/plan (examples: default low free limits; paid plans increase limits).
- Available fields: company registration data, addresses, filings, officers; includes provenance and confidence metadata.
- Implementation status: good candidate for company normalization & enrichment (especially legal entity matching).

### Google Places / Maps Business Data
- Use for business lookup and place metadata (website, phone, address).
- Authentication: API key with billing enabled; commercial terms apply.
- Rate limits/pricing: pay-as-you-go; lookups and place-details cost per request.
- Important: scraping Google/LinkedIn is prohibited — use official APIs only.

### Hunter.io, Clearbit, FullContact, ZoomInfo, Pipl, Dun & Bradstreet
- These offer contact/company enrichment (emails, company size, categories). Most are paid and have restricted terms for contact data and commercial usage.
- Many forbid resale; check each provider's license carefully.
- Implementation status: list as optional enrichment vendors; require ACE to obtain paid keys and confirm allowed usage.

### State Contractor License Boards / Public Records
- Many states publish contractor license registries and license lookup pages (e.g., California CSLB). Access patterns vary (public pages, some offer APIs).
- Implementation: build per-state adapters where available. Do not scrape pages that disallow automated access — prefer official API endpoints or manual verification instructions.

---

## Geocoding & Routing

### Google Maps Geocoding API
- Docs: https://developers.google.com/maps/documentation/geocoding/overview
- Authentication: API key + billing account required.
- Pricing: pay-as-you-go; free tier limited.
- Commercial use: permitted subject to Maps Platform Terms (may require map display for certain uses).
- Use-case: geocoding addresses, reverse geocoding.

### Mapbox Geocoding API
- Docs: https://docs.mapbox.com/api/search/geocoding/
- Authentication: Mapbox access token; free tier available; paid for production volume.
- Notes: Permanent storage of results requires billing/enterprise or permission (Mapbox permanent geocoding licensing rules).

### OpenCage / Here / OpenStreetMap Nominatim
- OpenCage: commercial API with free tier and rate-limits (https://opencagedata.com/api).
- HERE: enterprise-grade maps & routing with free tier (developer account) and paid tiers.
- Nominatim (OpenStreetMap): public instance has strict usage policy; heavy/commercial use requires self-hosting or paying a third-party provider.
- Implementation: support an abstract geocoder interface and allow switching between providers; default to Mapbox/OpenCage for production if ACE supplies API key.

Routing / road distances
- For driving distances: Google Directions API, Mapbox Directions, HERE Routing, or self-hosted OSRM/GraphHopper.
- Note: road distances may incur additional costs and are not always necessary — straight-line Haversine distance is acceptable for initial matching.

---

## LLMs & Embeddings

### OpenAI
- Docs: https://platform.openai.com/docs/guides/embeddings (developers.openai.com)
- Authentication: API key; paid usage.
- Capabilities: embeddings (text-embedding-3 / text-embedding-3-large and others), text generation, classification.
- Commercial use: permitted under OpenAI terms for many applications; review policy and acceptable usage.
- Implementation status: strong candidate for embeddings and email-generation prompts; will be added as a provider adapter and configurable LLM_PROMPT files.

### Cohere / Anthropic / Hugging Face Inference API
- Cohere: embeddings and generation with API key and paid plans.
- Anthropic: Claude API (paid / enterprise) for text generation.
- Hugging Face Inference: hosted models and embeddings; free tier limited, paid options available; self-hosting possible.
- Sentence-Transformers local models: run embeddings locally (GPU recommended) — good option if ACE prefers self-hosting to control data and costs.

---

## Transactional Email Providers

These providers offer API-based sending, event webhooks (deliveries, bounces, opens), templates, and domain authentication.

### SendGrid (Twilio SendGrid)
- Docs: https://docs.sendgrid.com/ (redirects to Twilio SendGrid docs)
- Authentication: API key.
- Features: webhooks (Event Webhook), templates, suppression lists, subaccounts, deliverability products.
- Pricing: free tier with limits; paid plans for higher volumes and deliverability features.
- Implementation status: primary candidate; implement `EmailProvider` adapter for SendGrid.

### Mailgun
- Docs: https://documentation.mailgun.com/
- Authentication: API key.
- Features: webhooks, events, batch sending, suppression, inbound parsing.
- Pricing: free tier/paid tiers.
- Implementation status: candidate adapter.

### Postmark
- Docs: https://postmarkapp.com/developer
- Features: strong transactional focus, explicit webhooks for delivery/bounce/open, built-in templates, inbound processing.
- Pricing: paid; developer-friendly docs and SDKs.
- Implementation status: candidate for transactional email adapter (recommended for transactional reliability).

### Amazon SES
- Docs: https://docs.aws.amazon.com/ses/latest/DeveloperGuide/Welcome.html
- Features: cost-effective, integrates with AWS SNS for bounces/complaints, IAM-based auth.
- Notes: SES requires domain verification and optional dedicated IPs for high volume.
- Implementation status: candidate, particularly for cost-sensitive high-volume sending.

---

## Summary / Implementation Recommendations (short)

NOTE: Project is now constrained to a $0 development budget. The guidance below prioritizes FREE and FREE-TIER sources and local fallbacks. Paid providers are marked and explicitly optional for POST-MVP.

- Build provider abstraction layers for: bid sources, company enrichment, geocoding, LLMs/embeddings, and email providers.
- Prioritize government data (SAM.gov, USAspending/FPDS) and other FREE sources for the MVP. Commercial project feeds (ConstructConnect, Dodge, PlanHub) are POST-MVP and optional.
- Use OpenCorporates and state license boards where they provide free access; otherwise use manually imported CSVs or synthetic datasets for enrichment during development.
- Default to LOCAL/DETERMINISTIC implementations for LLM/embeddings and email during development (templates, rule-based logic, local sentence-transformers where practical).
- Implement `docs/data-sources.md` (this file) and add a `providers/` adapter skeleton during Phase 2. Document required ENV variables in `.env.example` but do NOT require keys for the $0 MVP — provide safe defaults and `DRY_RUN` modes.

## Provider classifications (FREE / FREE TIER / PAID / REQUIRES CONTRACT / UNKNOWN)
- SAM.gov: FREE
- USAspending / FPDS: FREE
- OpenCorporates: FREE TIER (with license caveats) — may require paid plan for commercial redistribution
- State contractor license boards: FREE (varies by state; check each state's terms)
- OpenStreetMap / Nominatim: FREE (self-hosting recommended for heavy use)
- Mapbox: FREE TIER (but permanent geocode storage may require enterprise permission) — use only if ACE supplies key and agrees to license
- Google Maps: FREE TIER (billing account required) — POST-MVP preferred
- ConstructConnect, Dodge, The Blue Book, iSqFt, PlanHub, BidClerk: PAID / REQUIRES CONTRACT
- OpenAI, Cohere, Anthropic, Hugging Face hosted inference: FREE TIER / PAID (use local models or deterministic templates for $0 MVP)
- SendGrid, Mailgun, Postmark, SES: FREE TIER / PAID (DRY_RUN default; do not require keys for development)

Follow-up: see the updated ROADMAP and COST_MODEL for $0-mode specifics.

---

## Next steps (to progress Phase 1)
1. Decide which commercial project feed(s) ACE will subscribe to (ConstructConnect, Dodge, or PlanHub). We need account/contract to proceed.
2. Pick primary email provider (SendGrid, Postmark, Mailgun, or SES) and create API key for development.
3. Choose geocoding provider (Mapbox recommended) and obtain API token for batch geocoding.
4. Provision OpenAI (or alternative) API key for embeddings and email generation.
5. I'll scaffold the backend provider adapter interfaces and `.env.example` once you confirm which providers to prioritize.

---

References / Docs referenced during this pass:
- https://sam.gov/
- https://api.opencorporates.com/documentation/API-Reference
- https://www.constructconnect.com/
- https://www.construction.com/ (Dodge)
- https://docs.mapbox.com/api/search/geocoding/
- https://platform.openai.com/docs/guides/embeddings (redirects to developers.openai.com)
- https://www.twilio.com/docs/sendgrid/ (SendGrid docs)
- https://documentation.mailgun.com/en/latest/api_reference.html
- https://postmarkapp.com/developer
- https://docs.aws.amazon.com/ses/latest/DeveloperGuide/Welcome.html


(End of initial audit)
