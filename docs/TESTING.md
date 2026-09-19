# Testing Strategy — ACE Services

Testing layers and approach for the application.

## Testing Pyramid
- Unit tests: pure functions, normalization, scoring logic
- Integration tests: provider adapters, database interactions, background jobs
- End-to-end tests: critical user flows (review project, match, send email)

## Tools
- Python: pytest, pytest-asyncio
- Use Testcontainers for integration tests (Postgres, Redis)
- Fixtures for provider responses (recorded fixtures or VCR-like approach)

## CI
- Run unit tests and lint on PRs
- Run integration tests in main branch with service containers

## Mocks & Stubs
- Provider adapters should be testable via injected HTTP client or recorded fixtures
- Use contract tests for provider adapter correctness

## Test data
- Use representative samples with edge cases (missing fields, multiple trades, bad geo)

## Observability in tests
- Collect coverage and critical metrics thresholds

This testing strategy ensures safe evolution of matching logic and adapter code.
