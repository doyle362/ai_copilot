-- Enhanced Parking Expert Knowledge System
-- Based on comprehensive industry analysis

-- Add new tables to complement existing KPI system

-- Core parking principles and rules
CREATE TABLE parking_principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principle_name TEXT NOT NULL,
    principle_type TEXT NOT NULL, -- 'rule', 'threshold', 'guideline', 'best_practice'
    core_concept TEXT NOT NULL,
    detailed_explanation TEXT,
    mathematical_formula TEXT,
    threshold_values JSONB, -- Key thresholds like 85% occupancy rule
    evidence_source TEXT,
    applicability_conditions TEXT[],
    context_triggers TEXT[],
    confidence_level NUMERIC DEFAULT 0.9,
    is_foundational BOOLEAN DEFAULT false, -- Core principles like 85% rule
    created_at TIMESTAMP DEFAULT NOW()
);

-- Strategic decision frameworks
CREATE TABLE decision_frameworks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    framework_name TEXT NOT NULL,
    decision_type TEXT NOT NULL, -- 'pricing', 'capacity', 'operations', 'marketing'
    trigger_conditions JSONB, -- When to apply this framework
    decision_matrix JSONB, -- If-then logic for recommendations
    expected_outcomes JSONB, -- What results to expect
    risk_factors TEXT[],
    implementation_steps TEXT[],
    success_metrics TEXT[],
    context_triggers TEXT[],
    related_principles TEXT[], -- References to parking_principles
    created_at TIMESTAMP DEFAULT NOW()
);

-- Demand elasticity and market behavior data
CREATE TABLE market_behavior (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    behavior_type TEXT NOT NULL, -- 'elasticity', 'seasonality', 'anomaly_pattern'
    market_segment TEXT, -- 'downtown', 'airport', 'retail', 'residential'
    behavior_description TEXT NOT NULL,
    quantitative_data JSONB, -- Elasticity coefficients, percentage changes, etc.
    causal_factors TEXT[],
    detection_criteria JSONB,
    business_implications TEXT[],
    recommended_responses TEXT[],
    context_triggers TEXT[],
    evidence_strength NUMERIC DEFAULT 0.8,
    geographic_scope TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Operational tactics and interventions
CREATE TABLE operational_tactics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tactic_name TEXT NOT NULL,
    tactic_category TEXT NOT NULL, -- 'pricing', 'enforcement', 'marketing', 'capacity'
    situation_criteria JSONB, -- When to use this tactic
    implementation_details TEXT,
    expected_impact JSONB, -- Revenue, occupancy, customer satisfaction effects
    risk_level TEXT, -- 'low', 'medium', 'high'
    time_to_implement TEXT,
    cost_considerations TEXT,
    success_indicators TEXT[],
    alternative_tactics TEXT[],
    context_triggers TEXT[],
    industry_examples TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enhanced industry knowledge with more granular context
ALTER TABLE industry_knowledge ADD COLUMN market_conditions TEXT[];
ALTER TABLE industry_knowledge ADD COLUMN quantitative_benchmarks JSONB;
ALTER TABLE industry_knowledge ADD COLUMN implementation_difficulty TEXT;
ALTER TABLE industry_knowledge ADD COLUMN success_rate_data JSONB;

-- Enhanced KPI table with more detailed interpretation
ALTER TABLE parking_kpis ADD COLUMN decision_triggers JSONB; -- What values trigger specific actions
ALTER TABLE parking_kpis ADD COLUMN elasticity_data JSONB; -- How this KPI responds to changes
ALTER TABLE parking_kpis ADD COLUMN target_ranges JSONB; -- Optimal ranges by market type

-- Insert foundational parking principles
INSERT INTO parking_principles (principle_name, principle_type, core_concept, detailed_explanation, threshold_values, context_triggers, is_foundational) VALUES
(
    '85% Occupancy Rule',
    'rule',
    'Optimal parking occupancy target of approximately 85%',
    'Industry-standard target where most spaces are utilized but enough remain available for customer convenience. Beyond 85%, drivers struggle to find spots leading to congestion and frustration. Below 85% indicates potential for revenue optimization.',
    '{
        "target": 85,
        "acceptable_range": {"min": 80, "max": 90},
        "action_thresholds": {
            "price_increase": 90,
            "price_decrease_consideration": 50,
            "capacity_constraint": 95
        }
    }',
    ARRAY['occupancy', 'utilization', 'capacity', 'target', 'optimal'],
    true
),
(
    'Demand Elasticity Asymmetry',
    'guideline',
    'Parking demand responds differently to price increases vs decreases',
    'Price increases reduce demand more effectively (-0.3 elasticity) than price decreases increase demand (-0.1 elasticity). This means rate reductions should be used cautiously as they may reduce revenue without proportional volume gains.',
    '{
        "price_increase_elasticity": -0.3,
        "price_decrease_elasticity": -0.1,
        "implication": "Increases more effective than decreases"
    }',
    ARRAY['pricing', 'elasticity', 'demand', 'revenue'],
    true
);

