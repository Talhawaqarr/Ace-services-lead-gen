# Observability Contract — ACE Services

Defines telemetry, logging, tracing, and SLOs for core services and provider adapters.

## Metrics
- Common labels: `service`, `environment`, `provider`, `operation`, `status`.
- Core metrics to emit:
  - `http_requests_total` (method, path, status)
  - `adapter_requests_total` (adapter, provider, status)
  - `llm_requests`, `llm_costs`, `llm_hallucinations`
  - `matching_latency_ms`, `matching_candidate_count`
  - `email_sends_total`, `email_bounces_total`, `email_deliveries_total`

## Tracing
- Use OpenTelemetry. Trace all request flows end-to-end with `trace_id`.
- Important spans: ingestion -> normalization -> feature_generation -> matching -> email_generation -> send

## Logging
- JSON structured logs. Log levels: debug/info/warn/error.
- DO NOT log raw secrets. Mask tokens and PII.

## SLOs & Alerts
- LLM latency SLO: 95% < 2s (for generation on premium model)
- Email send success: 99.5% within 24 hours
- Alert on: provider error rates > 5% sustained for 5m, high bounce-rate, missing consumer heartbeats.

## Dashboards
- High-level ops dashboard: system health, provider health, recent bounces, matching throughput.

This contract will be used to implement instrumentation in each adapter and service.