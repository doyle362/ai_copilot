import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": None, "env_file_encoding": "utf-8", "case_sensitive": False}

    supabase_db_url: Optional[str] = None
    supabase_db_url_ro: Optional[str] = None

    jwt_issuer: str = "app.lvlparking.com"
    jwt_public_key_base64: Optional[str] = None
    dev_jwt_hs256_secret: str = "dev-local-please-rotate-9b1b7df7b6f54c8bbf7a9c"
    dev_zone_ids: str = "z-110,z-221"
    org_id: str = "org-demo"

    openai_api_key: Optional[str] = None
    openai_model_fast: str = "gpt-4o-mini"
    openai_model_reason: str = "o1-mini"

    rates_api_base_url: Optional[str] = None
    rates_api_token: Optional[str] = None

    api_port: int = 8088
    cors_allow_origins: str = "http://localhost:5173,https://app.lvlparking.com,https://analyst.yourdomain.com"
    analyst_auto_apply: bool = False
    analyst_require_approval: bool = True
    tz: str = "America/Chicago"

    # Elasticity probe settings
    analyst_enable_elasticity_probe: bool = False
    analyst_probe_max_delta: float = 0.10
    analyst_probe_default_deltas: str = "[-0.05,-0.02,0.02,0.05]"
    analyst_probe_horizon_days: int = 14

    scheduler_enabled: bool = True
    scheduler_daily_refresh_hour_utc: int = 9  # Defaults to 09:00 UTC (~4am Central)
    scheduler_daily_refresh_minute_utc: int = 0
    scheduler_zone_ids: Optional[str] = None

    log_level: str = "INFO"
    log_json: bool = False

    environment: str = "development"

    observability_tracing_enabled: bool = False
    observability_metrics_enabled: bool = True
    otel_exporter_endpoint: Optional[str] = None
    otel_exporter_insecure: bool = True
    otel_service_name: str = "level-analyst"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",")]

    @property
    def dev_zone_ids_list(self) -> List[str]:
        return [zone.strip() for zone in self.dev_zone_ids.split(",")]

    @property
    def scheduler_zone_ids_list(self) -> List[str]:
        if self.scheduler_zone_ids:
            return [zone.strip() for zone in self.scheduler_zone_ids.split(",") if zone.strip()]
        return []


def _resolve_env_file() -> Optional[str]:
    candidate = os.getenv("ANALYST_ENV_FILE")

    if candidate:
        path = Path(candidate)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / candidate
        return str(path)

    fallback = Path(__file__).resolve().parents[2] / ".env"
    return str(fallback) if fallback.exists() else None


settings = Settings(_env_file=_resolve_env_file())
