# Security Design — ACE Services

Security policies for the ACE Services platform. This covers secrets, authentication, authorization, data handling, webhooks, and other security controls.

## Secrets management
- All secrets and API credentials must be provided via environment variables or an external vault (e.g., HashiCorp Vault, AWS Secrets Manager).
- Do not commit secrets to git. Add `.env.example` with variable names only.

## Authentication
- Use OAuth2 / JWT for API access and session management via FastAPI's security utilities.
- Passwords hashed with Argon2 or bcrypt.
- Multi-factor authentication recommended for admin users.

## Authorization
- RBAC with roles: `admin`, `user`, `viewer`.
- Granular permissions for sensitive actions (sending emails, connecting providers, deleting records).

## API key protection
- Provider credentials stored server-side only.
- Admin UI never exposes full keys; show masked values and last_updated.

## Database security
- Use least-privilege DB users (separate users for migrations/admin vs app readonly where appropriate).
- Use SSL/TLS for DB connections in production.

## Input validation
- Strict Pydantic models for every API request and provider adapter response validation.
- Treat all external provider data as untrusted.

## File handling
- Document uploads stored in S3-compatible storage with restricted permissions.
- Virus scanning recommended for file uploads if accepting user-supplied files.

## Webhook verification
- Validate signature headers for email provider webhooks (e.g., SendGrid signature, Postmark X-Postmark-Signature).
- Replay protection using unique event IDs.

## Rate limiting
- API rate limiting per user and per IP using middleware (e.g., FastAPI-limiter or nginx ratelimit) to protect against abuse.

## Audit logs
- All envelope-changing events logged to `audit_logs` with actor, action, and details.
- Retention policy for audit logs per compliance.

## Prompt injection and LLM safety
- Treat all external text as untrusted. Use strict prompt templates and include verification steps to prevent LLM hallucinations.
- In email generation prompts, instruct the model not to invent facts and to cite the source of every claim (source field must be inserted).

## Data encryption
- Encrypt sensitive fields at rest if required (e.g., personal contact details) using DB column-level encryption or application-layer encryption.

## Backups & DR
- Regular DB backups with automated restore tests. S3 backups for files.

## Compliance
- Provide suppression list and unsubscribe handling for email compliance.
- Respect Do Not Contact and GDPR where applicable for EU contacts.

## Incident response
- Define incident response playbooks for data breach, provider key leaks, or mass bounces detected by email provider.

This security baseline is a starting point and must be adapted to ACE's operational compliance needs.
