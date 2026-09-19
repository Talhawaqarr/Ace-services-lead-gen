# Observability & Monitoring — ACE Services

Monitoring objectives
- Ensure ingestion pipelines are healthy
- Track matching throughput and latency
- Monitor email deliverability and bounces
- Alert on provider auth failures and high error rates

Key metrics
- Provider sync: projects ingested / sync run, errors per run
- Jobs: job duration, success/failure rate, retry counts
- Matching: matches generated per project, precision@K (tracking via feedback)
- Email: sends/day, bounces/day, open rate, reply rate, delivery latency
- Costs: embedding calls, geocoding calls, email sends

Logging
- Structured JSON logs with correlation IDs (project_id, job_id)
- Retain logs for X days (configurable) and provide log search for operators

Tracing
- Add distributed tracing for long pipelines (e.g., OpenTelemetry) linking ingestion → normalization → matching → send

Dashboards & Alerts
- Dashboards: ingestion health, matching KPIs, email deliverability, cost trends
- Alerts: high job failure rate (>X%), provider auth errors, bounce spikes, high cost rate of embeddings

Tools (suggested)
- Metrics: Prometheus + Grafana or hosted (Datadog)
- Logs: ELK stack or hosted (Logflare, Datadog logs)
- Tracing: Jaeger or a managed tracing provider

Runbooks
- Clear runbooks for requeuing DLQ jobs, restarting workers, rotating provider keys, and investigating high bounce rates.

This document complements `OPERATIONAL_PLAN.md` and provides the monitoring specifics for SLAs and alerts.
