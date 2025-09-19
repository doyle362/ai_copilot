-- Create staging table for demo transactions (idempotent)
CREATE TABLE IF NOT EXISTS public.stg_transactions (
    txn_id text PRIMARY KEY,
    ts timestamptz NOT NULL,
    location_id uuid,
    zone_id text NOT NULL,
    duration_min int NOT NULL CHECK (duration_min > 0),
    amount_usd numeric(10,2) NOT NULL CHECK (amount_usd >= 0)
);

-- Create index for efficient querying by zone and time
CREATE INDEX IF NOT EXISTS idx_stg_txn_zone_ts ON public.stg_transactions(zone_id, ts);

-- Grant permissions for the analyst role (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_analyst_copilot') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.stg_transactions TO ai_analyst_copilot;
    END IF;
END $$;