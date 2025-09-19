-- Migration: Add parking KPI and analytical patterns knowledge system
-- This adds industry-specific knowledge tables to support intelligent analysis

-- Parking Industry KPI & Metrics Knowledge System
CREATE TABLE parking_kpis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kpi_name TEXT NOT NULL,
    kpi_category TEXT NOT NULL, -- 'efficiency', 'revenue', 'utilization', 'performance'
    calculation_formula TEXT,
    interpretation_rules JSONB, -- Thresholds and what they mean
    context_triggers TEXT[],     -- When to surface this KPI
    industry_benchmarks JSONB,  -- Industry standard ranges
    recommended_actions JSONB,  -- What to do at different thresholds
    related_kpis TEXT[],        -- Other KPIs to consider together
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE analytical_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL, -- 'seasonal', 'behavioral', 'revenue', 'operational'
    description TEXT NOT NULL,
    detection_criteria JSONB,   -- How to identify this pattern
    significance_level TEXT,     -- 'critical', 'important', 'informational'
    typical_causes TEXT[],       -- What usually causes this pattern
    recommended_analysis TEXT[], -- Follow-up analyses to perform
    example_insights TEXT[],     -- Example insights to generate
    context_triggers TEXT[],     -- Keywords that should surface this
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- KPI Analysis Templates
CREATE TABLE kpi_analysis_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name TEXT NOT NULL,
    kpi_combination TEXT[], -- Which KPIs to analyze together
    analysis_type TEXT,     -- 'correlation', 'trend', 'benchmark', 'optimization'
    insight_template TEXT,  -- Template for generating insights
    action_recommendations JSONB,
    context_triggers TEXT[]
);

-- Industry Knowledge Table
CREATE TABLE industry_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_type TEXT NOT NULL, -- 'benchmark', 'best_practice', 'regulation', 'seasonal_pattern'
    category TEXT NOT NULL,       -- 'pricing', 'occupancy', 'revenue', 'operations'
    industry_vertical TEXT,       -- 'airport', 'downtown', 'residential', 'retail', 'hospital'
    geographic_region TEXT,       -- 'us_west_coast', 'europe', 'urban_core', etc.
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    context_triggers TEXT[],      -- Keywords that should trigger this knowledge
    confidence_level NUMERIC,    -- How confident we are in this knowledge (0.0-1.0)
    source TEXT,                 -- Where this knowledge came from
    last_updated TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Example KPI definitions
INSERT INTO parking_kpis (kpi_name, kpi_category, calculation_formula, interpretation_rules, context_triggers, industry_benchmarks, recommended_actions, related_kpis) VALUES
(
    'Occupancy Efficiency Ratio',
    'efficiency',
    '(Average Daily Occupancy / Theoretical Maximum Occupancy) * 100',
    '{
        "excellent": {"min": 85, "max": 95, "meaning": "Optimal utilization without oversaturation"},
        "good": {"min": 70, "max": 84, "meaning": "Healthy utilization with room for growth"},
        "concerning": {"min": 50, "max": 69, "meaning": "Underutilization, revenue optimization needed"},
        "critical": {"min": 0, "max": 49, "meaning": "Significant underperformance, immediate action required"}
    }',
    ARRAY['occupancy', 'efficiency', 'utilization', 'capacity'],
    '{
        "downtown": {"target": "75-85%", "peak": "85-95%"},
        "airport": {"target": "80-90%", "peak": "90-98%"},
        "retail": {"target": "65-80%", "peak": "80-95%"}
    }',
    '{
        "below_50": ["Analyze pricing strategy", "Review marketing efforts", "Assess location accessibility"],
        "50_to_70": ["Consider dynamic pricing", "Optimize time-based rates", "Analyze competitor pricing"],
        "above_95": ["Consider rate increases", "Monitor customer satisfaction", "Plan capacity expansion"]
    }',
    ARRAY['Revenue Per Space', 'Average Session Duration', 'Peak Hour Utilization']
),
(
    'Revenue Per Available Space Hour (RevPASH)',
    'revenue',
    'Total Revenue / (Total Spaces * Hours in Period)',
    '{
        "excellent": {"min": 2.50, "meaning": "Strong revenue performance"},
        "good": {"min": 1.50, "max": 2.49, "meaning": "Solid revenue generation"},
        "concerning": {"min": 0.75, "max": 1.49, "meaning": "Revenue optimization needed"},
        "critical": {"max": 0.74, "meaning": "Poor revenue performance"}
    }',
    ARRAY['revenue', 'RevPASH', 'performance', 'space', 'hourly'],
    '{
        "downtown": {"target": "$1.80-2.80/hour", "premium": "$3.00+/hour"},
        "airport": {"target": "$2.50-4.00/hour", "premium": "$4.50+/hour"}
    }',
    '{
        "below_075": ["Immediate pricing review", "Assess demand patterns", "Consider promotional strategies"],
        "075_to_150": ["Optimize time-based pricing", "Analyze peak/off-peak ratios", "Test rate adjustments"]
    }',
    ARRAY['Occupancy Efficiency Ratio', 'Average Transaction Value', 'Duration Premium Capture']
),
(
    'Average Session Duration',
    'utilization',
    'Total Session Minutes / Number of Sessions',
    '{
        "short_stays": {"max": 60, "meaning": "High turnover, good for short-term parking"},
        "medium_stays": {"min": 60, "max": 240, "meaning": "Balanced utilization pattern"},
        "long_stays": {"min": 240, "meaning": "Extended parking, potential premium pricing"}
    }',
    ARRAY['duration', 'session', 'turnover', 'time'],
    '{
        "downtown": {"average": "90-180 minutes", "peak_hours": "60-120 minutes"},
        "airport": {"average": "3-24 hours", "short_term": "1-4 hours"},
        "retail": {"average": "2-4 hours", "peak_shopping": "3-6 hours"}
    }',
    '{
        "very_short": ["Implement minimum charges", "Analyze pricing structure", "Consider time-based rates"],
        "very_long": ["Evaluate maximum stay policies", "Consider daily/weekly rates", "Analyze space utilization"]
    }',
    ARRAY['Occupancy Efficiency Ratio', 'Revenue Per Space', 'Turnover Rate']
);

