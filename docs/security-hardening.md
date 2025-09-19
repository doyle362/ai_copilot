# Security Hardening Checklist

Use this playbook when preparing Level Analyst for production deployments.

## Authentication & Authorization

- **JWT secrets** – Set `DEV_JWT_HS256_SECRET` (for symmetric signing) or `JWT_PUBLIC_KEY_BASE64` (for asymmetric verification). The default development secret logs a warning when `ENVIRONMENT` is not `development`.
- **Token rotation** – Issue short-lived JWTs (24h or less) and automate rotation via your identity provider.
- **Zone access** – Confirm that PostgreSQL RLS policies are active for all tables containing zone-specific data (`insights`, `recommendations`, `historical_transactions`).

## Secrets Management

- Store database URLs, JWT keys, OpenAI API keys, and rate provider tokens in a secret manager (AWS Secrets Manager, Vault, etc.).
- Inject secrets at runtime via environment variables; avoid committing them to `.env` files or container images.

## Network & Transport

- Terminate TLS at the reverse proxy or load balancer (see `deploy/nginx/analyst.conf`).
- Enforce HTTPS redirects and HSTS (already present in the sample nginx config).
- Restrict database access to application subnets/security groups.

## Logging & Monitoring

- Tune `LOG_LEVEL` and `LOG_JSON` to integrate with centralized logging.
- Ship logs to a SIEM/security monitoring platform to detect anomalies (e.g., repeated failed auth).
- Enable Gunicorn access/error logs for auditing.

## Dependency & Vulnerability Management

- Run dependency scans regularly (`pip install safety` or GitHub Dependabot). Review CVEs for `fastapi`, `uvicorn`, `gunicorn`, and `asyncpg`.
- Keep Docker base image (`python:3.11-slim`) up to date with security patches.

## Database Hygiene

- Rotate Supabase credentials annually or when staff changes.
- Enforce least-privilege roles; the application should connect with a limited user rather than the default `postgres` account.

## Automated Checks

- Add CI jobs that:
  - Lint and run tests (`pytest`).
  - Execute dependency vulnerability scans.
  - Verify that `DEV_JWT_HS256_SECRET` is not set to the default value in production branches.

## Incident Response

- Define alert thresholds for failed scheduler runs and API error spikes.
- Archive logs for at least 30 days to support investigations.

