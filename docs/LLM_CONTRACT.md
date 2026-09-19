# LLM Contract — ACE Services

Purpose: Define how LLMs (generation and embeddings) will be used safely, auditable, and with deterministic fallbacks.

## Supported tasks
- Email personalization generation (`generate_email_personalization`)
- Short explanations for matches (`explain_match`)
- Embedding generation for texts (`embed_texts`)

## Input schemas
- `generate_email_personalization` input:
  - `project_id` (uuid)
  - `project_summary` (string)
  - `contractor_brief` (string)
  - `claims` (list of {fact, source_id}) — REQUIRED: list of factual claims to be included; derived from canonical DB
  - `tone` (optional)
  - `prompt_id` (template id)

- `embed_texts` input:
  - `texts`: List[str]
  - `model`: str

## Output schemas
- `generate_email_personalization` output:
  - `subject` (string)
  - `body` (string)
  - `claims_used`: List of {claim, source, confidence}
  - `llm_metadata`: {model, tokens_used, request_id, truncated}
  - `safety_checks`: {prompt_injection_flag: bool, hallucination_checks: [issues]}

- `embed_texts` output:
  - `embeddings`: List[vector]
  - `model` and `vector_dim`
  - `usage` metadata for cost tracking

## Validation
- All `claims_used` must match items in the input `claims` list or be empty.
- If the model inserts an unverifiable factual claim, the response must include `safety_checks.hallucination_issues` and the generation should be rejected unless manually approved.
- Responses must not include undisclosed PII or contact data unless sourced from verified fields with provenance.

## Grounding requirements
- Every factual statement in generated output must be traced to a `source_id` (project or contractor field) and included in `claims_used`.
- The contract requires that `claims` (from canonical DB) is authoritative; LLM cannot invent claims.

## Model configuration
- Default model: `text-embedding-3` for embeddings, `gpt-4o`-like for generation — configurable via `ENV`.
- Token/cost tracking must be implemented and reported to telemetry.

## Timeouts & Retries
- Default timeout: 30s for generate, 60s for batch embed operations.
- Retry policy: Exponential backoff for 429/5xx with capped attempts (3 attempts) except for 401/403.

## Fallbacks
- If generation fails or hallucination detected, system falls back to deterministic template-based generation (static templates) and flags email for manual editing.
- If embedding provider fails, fallback to local sentence-transformers if available; otherwise mark semantic features as unavailable.

## Prompt injection protection
- Sanitize inputs; strip input fields that look like instructions.
- Prepend a system instruction forbidding the model from altering or inventing claims.
- Detect suspicious outputs via heuristics (new URLs, unusual numeric values) and mark `prompt_injection_flag`.

## Hallucination handling
- Compare generated factual claims against canonical DB. If mismatches found, mark `hallucination_issues` and do not auto-send.

## Observability
- Emit `llm.requests`, `llm.errors`, `llm.hallucinations`, `llm.costs` metrics.
- Store `llm_responses` in DB for audit and reproduction.

## Security
- Do not include raw prompt text in logs in production; store masked prompts in `llm_prompts` with access control.

This contract defines safe LLM usage patterns for ACE. Implementations must adhere strictly; any deviation requires approval.