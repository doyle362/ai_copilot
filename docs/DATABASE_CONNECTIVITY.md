# Database Connectivity Guide

## Quick Diagnostics

Run diagnostics to identify connectivity issues:

```bash
# HTTP endpoint (API must be running)
curl http://localhost:8080/diag/db | jq

# CLI script
python3 scripts/db-check.py

# Make target
make db-check
```

## Common Connection Issues

### 1. Network/Firewall Timeouts

**Symptoms**: `ConnectionTimeout` or `TimeoutError`

**Solutions**:
- Try Supabase connection pooler on port 6543:
  ```bash
  # Change port in SUPABASE_DB_URL
  postgres://user:pass@db.xxx.supabase.co:6543/postgres?sslmode=require
  ```
- Check corporate firewall/VPN settings
- Test from different network (mobile hotspot)

### 2. SSL/TLS Issues

**Symptoms**: SSL-related errors

**Solutions**:
- Ensure `?sslmode=require` in connection string:
  ```bash
  SUPABASE_DB_URL=postgres://user:pass@host:port/db?sslmode=require
  ```
- Try `?sslmode=prefer` as fallback

### 3. Authentication Failures

**Symptoms**: `password authentication failed`

**Solutions**:
- URL-encode special characters in password:
  - `@` → `%40`
  - `:` → `%3A`
  - `/` → `%2F`
  - `?` → `%3F`
  - `&` → `%26`
  - `#` → `%23`
  - `%` → `%25`
- Use simpler passwords without special characters
- Verify credentials in Supabase dashboard

### 4. DNS Resolution

**Symptoms**: `nodename nor servname provided, or not known`

**Solutions**:
- Check DNS resolution: `nslookup db.xxx.supabase.co`
- Try alternative DNS servers (8.8.8.8, 1.1.1.1)
- Verify hostname in SUPABASE_DB_URL

## Recommended Connection Strings

### Development (Local)
```bash
SUPABASE_DB_URL=postgres://ai_analyst_copilot:PASSWORD@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### Behind Corporate Firewall
```bash
SUPABASE_DB_URL=postgres://ai_analyst_copilot:PASSWORD@db.xxx.supabase.co:6543/postgres?sslmode=require
```

### Alternative SSL Settings
```bash
SUPABASE_DB_URL=postgres://ai_analyst_copilot:PASSWORD@db.xxx.supabase.co:5432/postgres?sslmode=prefer
```

## Environment Variables

Set in `.env` file:

```bash
# Primary database connection
SUPABASE_DB_URL=postgres://ai_analyst_copilot:PASSWORD@db.xxx.supabase.co:5432/postgres?sslmode=require

# Optional: read-only connection for heavy queries
SUPABASE_DB_URL_RO=postgres://ai_analyst_copilot:PASSWORD@db.xxx.supabase.co:6543/postgres?sslmode=require

# Optional: override SSL mode globally
PGSSLMODE=require
```

## Testing Connectivity

The diagnostics endpoint `/diag/db` returns:

```json
{
  "env": {
    "SUPABASE_DB_URL_present": true,
    "PGSSLMODE": null
  },
  "tcp": {
    "db.xxx.supabase.co:5432": {"ok": true, "detail": "ok", "ms": 45.2},
    "db.xxx.supabase.co:6543": {"ok": true, "detail": "ok", "ms": 48.1}
  },
  "psycopg_connect": {
    "ok": true,
    "roundtrip_ms": 152.3,
    "server_time": "2024-01-15 10:30:45",
    "user": "ai_analyst_copilot",
    "db": "postgres"
  },
  "hints": []
}
```

## Troubleshooting Steps

1. **Test TCP connectivity**: Check if ports 5432/6543 are reachable
2. **Verify DNS**: Ensure hostname resolves correctly
3. **Check SSL**: Try different sslmode values
4. **Test auth**: Verify username/password work in Supabase dashboard
5. **Try pooler**: Use port 6543 if 5432 is blocked
6. **Network change**: Test from different network/VPN off

## Gotchas

- .env lines must be unquoted (no `SUPABASE_DB_URL="..."`).
- Prefer `postgresql://` over `postgres://`.
- Ensure the DSN is one line; watch for hidden characters (use: `cat -A .env`).
- Exact host: `db.xzokblkebghmqargqgjb.supabase.co`
- Pooler port 6543 often works when 5432 is blocked.
- URL-encoding for special chars if you ever change the password: @ %40, : %3A, / %2F, ? %3F, & %26, # %23, % %25.