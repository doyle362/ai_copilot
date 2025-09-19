-- Level Analyst: Pre-migration grants for ai_analyst_copilot
-- Purpose: Grant permissions needed to run application migrations
-- Run this after setting the password, but before running app migrations

-- Grant schema-level permissions
GRANT USAGE, CREATE ON SCHEMA public TO ai_analyst_copilot;

-- Grant permissions on existing tables (if any)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_analyst_copilot;

-- Grant permissions on existing sequences (if any)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ai_analyst_copilot;

-- Set default privileges for future objects created by any role in public schema
-- This ensures ai_analyst_copilot can read tables created during migration
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ai_analyst_copilot;

-- Allow insert/update on future tables for application runtime
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT INSERT, UPDATE ON TABLES TO ai_analyst_copilot;

-- Allow sequence usage for auto-increment columns
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO ai_analyst_copilot;

-- Note: The role now has sufficient permissions to:
-- 1. Create tables, indexes, and other objects during migration
-- 2. Read from existing tables
-- 3. Automatically get appropriate permissions on newly created tables