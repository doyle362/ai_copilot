-- Level Analyst: Post-migration grants for ai_analyst_copilot
-- Purpose: Apply explicit table-level permissions after migrations have created all objects
-- Run this after the application migrations have completed successfully

DO $$
DECLARE
    table_name text;
    read_write_tables text[] := ARRAY[
        'insights',
        'recommendations',
        'price_changes',
        'insight_threads',
        'thread_messages',
        'feedback_memories',
        'feedback_memory_embeddings',
        'inferred_rate_plans',
        'proposed_rate_plans'
    ];
    read_only_tables text[] := ARRAY[
        'agent_prompt_versions',
        'agent_guardrails',
        'mart_metrics_daily',
        'mart_metrics_hourly'
    ];
BEGIN
    -- Grant read-write permissions on application tables
    FOREACH table_name IN ARRAY read_write_tables
    LOOP
        IF EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = table_name AND n.nspname = 'public'
        ) THEN
            EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.%I TO ai_analyst_copilot', table_name);
            RAISE NOTICE 'Granted READ-WRITE on table: %', table_name;
        ELSE
            RAISE NOTICE 'Table not found (skipping): %', table_name;
        END IF;
    END LOOP;

    -- Grant read-only permissions on reference/analytics tables
    FOREACH table_name IN ARRAY read_only_tables
    LOOP
        IF EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = table_name AND n.nspname = 'public'
        ) THEN
            EXECUTE format('GRANT SELECT ON TABLE public.%I TO ai_analyst_copilot', table_name);
            RAISE NOTICE 'Granted READ-ONLY on table: %', table_name;
        ELSE
            RAISE NOTICE 'Table not found (skipping): %', table_name;
        END IF;
    END LOOP;

    -- Ensure permissions on all existing tables and sequences
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_analyst_copilot;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ai_analyst_copilot;

    -- Optional security hardening (commented out by default)
    -- Uncomment the next line to prevent the role from creating new objects after migration
    -- REVOKE CREATE ON SCHEMA public FROM ai_analyst_copilot;

    RAISE NOTICE 'Post-migration grants completed successfully';
END
$$;