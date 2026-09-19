# Security Controls — ACE Services

This document summarizes the security controls and compliance considerations for the ACE platform.

## Access Control
- Use RBAC with least privilege. Roles: `admin`, `operator`, `auditor`, `developer`.
- Separate keys for ingestion, enrichment, and sending services.

## Data Protection
- Encrypt data at rest (DB encryption or disk-level), and in transit (TLS everywhere).
- Mask PII in logs; store raw PII only in `sensitive_data` table with strict access controls.
- Rotate keys periodically and maintain an audit log for key access.

## Secrets & Keys
- Use central secrets manager. Avoid long-lived personal tokens.

## Network
- VPC-only DB access in production; private subnets for worker pools.
- Use ingress rate-limits and WAF for public endpoints.

## Auditing & Logging
- All actions affecting `emails`, `matches`, `contractors`, `projects` must be auditable with `actor_id`, `actor_type`, `timestamp`, `action`, `before`, `after`.

## Incident Response
- Define contact list, runbooks for data breaches, mass-bounces, or provider outages.

## Compliance
- Data retention and deletion policies; comply with CAN-SPAM for emails.

These controls are a baseline; expand with legal guidance for specific providers and jurisdictions.