-- Example analytical patterns
INSERT INTO analytical_patterns (pattern_name, pattern_type, description, detection_criteria, significance_level, typical_causes, recommended_analysis, example_insights, context_triggers) VALUES
(
    'Weekend Premium Opportunity',
    'revenue',
    'Weekends show different demand patterns that may support premium pricing',
    '{
        "weekend_vs_weekday_occupancy": {"threshold": 1.15, "comparison": "greater_than"},
        "weekend_session_duration": {"threshold": 1.20, "comparison": "greater_than"},
        "minimum_weekend_occupancy": {"threshold": 60, "comparison": "greater_than"}
    }',
    'important',
    ARRAY['Event-driven demand', 'Leisure vs business travel patterns', 'Reduced supply from office buildings'],
    ARRAY['Analyze weekend vs weekday pricing elasticity', 'Segment weekend demand by time slots', 'Compare weekend revenue per space'],
    ARRAY[
        'Weekend demand is 20% higher with 25% longer sessions - premium pricing opportunity identified',
        'Saturday afternoons show 40% higher occupancy than weekdays - consider implementing weekend rates',
        'Weekend visitors stay 30% longer on average - duration-based pricing could capture additional value'
    ],
    ARRAY['weekend', 'premium', 'pricing', 'saturday', 'sunday', 'demand']
),
(
    'Capacity Constraint Alert',
    'operational',
    'Consistent high occupancy periods that may indicate capacity constraints',
    '{
        "sustained_high_occupancy": {"threshold": 95, "duration_hours": 3, "frequency_per_week": 2},
        "peak_occupancy": {"threshold": 98, "frequency_per_month": 4},
        "waitlist_indicators": {"overflow_sessions": 5, "per_week": true}
    }',
    'critical',
    ARRAY['Market demand growth', 'Competitor capacity reduction', 'Event-driven spikes', 'Pricing below market'],
    ARRAY['Revenue impact analysis of capacity expansion', 'Alternative overflow location analysis', 'Price elasticity testing'],
    ARRAY[
        'Zone consistently hits 98% occupancy on weekday mornings - capacity expansion or premium pricing recommended',
        'Peak demand regularly exceeds capacity by 15% - immediate revenue optimization opportunity',
        'High-demand periods show revenue ceiling due to capacity - expansion ROI analysis needed'
    ],
    ARRAY['capacity', 'constraint', 'full', 'overflow', 'expansion', 'waitlist']
),
(
    'Seasonal Demand Shift',
    'seasonal',
    'Significant changes in demand patterns that indicate seasonal trends',
    '{
        "month_over_month_change": {"threshold": 20, "comparison": "greater_than"},
        "year_over_year_change": {"threshold": 15, "comparison": "greater_than"},
        "consecutive_months": {"min_months": 2, "trend_direction": "same"}
    }',
    'important',
    ARRAY['Weather patterns', 'Tourist seasons', 'Business travel cycles', 'Local event calendars'],
    ARRAY['Historical seasonal pattern analysis', 'Competitive landscape seasonal changes', 'Pricing strategy optimization'],
    ARRAY[
        'Summer demand drops 25% - seasonal pricing adjustment recommended',
        'Holiday season shows 40% increase for 6 weeks - premium pricing window identified',
        'Spring demand surge begins 2 weeks earlier than last year - pricing calendar adjustment needed'
    ],
    ARRAY['seasonal', 'summer', 'winter', 'holiday', 'tourist', 'weather', 'trend']
);

