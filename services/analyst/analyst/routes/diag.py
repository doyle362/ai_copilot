from __future__ import annotations
import os, socket, time, json
from typing import Dict, Any, List, Optional, Tuple
from fastapi import APIRouter
import psycopg
from psycopg.rows import dict_row

router = APIRouter(prefix="/diag", tags=["diagnostics"])

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    # Try environment variable first, then check settings module
    from ..config import settings
    v = os.getenv(name, default)
    if v in ("", None) and hasattr(settings, name.lower()):
        v = getattr(settings, name.lower())
    return v if v not in ("", None) else None

def _parse_dsn_parts(dsn: str) -> Dict[str, str]:
    # Minimal parse: try psycopg conninfo and fallback to urlparse if needed
    try:
        info = psycopg.conninfo.ConnInfo(dsn)
        return {
            "host": info.host or "",
            "port": str(info.port or 5432),
            "dbname": info.dbname or "",
            "user": info.user or "",
            "sslmode": info.sslmode or "",
        }
    except Exception:
        return {"host": "", "port": "", "dbname": "", "user": "", "sslmode": ""}

def _tcp_check(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, str, float]:
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True, "ok", time.time() - t0
    except socket.gaierror as e:
        return False, f"dns_error: {e}", time.time() - t0
    except TimeoutError:
        return False, "timeout", time.time() - t0
    except OSError as e:
        return False, f"os_error: {e}", time.time() - t0
    finally:
        try:
            s.close()
        except Exception:
            pass

@router.get("/db")
def diag_db() -> Dict[str, Any]:
    """
    Connectivity diagnostics for the configured Postgres (Supabase).
    Returns structured results for TCP to 5432/6543 and a psycopg connect attempt with sslmode=require.
    """
    dsn = _env("SUPABASE_DB_URL", "") or ""
    result: Dict[str, Any] = {
        "env": {
            "SUPABASE_DB_URL_present": bool(dsn),
            "PGSSLMODE": _env("PGSSLMODE"),
        },
        "tcp": {},
        "psycopg_connect": {},
        "hints": []
    }
    if not dsn:
        result["hints"].append("Set SUPABASE_DB_URL in .env (include ?sslmode=require).")
        return result

    parts = _parse_dsn_parts(dsn)
    host = parts.get("host") or "db.invalid"
    # test both ports regardless of DSN; common fix is to use pooler 6543
    checks = [(host, 5432), (host, 6543)]
    for h, p in checks:
        ok, msg, dur = _tcp_check(h, p)
        result["tcp"][f"{h}:{p}"] = {"ok": ok, "detail": msg, "ms": round(dur * 1000, 1)}
        if (not ok) and p == 6543:
            result["hints"].append("If 5432 is blocked, try Supabase pooler on port 6543.")

    # psycopg connect attempt with sslmode=require (it will respect the DSN query)
    try:
        t0 = time.time()
        with psycopg.connect(dsn, connect_timeout=4, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("select now() as server_time, current_user, current_database() as db")
                row = cur.fetchone()
        result["psycopg_connect"] = {
            "ok": True,
            "roundtrip_ms": round((time.time() - t0) * 1000, 1),
            "server_time": str(row.get("server_time") if row else None),
            "user": row.get("current_user") if row else None,
            "db": row.get("db") if row else None
        }
    except Exception as e:
        result["psycopg_connect"] = {
            "ok": False,
            "error": str(e.__class__.__name__),
            "detail": str(e)
        }
        # common helpful hints
        if "ssl" in str(e).lower():
            result["hints"].append("Ensure '?sslmode=require' is present in SUPABASE_DB_URL.")
        if "timeout" in str(e).lower():
            result["hints"].append("Network timeout: try port 6543 (pooler) or another network/VPN off.")
        if "password authentication" in str(e).lower():
            result["hints"].append("Check user/password. Avoid special chars that need URL-encoding (@ : / ? & # %).")
    return result