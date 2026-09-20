# Phase 18 — Deployment and Runtime Hardening

## Goal

Provide a reproducible, zero-cost container runtime for the API while keeping production safety gates explicit.

## Container

The Dockerfile:
- uses Python 3.12 slim;
- installs only `requirements.txt`;
- runs as a non-root `app` user;
- exposes port 8000;
- provides a container healthcheck through `/health/ready`;
- starts only after the database is reachable;
- runs `alembic upgrade head` before starting Uvicorn.

## Local Docker Compose

`docker-compose.yml` provides a local PostgreSQL 16 database and API container. It is development-only configuration:
- `APP_ENV=development`;
- fixture ingestion;
- mock email/LLM providers;
- `DRY_RUN=true`;
- no secrets or paid services.

Start:

```bash
docker compose up --build
```

Then verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

Stop:

```bash
docker compose down
```

To remove the local database volume too:

```bash
docker compose down -v
```

## Production boundary

The Compose file is not a production deployment template.

Production must provide:
- a managed or separately secured PostgreSQL instance;
- `APP_ENV=production`;
- a non-mock email provider implementation;
- `DRY_RUN=false`;
- `API_AUTH_TOKEN`;
- secrets through the deployment secret mechanism;
- TLS termination and network controls;
- backups and restore testing;
- external log/metric collection.

The application currently validates the production configuration but does not claim that these controls are implemented by Docker Compose.

## Migration behavior

Migrations run once at API container startup. In a multi-replica deployment, do not allow every replica to race migrations; use a dedicated migration job or deployment step.

## Zero-cost boundary

This phase adds no paid infrastructure and does not activate live providers, email sending, LLMs, or external monitoring.
