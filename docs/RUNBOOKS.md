# Runbooks — ACE Services

Operational runbooks for common incidents and routine operations.

## Incident: Provider outage
1. Identify provider via `adapter.health_check()` and metrics.
2. Switch to fallback provider (if available) or enable degraded mode in UI.
3. Notify stakeholders and open incident ticket.
4. Monitor metrics and restart adapter if transient.

## Incident: Mass bounce spike
1. Pause all active campaigns.
2. Check bounce webhooks and logs to identify patterns.
3. Add permanent bounces to suppression list.
4. Contact email provider support; follow incident response plan.

## Routine: Add new provider
1. Create adapter following `PROVIDER_CONTRACTS.md`.
2. Add contract tests and fixtures.
3. Add env vars to `ENVIRONMENT.md` and secrets manager.
4. Run smoke tests and enable in staging only.

## Routine: Reindex embeddings
1. Pause matching consumers.
2. Run `reindex_embeddings` job with controlled concurrency.
3. Monitor embedding queue and backpressure.
4. Re-enable consumers after validation.

Keep runbooks concise and executable by on-call operator.