# Phase 17 — Observability Hardening

## Scope

Provide a lightweight observability foundation without adding paid services or new runtime dependencies.

## Request logging

Every API request receives a correlation ID.

- Client-supplied `X-Request-ID` is preserved.
- If absent, the API generates a UUID request ID.
- The response returns the ID in `X-Request-ID`.
- Requests are logged as JSON with method, path, status code, duration, and request ID.
- The logger does not log authorization headers or secret values.

## Health

Existing liveness and database readiness endpoints remain available.

## Deliberate limitation

This phase does not add Prometheus, Grafana, OpenTelemetry, hosted logging, distributed tracing, or paid monitoring. Those can be attached later using the same request correlation field.

## Validation

Run the focused Phase 17 tests, then the full suite before merging.
