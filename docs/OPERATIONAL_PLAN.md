# Operational Plan — ACE Services

This document gives high-level operational guidance for running ACE Services in production: deployment, monitoring, backups, scaling, and SLAs.

## Deployment
- Use Docker images for app, workers, and dependencies.
- Orchestrate with Kubernetes for scalability or `docker-compose` for early staging.
- Use CI/CD pipeline to build images, run tests, and deploy to environment.

## Monitoring & Alerting
- Metrics: request latencies, job processing times, match counts, email send rates, bounce rates
- Logs: structured JSON logs for all services
- Alerts: high bounce rate, many job failures, auth errors from providers

## Backups & DR
- Daily DB backups with point-in-time recovery where feasible
- S3 object backups and lifecycle policies

## Scaling
- Horizontal scale workers for ingestion and embedding computation
- Database scaling: read-replicas for heavy read queries (dashboard)

## Cost control
- Throttle embedding requests; batch and cache embeddings
- Monitor email provider costs and set daily caps

## SLAs
- Ingestion SLA: projects from primary provider available within X minutes
- Matching SLA: match generation within Y seconds for new projects

## Security & Compliance
- See SECURITY.md for baseline controls and implementation specifics

## Runbook snippets
- How to restart workers, requeue failed jobs, and refresh embeddings

This plan is intentionally high-level; next steps include runbooks and CI/CD pipeline definitions.
