# Test Fixtures — ACE Services

Guidance for test fixtures, contract tests, and synthetic data for deterministic CI.

## Principles
- Tests must never call third-party providers in CI; use recorded fixtures or mocked adapters.
- Provide canonical fixture sets for projects, contractors, and emails.
- Use contract tests to validate adapter behavior against `PROVIDER_CONTRACTS.md`.

## Fixtures to provide
- `fixtures/projects/basic.json` — minimal project representation
- `fixtures/projects/missing_dates.json` — edge case
- `fixtures/contractors/basic.json`
- `fixtures/emails/draft.json`
- `fixtures/embeddings/small.npy` — small embedding vectors for similarity tests

## Adapter contract tests
- For each adapter, run tests that assert:
  - `list_projects` returns expected fields and handles pagination
  - `get_project_details` normalizes fields and returns `source_id`
  - Error handling: 429 triggers retry, 401 triggers abort

## Integration tests
- Matching pipeline integration test: run feature generation -> matching engine with synthetic dataset and assert top-N accuracy against labeled ground truth

## Mocking LLMs
- Provide deterministic LLM stubs returning pre-recorded responses in `fixtures/llm/` and a `llm_recorder` for local experimentation

These fixtures avoid external API calls and ensure repeatable CI.