-- Insert market behavior patterns
INSERT INTO market_behavior (behavior_type, behavior_description, quantitative_data, context_triggers) VALUES
(
    'elasticity',
    'Downtown parking price elasticity patterns',
    '{
        "price_increase_response": -0.3,
        "price_decrease_response": -0.1,
        "optimal_increment": 0.25,
        "testing_period": "2-3 weeks"
    }',
    ARRAY['downtown', 'pricing', 'elasticity', 'urban']
),
(
    'seasonality',
    'Tourist area seasonal demand variation',
    '{
        "summer_peak_increase": "30-40%",
        "winter_decrease": "15-20%",
        "peak_months": ["June", "July", "August"],
        "planning_horizon": "quarterly"
    }',
    ARRAY['seasonal', 'tourism', 'coastal', 'variation']
);

-- Insert decision frameworks
INSERT INTO decision_frameworks (framework_name, decision_type, trigger_conditions, decision_matrix, context_triggers) VALUES
(
    'Occupancy-Based Pricing Framework',
    'pricing',
    '{
        "high_occupancy": ">90%",
        "target_occupancy": "80-90%",
        "low_occupancy": "<50%"
    }',
    '{
        "high_occupancy": {
            "action": "increase_price",
            "increment": "$0.25-0.50",
            "expected_outcome": "reduce to 85% occupancy, increase revenue"
        },
        "low_occupancy": {
            "action": "investigate_causes",
            "alternatives": ["marketing", "rate_reduction", "policy_changes"],
            "caution": "rate_decreases_have_limited_impact"
        }
    }',
    ARRAY['pricing', 'occupancy', 'revenue', 'optimization']
);

-- Insert operational tactics
INSERT INTO operational_tactics (tactic_name, tactic_category, situation_criteria, implementation_details, expected_impact, context_triggers) VALUES
(
    'Dynamic Peak Hour Pricing',
    'pricing',
    '{
        "consistent_high_occupancy": ">90%",
        "time_pattern": "predictable_peaks",
        "customer_complaints": "difficulty_finding_spots"
    }',
    'Increase hourly rates by $0.25-0.50 during identified peak periods. Monitor occupancy response over 2-3 weeks and adjust accordingly.',
    '{
        "occupancy_change": "reduce to 85%",
        "revenue_increase": "10-15%",
        "customer_satisfaction": "improved availability"
    }',
    ARRAY['peak', 'pricing', 'dynamic', 'revenue']
),
(
    'Off-Peak Promotional Strategy',
    'marketing',
    '{
        "low_occupancy": "<50%",
        "underutilized_periods": "evenings_weekends",
        "nearby_competition": "available"
    }',
    'Implement targeted promotions for slow periods: early bird discounts, flat-rate evening parking, partnership with local businesses.',
    '{
        "occupancy_increase": "moderate",
        "revenue_impact": "positive_if_volume_increases",
        "market_positioning": "improved"
    }',
    ARRAY['promotion', 'marketing', 'underutilized', 'evening']
);

-- Create indexes for efficient retrieval
CREATE INDEX idx_parking_principles_triggers ON parking_principles USING GIN(context_triggers);
CREATE INDEX idx_parking_principles_foundational ON parking_principles(is_foundational);
CREATE INDEX idx_decision_frameworks_type ON decision_frameworks(decision_type);
CREATE INDEX idx_decision_frameworks_triggers ON decision_frameworks USING GIN(context_triggers);
CREATE INDEX idx_market_behavior_type ON market_behavior(behavior_type);
CREATE INDEX idx_market_behavior_triggers ON market_behavior USING GIN(context_triggers);
CREATE INDEX idx_operational_tactics_category ON operational_tactics(tactic_category);
CREATE INDEX idx_operational_tactics_triggers ON operational_tactics USING GIN(context_triggers);