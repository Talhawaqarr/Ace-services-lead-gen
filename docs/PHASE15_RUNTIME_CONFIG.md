# Phase 15 — Runtime and Configuration Hardening

## Purpose

Centralize runtime configuration and make the default development path safe and reproducible.

## Runtime defaults

- APP_ENV=development
- INGESTION_MODE=fixture
- EMAIL_PROVIDER=mock
- LLM_PROVIDER=mock
- DRY_RUN=true
- no SAM.gov API key required

These defaults keep local development offline and prevent accidental external outreach.

## Configuration validation

src/config.py is the single runtime configuration boundary. It validates:

- supported environment names
- fixture-only ingestion until a live provider is explicitly implemented
- non-negative email rate limits
- no DRY_RUN=true in production
- no mock email provider in production

Secrets such as SAMGOV_API_KEY are read from environment variables and are not logged or returned by API configuration responses.

## Current provider behavior

Phase 15 does not add live SAM.gov calls. The existing SAM.gov providers remain fixture-backed. A future live provider must be a separate adapter behind the provider contracts and explicit configuration.

## Testing

Configuration tests verify safe defaults and reject unsafe configuration combinations.
