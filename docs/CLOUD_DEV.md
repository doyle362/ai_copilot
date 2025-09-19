# Cloud Dev (Codespaces)

If local egress blocks Postgres ports, use GitHub Codespaces:

1) Push this repo to GitHub.
2) Click "Code" → "Create codespace on main".
3) In the Codespace terminal:
   - Create `.env` with your SUPABASE_DB_URL (pooler recommended):
     postgresql://ai_analyst_copilot:YOUR_PASSWORD@db.xzokblkebghmqargqgjb.supabase.co:6543/postgres?sslmode=require
   - Start the API:
     uvicorn analyst.main:app --host 0.0.0.0 --port 8080 --reload
4) Visit the forwarded port. Egress from Codespaces is open, so DB should connect.

Tips:
- If your corporate SSO blocks Codespaces, a small VM (e.g., Fly.io, Render, EC2) works too.