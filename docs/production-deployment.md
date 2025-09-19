# Production Deployment Guide

This guide outlines the key steps for running the Level Analyst service in a production environment.

## Runtime Architecture

- **Application server** – Gunicorn manages Uvicorn workers (`analyst.main:app`) using the configuration in `services/analyst/gunicorn_conf.py`. Worker counts, timeouts, and logging destinations are controlled through `GUNICORN_*` environment variables.
- **Reverse proxy** – Front the application with nginx (or an equivalent load balancer) to terminate TLS, serve static assets, and forward API traffic. A reference configuration is provided in `deploy/nginx/analyst.conf` and assumes the static iframe bundle is mounted at `/srv/level-analyst/static/iframe/`.
- **Containerization** – The updated `services/analyst/Dockerfile` installs Gunicorn and launches it by default. `docker-compose.yml` exposes tuning knobs for worker counts and timeouts via environment variables.
- **Scheduler** – APScheduler runs inside the API process (default enabled) to regenerate insights/recommendations once per day. Control cadence with `SCHEDULER_*` environment variables or disable entirely with `SCHEDULER_ENABLED=false`.

## Configuration & Secrets

- Runtime settings are sourced from environment variables via `analyst.config.Settings`. Optionally set `ANALYST_ENV_FILE` to point at an `.env` file (absolute or repository-relative path). If unset, the loader falls back to the repository root `.env` when present.
- Store sensitive values (database credentials, JWT secrets, API keys) in a secrets manager and inject them as environment variables at deploy time. Avoid baking credentials into images.
- Scheduler-related options:
  - `SCHEDULER_ENABLED`: toggle background jobs (`true` by default).
  - `SCHEDULER_DAILY_REFRESH_HOUR_UTC` / `SCHEDULER_DAILY_REFRESH_MINUTE_UTC`: cron-style UTC time for the daily refresh.
  - `SCHEDULER_ZONE_IDS`: explicit comma-separated list of zones to analyze; omit to auto-discover from `historical_transactions`.
- Logging options:
  - `LOG_LEVEL`: root log level (`INFO` default).
  - `LOG_JSON`: set to `true` to emit structured JSON logs for ingestion by log pipelines.

## Static Assets

- Build the React dashboard (`web/card`) and copy the output into `services/analyst/static/iframe/` before containerization, or mount the directory separately. The nginx sample serves `/card/` and `/static/` directly to offload that traffic from Gunicorn workers.

## Observability & Operations

- Gunicorn stdout/stderr integrate with the container runtime logging driver. For production, forward logs to a centralized system and monitor worker restarts.
- Configure health checks against `/health/` upstream and tighten nginx proxy timeouts to match your load profile.

## SSL/TLS

- Replace the placeholder certificate directives in `deploy/nginx/analyst.conf` with the paths issued by your certificate authority (e.g., Let’s Encrypt). Enforce HTTPS and HSTS as shown.

## Scaling Considerations

- Tune `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, and related variables based on CPU/memory availability and request latency.
- When horizontal scaling across multiple containers or instances, ensure sticky sessions are not required (JWT auth is stateless) and share static assets through object storage or build pipelines.
