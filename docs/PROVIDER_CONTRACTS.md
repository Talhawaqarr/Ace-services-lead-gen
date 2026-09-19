# Provider Contracts — ACE Services

This document defines the abstract interface contracts for external providers. These are documentation-only contracts describing inputs, outputs, and error semantics that adapters must implement.

General rules for all provider contracts
- Adapters must implement health_check() returning {status, info, last_checked}.
- Adapters must be idempotent for upsert operations using `source+source_id` as idempotency key.
- All responses treated as untrusted; adapters must validate and normalize fields before returning canonical structures.
- Observability: adapters must emit metrics for requests, errors, latencies, and rate-limit events.

## BidProvider / ProjectProvider
- Purpose: Fetch project/opportunity listings and details.
- Methods:
  - `list_projects(filters, page_token) -> {projects: [ProjectRaw], next_page_token, meta}`
  - `get_project_details(source_id) -> ProjectRaw`
  - `health_check() -> {status, info}`
- ProjectRaw (minimal fields expected): `{source, source_id, title, description, location: {address, city, state, zip}, dates: {bid_date}, trades: [], estimated_value, documents: []}`
- Errors:
  - Retryable: 429 (rate limit), 5xx server errors, transient network errors
  - Non-retryable: 401/403 (auth invalid), 404 (resource gone)
- Timeouts: default 30s; allow override per-provider.
- Rate limit behavior: adapters must honor `Retry-After` and implement per-provider rate-limiters.
- Idempotency: use `source+source_id` keys on upsert.
- Caching: responses may be cached for short TTLs; store raw payloads in `projects_raw`.

## ContractorProvider
- Purpose: Search and fetch contractor/company data.
- Methods:
  - `search_companies(query, page_token) -> {companies: [CompanyRaw], next_page_token}`
  - `get_company_details(source_id) -> CompanyRaw`
- CompanyRaw minimal fields: `{source, source_id, company_name, addresses, website, phone, officers, filings}`
- Errors: same classification as BidProvider.

## EnrichmentProvider
- Purpose: Enrich company/contractor data (licenses, emails, firmographics)
- Methods:
  - `enrich_company(company_id) -> {licenses:[], emails:[], confidence_scores}`
  - `verify_email(email) -> {email, deliverable: bool, details}`
- Caching: expensive enrichment should be cached and rate-limited.

## GeocodingProvider
- Purpose: Geocode addresses and provide reverse geocoding.
- Methods:
  - `geocode(address) -> {latitude, longitude, provider, confidence, raw}`
  - `batch_geocode(addresses) -> stream of results`
- License: adapters must expose whether persistent storage of coordinates is allowed.
- Errors: 429 should be treated as retryable with backoff.

## EmailProvider
- Purpose: Send transactional emails and receive webhooks for events.
- Methods:
  - `send_email(email_payload) -> {message_id, status_code, provider_response}`
  - `get_status(message_id) -> {status, details}`
  - `parse_webhook(request_payload) -> [EmailEvent]`
  - `verify_webhook(signature_headers, body) -> bool`
- Idempotency: adapters must support idempotent send via `idempotency_key` where provider supports it; otherwise the app must implement dedupe.
- Rate limiting: respect provider rate limits and implement circuit-breaker.

## LLMProvider / EmbeddingProvider
- Purpose: Text generation and embeddings.
- Methods:
  - `embed(texts: List[str], model, options) -> List[embedding_vectors]`
  - `generate(prompt: str, model, params) -> {text, usage, tokens, metadata}`
  - `health_check()`
- Errors:
  - Retryable: transient network, 429 with backoff.
  - Non-retryable: invalid API key, model not found.
- Token/cost tracking: adapters must return usage metrics for cost accounting.
- Fallback: support alternate model or local model when available.

## Observability
- Each adapter must emit metrics: `adapter.requests`, `adapter.errors`, `adapter.latency_ms`, `adapter.rate_limit_hits`.
- Log raw responses at debug level only; strip secrets.

---

These provider contracts will be used to implement test fixtures, contract tests, and adapter skeletons. Do NOT implement real providers now; implement test-only mocks against these contracts in CI.