-- Level Analyst: Set ai_analyst_copilot role password (updated)
-- Purpose: Create or update the ai_analyst_copilot role with a secure password
-- Run this first, before any migration or grant scripts

DO $$
BEGIN
    -- Check if role exists
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_analyst_copilot') THEN
        -- Role exists, update password
        ALTER ROLE ai_analyst_copilot WITH PASSWORD 'I#K&rzsO*cq^_P27HnkbZh#DWomK9o=K';
        RAISE NOTICE 'Updated password for existing role ai_analyst_copilot';
    ELSE
        -- Role doesn't exist, create it
        CREATE ROLE ai_analyst_copilot WITH LOGIN PASSWORD 'I#K&rzsO*cq^_P27HnkbZh#DWomK9o=K';
        RAISE NOTICE 'Created new role ai_analyst_copilot with password';
    END IF;
END
$$;