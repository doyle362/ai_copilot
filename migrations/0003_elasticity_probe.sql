-- Migration 0003: Elasticity Probe System
-- Add tables for pricing experiments and elasticity testing

-- Pricing experiments table
CREATE TABLE IF NOT EXISTS pricing_experiments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id text NOT NULL,
    location_id uuid,
    daypart text NOT NULL CHECK (daypart IN ('morning', 'evening')),
    dow int NOT NULL CHECK (dow BETWEEN 0 AND 6),
    deltas numeric[] NOT NULL,
    guardrails_snapshot jsonb NOT NULL,
    horizon_days int NOT NULL DEFAULT 14,
    status text NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'running', 'complete', 'aborted')),
    started_at timestamptz,
    ends_at timestamptz,
    created_by uuid,
    created_at timestamptz DEFAULT now()
);

-- Experiment arms table
CREATE TABLE IF NOT EXISTS pricing_experiment_arms (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id uuid NOT NULL REFERENCES pricing_experiments(id) ON DELETE CASCADE,
    delta numeric NOT NULL,
    proposal jsonb NOT NULL,
    control boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'applied', 'errored', 'reverted')),
    applied_change_id uuid,
    created_at timestamptz DEFAULT now()
);

-- Experiment results table
CREATE TABLE IF NOT EXISTS pricing_experiment_results (
    experiment_id uuid NOT NULL REFERENCES pricing_experiments(id) ON DELETE CASCADE,
    arm_id uuid NOT NULL REFERENCES pricing_experiment_arms(id) ON DELETE CASCADE,
    metric_window daterange,
    rev_psh numeric,
    occupancy numeric,
    lift_rev_psh numeric,
    lift_occupancy numeric,
    method text DEFAULT 'simple',
    computed_at timestamptz DEFAULT now(),
    PRIMARY KEY (experiment_id, arm_id, metric_window)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pricing_experiments_zone_created
    ON pricing_experiments(zone_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pricing_experiment_arms_experiment
    ON pricing_experiment_arms(experiment_id);

CREATE INDEX IF NOT EXISTS idx_pricing_experiment_results_experiment
    ON pricing_experiment_results(experiment_id);

-- Enable Row Level Security
ALTER TABLE pricing_experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_experiment_arms ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_experiment_results ENABLE ROW LEVEL SECURITY;

-- RLS Policies for zone-scoped access

-- Pricing experiments: readable/writable if zone_id is in jwt.claims.zone_ids
CREATE POLICY pricing_experiments_select_policy ON pricing_experiments
    FOR SELECT USING (
        zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
    );

CREATE POLICY pricing_experiments_insert_policy ON pricing_experiments
    FOR INSERT WITH CHECK (
        zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
    );

CREATE POLICY pricing_experiments_update_policy ON pricing_experiments
    FOR UPDATE USING (
        zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
    );

-- Experiment arms: accessible if parent experiment's zone is accessible
CREATE POLICY pricing_experiment_arms_select_policy ON pricing_experiment_arms
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM pricing_experiments e
            WHERE e.id = experiment_id
            AND e.zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
        )
    );

CREATE POLICY pricing_experiment_arms_insert_policy ON pricing_experiment_arms
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM pricing_experiments e
            WHERE e.id = experiment_id
            AND e.zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
        )
    );

CREATE POLICY pricing_experiment_arms_update_policy ON pricing_experiment_arms
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM pricing_experiments e
            WHERE e.id = experiment_id
            AND e.zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
        )
    );

-- Experiment results: accessible if parent experiment's zone is accessible
CREATE POLICY pricing_experiment_results_select_policy ON pricing_experiment_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM pricing_experiments e
            WHERE e.id = experiment_id
            AND e.zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
        )
    );

CREATE POLICY pricing_experiment_results_insert_policy ON pricing_experiment_results
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM pricing_experiments e
            WHERE e.id = experiment_id
            AND e.zone_id = ANY(string_to_array(current_setting('request.jwt.claims', true)::json->>'zone_ids', ','))
        )
    );

-- Grant permissions to analyst role
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_analyst_copilot') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_experiments TO ai_analyst_copilot;
        GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_experiment_arms TO ai_analyst_copilot;
        GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_experiment_results TO ai_analyst_copilot;
    END IF;
END $$;