-- Example KPI analysis templates
INSERT INTO kpi_analysis_templates (template_name, kpi_combination, analysis_type, insight_template, action_recommendations, context_triggers) VALUES
(
    'Revenue Optimization Analysis',
    ARRAY['Occupancy Efficiency Ratio', 'Revenue Per Available Space Hour', 'Average Session Duration'],
    'optimization',
    'Zone {zone_id} shows {occupancy_efficiency}% occupancy with ${revpash}/hour RevPASH. {interpretation_based_on_thresholds}',
    '{
        "low_occupancy_low_revenue": ["Reduce pricing to drive volume", "Improve marketing/visibility", "Analyze competitor rates"],
        "high_occupancy_low_revenue": ["Increase pricing to capture value", "Implement time-based premiums", "Test demand elasticity"],
        "optimal_range": ["Fine-tune pricing", "Monitor competitor changes", "Prepare for seasonal adjustments"]
    }',
    ARRAY['revenue', 'optimization', 'pricing', 'performance', 'ROI']
);

-- Example industry knowledge
INSERT INTO industry_knowledge (knowledge_type, category, industry_vertical, title, content, context_triggers) VALUES
(
    'benchmark',
    'occupancy',
    'downtown',
    'Downtown Occupancy Standards',
    'Typical downtown parking occupancy rates range from 65-85% during peak hours. Rates above 90% indicate high demand and pricing optimization opportunities. Rates below 50% suggest underutilization requiring strategy review.',
    ARRAY['occupancy', 'downtown', 'benchmark', 'typical', 'standard']
),
(
    'best_practice',
    'pricing',
    NULL,
    'Dynamic Pricing Guidelines',
    'Price adjustments should typically be made in 15-25% increments to avoid demand shock. Test smaller adjustments (5-10%) first in high-sensitivity markets. Monitor for 2-3 weeks before making additional changes.',
    ARRAY['pricing', 'adjustment', 'dynamic', 'increase', 'decrease']
),
(
    'benchmark',
    'revenue',
    'airport',
    'Airport Revenue Benchmarks',
    'Airport parking typically generates $2.50-4.00 per space per hour during peak periods. Premium locations near terminals can command $4.50+ per hour. Long-term parking averages $8-15 per day.',
    ARRAY['airport', 'revenue', 'benchmark', 'terminal', 'long-term']
),
(
    'seasonal_pattern',
    'demand',
    'retail',
    'Retail Seasonal Patterns',
    'Retail parking demand typically peaks November-December (holiday shopping) with 30-40% increases. Summer months may see 15-20% decreases except in tourist areas. Back-to-school periods show moderate 10-15% increases.',
    ARRAY['seasonal', 'retail', 'holiday', 'shopping', 'demand', 'summer']
);

-- Create indexes for better query performance
CREATE INDEX idx_parking_kpis_category ON parking_kpis(kpi_category);
CREATE INDEX idx_parking_kpis_triggers ON parking_kpis USING GIN(context_triggers);
CREATE INDEX idx_analytical_patterns_type ON analytical_patterns(pattern_type);
CREATE INDEX idx_analytical_patterns_triggers ON analytical_patterns USING GIN(context_triggers);
CREATE INDEX idx_industry_knowledge_category ON industry_knowledge(category);
CREATE INDEX idx_industry_knowledge_triggers ON industry_knowledge USING GIN(context_triggers);
CREATE INDEX idx_kpi_templates_triggers ON kpi_analysis_templates USING GIN(context_triggers);