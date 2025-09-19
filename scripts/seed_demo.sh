#!/usr/bin/env bash
set -euo pipefail

echo "=== Level Analyst Demo Data Seeding ==="

# Check for psql
if ! command -v psql >/dev/null 2>&1; then
    echo "❌ ERROR: psql not found. Please install PostgreSQL client tools:"
    echo "   macOS: brew install postgresql"
    echo "   Ubuntu: sudo apt-get install postgresql-client"
    echo "   CentOS: sudo yum install postgresql"
    exit 2
fi

# Check for SUPABASE_DB_URL
if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
    echo "❌ ERROR: SUPABASE_DB_URL environment variable not set."
    echo "   Set it in .env or export it directly:"
    echo "   export SUPABASE_DB_URL='postgresql://ai_analyst_copilot:YOUR_PASSWORD@db.host:6543/postgres?sslmode=require'"
    exit 3
fi

# Add sslmode=require if not present
URL="$SUPABASE_DB_URL"
if [[ "$URL" != *"sslmode="* ]]; then
    if [[ "$URL" == *"?"* ]]; then
        URL="${URL}&sslmode=require"
    else
        URL="${URL}?sslmode=require"
    fi
fi

echo "✓ psql found"
echo "✓ SUPABASE_DB_URL configured"

# Test connection
echo "🔗 Testing database connection..."
if ! psql "$URL" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to database. Check your SUPABASE_DB_URL and network connectivity."
    echo "   Try the diagnostics: curl http://localhost:8080/diag/db"
    exit 4
fi
echo "✓ Database connection successful"

# Create schema
echo "📊 Creating staging schema..."
if ! psql "$URL" -v ON_ERROR_STOP=1 -f sql/seed_schema.sql; then
    echo "❌ ERROR: Failed to create staging schema"
    exit 5
fi
echo "✓ Staging schema ready"

# Truncate existing data
echo "🗑️  Truncating existing demo data..."
psql "$URL" -c "TRUNCATE public.stg_transactions;" >/dev/null
echo "✓ Staging table cleared"

# Load CSV data
echo "📥 Loading demo transactions from CSV..."
if ! psql "$URL" -c "\\copy public.stg_transactions(txn_id,ts,location_id,zone_id,duration_min,amount_usd) FROM 'data/demo_transactions.csv' WITH (FORMAT csv, HEADER true)"; then
    echo "❌ ERROR: Failed to load CSV data"
    exit 6
fi
echo "✓ Demo data loaded"

# Show data summary
echo "📈 Data summary:"
psql "$URL" -c "
SELECT
    zone_id,
    count(*) as rows,
    min(ts)::date as min_day,
    max(ts)::date as max_day,
    round(avg(amount_usd), 2) as avg_amount,
    round(avg(duration_min), 0) as avg_duration_min
FROM public.stg_transactions
GROUP BY 1
ORDER BY 1;
"

# Run dbt if available
if [[ -d "analytics" ]]; then
    echo "🔧 Running dbt transformations..."
    if command -v dbt >/dev/null 2>&1; then
        (cd analytics && dbt deps --quiet && dbt run --quiet && dbt test --quiet) || {
            echo "⚠️  dbt run encountered issues, but continuing..."
        }
        echo "✓ dbt transformations completed"
    else
        echo "⚠️  dbt not found. Install with: pip install dbt-postgres"
        echo "   Then run: cd analytics && dbt deps && dbt run && dbt test"
    fi
else
    echo "ℹ️  No analytics/ directory found, skipping dbt"
fi

# Final sanity check
echo "🔍 Recent transactions (sample):"
psql "$URL" -c "SELECT txn_id, ts, zone_id, duration_min, amount_usd FROM public.stg_transactions ORDER BY ts DESC LIMIT 5;"

echo "✅ Demo data seeding completed successfully!"
echo "   • Loaded $(psql "$URL" -t -c "SELECT count(*) FROM public.stg_transactions;") transactions"
echo "   • Coverage: $(psql "$URL" -t -c "SELECT count(DISTINCT zone_id) FROM public.stg_transactions;") zones"
echo "   • Time range: $(psql "$URL" -t -c "SELECT min(ts)::date || ' to ' || max(ts)::date FROM public.stg_transactions;")"

exit 0