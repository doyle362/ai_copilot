import logging

from .config import settings

logger = logging.getLogger(__name__)


def emit_security_warnings() -> None:
    """Log actionable security warnings for unsafe configuration choices."""

    if settings.environment.lower() not in {"development", "dev", "test"}:
        if settings.dev_jwt_hs256_secret.startswith("dev-local-please-rotate"):
            logger.warning(
                "Default development JWT secret detected in %s environment. "
                "Set DEV_JWT_HS256_SECRET to a secure value or configure JWT_PUBLIC_KEY_BASE64.",
                settings.environment,
            )

        if settings.supabase_db_url and "YOUR_PASSWORD" in settings.supabase_db_url:
            logger.warning(
                "Supabase connection string still contains placeholder password. Update SUPABASE_DB_URL before deploying."
            )

    if not settings.supabase_db_url:
        logger.warning("SUPABASE_DB_URL is not configured; database-dependent features will be unavailable.")

    if not settings.jwt_public_key_base64 and not settings.dev_jwt_hs256_secret:
        logger.warning("No JWT verification material configured. Set JWT_PUBLIC_KEY_BASE64 or DEV_JWT_HS256_SECRET.")

