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