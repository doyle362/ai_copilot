#!/usr/bin/env bash
set -euo pipefail

DB_HOST="db.xzokblkebghmqargqgjb.supabase.co"
REMOTE_PORT="${1:-6543}"       # 6543 = pooler (recommended), 5432 = direct
LOCAL_PORT="${LOCAL_PORT:-15432}"

if [[ -z "${TUNNEL_HOST:-}" || -z "${TUNNEL_USER:-}" ]]; then
  echo "Usage: TUNNEL_HOST=your.vm TUNNEL_USER=you ./scripts/pg_tunnel.sh [6543|5432]"
  echo "Optional: TUNNEL_KEY=~/.ssh/id_ed25519 LOCAL_PORT=15432"
  exit 1
fi

SSH_OPTS=()
[[ -n "${TUNNEL_KEY:-}" ]] && SSH_OPTS+=( -i "${TUNNEL_KEY}" )
SSH_OPTS+=( -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 )

echo "== Opening SSH tunnel =="
echo " Local  localhost:${LOCAL_PORT}  →  ${DB_HOST}:${REMOTE_PORT}  via  ${TUNNEL_USER}@${TUNNEL_HOST}"
echo
echo "While this is running, set these .env overrides (in another shell):"
if [[ "${REMOTE_PORT}" == "6543" ]]; then
  echo "  SUPABASE_DB_URL=postgresql://ai_analyst_copilot:YOUR_PASSWORD@127.0.0.1:${LOCAL_PORT}/postgres?sslmode=require"
else
  echo "  SUPABASE_DB_URL=postgresql://ai_analyst_copilot:YOUR_PASSWORD@127.0.0.1:${LOCAL_PORT}/postgres?sslmode=require"
fi
echo
echo "Press Ctrl+C to close the tunnel."
echo

exec ssh "${SSH_OPTS[@]}" -N -L "${LOCAL_PORT}:${DB_HOST}:${REMOTE_PORT}" "${TUNNEL_USER}@${TUNNEL_HOST}"