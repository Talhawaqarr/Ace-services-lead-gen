# Phase 16 — API Authentication Hardening

## Scope

Add a zero-cost production API access boundary without introducing a user database or paid identity provider.

## Runtime behavior

- Development/test/staging: authentication is disabled by default.
- Production: API_AUTH_TOKEN is required by runtime configuration.
- Business/API routes require Authorization: Bearer <API_AUTH_TOKEN>.
- /health and /health/ready remain public.
- Missing or invalid credentials return HTTP 401.
- Missing production configuration returns a configuration validation error before the API can be considered ready.

## Security properties

- Secrets are stored in environment configuration, not source control.
- The bearer token uses constant-time comparison.
- The token is excluded from Settings repr output.
- API responses do not expose the configured token.

## Deliberate limitation

This phase provides service-level API authentication, not multi-user identity or RBAC. OAuth/OIDC, user accounts, roles, and granular permissions remain future work.

## Validation

Run the focused Phase 16 tests, then the full suite before merging.