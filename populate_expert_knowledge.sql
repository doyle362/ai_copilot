-- Comprehensive Parking Expert Knowledge Population
-- Based on "AI-Powered Parking Data Analysis: Key Insights and Recommendations" report

-- First run the schema creation, then populate with expert knowledge

-- PART 1: Enhanced KPI Definitions with Expert Context
INSERT INTO parking_kpis (kpi_name, kpi_category, calculation_formula, interpretation_rules, context_triggers, industry_benchmarks, recommended_actions, related_kpis, decision_triggers, target_ranges) VALUES

-- Revenue per Available Space Hour (RevPASH) - Central metric
(
    'Revenue per Available Space Hour (RevPASH)',
    'revenue',
    'Total Parking Revenue ÷ (Total Spaces × Operating Hours)',
    '{
        "excellent": {"min": 2.50, "meaning": "Strong revenue performance, well-optimized pricing"},
        "good": {"min": 1.50, "max": 2.49, "meaning": "Solid revenue generation with room for improvement"},
        "concerning": {"min": 0.75, "max": 1.49, "meaning": "Revenue optimization needed, pricing or occupancy issues"},
        "critical": {"max": 0.74, "meaning": "Poor revenue performance, immediate intervention required"}
    }',
    ARRAY['revpash', 'revenue', 'space-hour', 'yield', 'performance'],
    '{
        "downtown": {"target": "$1.80-2.80/hour", "premium": "$3.00+/hour"},
        "airport": {"target": "$2.50-4.00/hour", "premium": "$4.50+/hour"},
        "retail": {"target": "$1.00-2.00/hour", "peak": "$2.50+/hour"}
    }',
    '{
        "below_075": ["Immediate pricing review", "Analyze demand patterns", "Check competitive landscape"],
        "075_to_150": ["Implement dynamic pricing", "Extend operating hours", "Improve payment convenience"],
        "above_250": ["Monitor for demand ceiling", "Consider capacity expansion", "Optimize time-based rates"]
    }',
    ARRAY['Occupancy Efficiency Ratio', 'Average Transaction Value', 'Turnover Rate'],
    '{
        "price_increase_trigger": 2.00,
        "price_decrease_consideration": 1.00,
        "capacity_analysis_trigger": 3.00
    }',
    '{
        "downtown": {"optimal": "2.00-2.80", "minimum": "1.50"},
        "suburban": {"optimal": "1.00-1.80", "minimum": "0.75"},
        "event_driven": {"peak": "3.00-5.00", "base": "1.50-2.50"}
    }'
),

-- Enhanced Occupancy Efficiency with 85% rule integration
(
    'Occupancy Efficiency Ratio',
    'efficiency',
    '(Average Daily Occupancy ÷ Theoretical Maximum Occupancy) × 100',
    '{
        "excellent": {"min": 85, "max": 90, "meaning": "Optimal utilization - the 85% rule sweet spot"},
        "good": {"min": 70, "max": 84, "meaning": "Healthy utilization with growth opportunity"},
        "concerning": {"min": 50, "max": 69, "meaning": "Underutilization, revenue optimization needed"},
        "critical": {"min": 0, "max": 49, "meaning": "Significant underperformance, immediate action required"},
        "overcapacity": {"min": 91, "max": 100, "meaning": "Beyond effective capacity, customer experience issues"}
    }',
    ARRAY['occupancy', 'efficiency', 'utilization', '85%', 'capacity'],
    '{
        "downtown": {"target": "80-85%", "peak_acceptable": "85-90%"},
        "airport": {"target": "85-90%", "peak_acceptable": "90-95%"},
        "retail": {"target": "70-80%", "peak_acceptable": "80-85%"}
    }',
    '{
        "below_50": ["Analyze pricing strategy", "Review marketing efforts", "Assess accessibility"],
        "50_to_70": ["Consider dynamic pricing", "Optimize time-based rates", "Improve signage"],
        "above_90": ["Increase rates immediately", "Monitor customer satisfaction", "Plan capacity expansion"],
        "above_95": ["Emergency rate increase", "Implement waitlist system", "Activate overflow planning"]
    }',
    ARRAY['Revenue Per Space Hour', 'Turnover Rate', 'Peak Hour Analysis'],
    '{
        "rate_increase_trigger": 90,
        "rate_decrease_consideration": 50,
        "capacity_constraint_alert": 95
    }',
    '{
        "all_markets": {"target": "80-85%", "maximum_sustainable": "90%"}
    }'
),

-- Turnover Rate with industry benchmarks
(
    'Turnover Rate',
    'utilization',
    'Total Parking Sessions ÷ Number of Spaces (per day)',
    '{
        "excellent": {"min": 4, "meaning": "High space efficiency, good revenue generation"},
        "good": {"min": 3, "max": 3.9, "meaning": "Solid turnover, spaces being shared effectively"},
        "concerning": {"min": 1.5, "max": 2.9, "meaning": "Low turnover, possible long-term parker dominance"},
        "critical": {"max": 1.4, "meaning": "Very low turnover, revenue opportunity missed"}
    }',
    ARRAY['turnover', 'sessions', 'utilization', 'sharing'],
    '{
        "garage": {"target": "3-5 sessions/day", "excellent": "4+ sessions/day"},
        "street": {"target": "2-4 sessions/day", "downtown": "4-6 sessions/day"},
        "retail": {"target": "3-5 sessions/day", "peak_shopping": "5+ sessions/day"}
    }',
    '{
        "below_2": ["Implement time limits", "Review pricing structure", "Analyze permit allocation"],
        "2_to_3": ["Consider premium long-stay pricing", "Promote short-term usage"],
        "above_5": ["Monitor customer satisfaction", "Ensure adequate stay duration", "Consider capacity expansion"]
    }',
    ARRAY['Average Session Duration', 'Occupancy Efficiency Ratio', 'Revenue Per Space'],
    '{
        "time_limit_consideration": 2.0,
        "pricing_review_trigger": 1.5,
        "capacity_analysis_trigger": 5.0
    }',
    '{
        "urban_core": {"optimal": "4-6", "minimum": "3"},
        "suburban": {"optimal": "2-4", "minimum": "2"},
        "event_venues": {"peak": "6-10", "off_peak": "1-2"}
    }'
);

-- PART 2: Core Parking Principles from the Report
INSERT INTO parking_principles (principle_name, principle_type, core_concept, detailed_explanation, threshold_values, context_triggers, is_foundational, evidence_source) VALUES

(
    'Revenue per Space-Hour Optimization',
    'best_practice',
    'Maximize revenue from each space-hour of inventory',
    'Each hour a space is available represents perishable inventory. Once the hour passes, that revenue opportunity is lost forever. Focus on maximizing revenue per space-hour through optimal pricing and occupancy management.',
    '{
        "calculation": "total_revenue / (spaces × operating_hours)",
        "optimization_target": "maximize while maintaining 85% occupancy"
    }',
    ARRAY['revenue', 'space-hour', 'perishable', 'inventory', 'optimization'],
    true,
    'Canadian Parking Association - Revenue Management Best Practices'
),

(
    'Demand Elasticity Asymmetry Principle',
    'rule',
    'Price increases are more effective than price decreases for demand management',
    'Parking demand shows asymmetric elasticity: price increases reduce demand more effectively (-0.3 elasticity) than price decreases increase demand (-0.1 elasticity). This means rate reductions should be used cautiously.',
    '{
        "price_increase_elasticity": -0.3,
        "price_decrease_elasticity": -0.1,
        "implication": "10% price increase = ~3% demand reduction",
        "caution": "10% price decrease = only ~1% demand increase"
    }',
    ARRAY['elasticity', 'pricing', 'demand', 'asymmetric'],
    true,
    'Seattle Dynamic Pricing Study'
),

(
    'Peak Demand Identification Rule',
    'guideline',
    'Identify and optimize pricing for consistent peak demand periods',
    'Peak demand periods are when occupancy regularly exceeds 85-90%. These represent the highest revenue opportunities and should be prioritized for rate optimization.',
    '{
        "peak_threshold": 85,
        "action_threshold": 90,
        "monitoring_period": "2-3 weeks"
    }',
    ARRAY['peak', 'demand', 'timing', 'optimization'],
    false,
    'Industry Best Practices'
);

-- PART 3: Market Behavior Patterns
INSERT INTO market_behavior (behavior_type, market_segment, behavior_description, quantitative_data, causal_factors, context_triggers) VALUES

(
    'elasticity',
    'downtown',
    'Urban core parking shows moderate price sensitivity with asymmetric response',
    '{
        "price_increase_response": -0.3,
        "price_decrease_response": -0.1,
        "optimal_increment": "$0.25",
        "testing_period": "2-3 weeks",
        "customer_tolerance": "moderate"
    }',
    ARRAY['Limited alternatives', 'Business necessity', 'Time constraints'],
    ARRAY['downtown', 'urban', 'pricing', 'elasticity']
),

(
    'anomaly_pattern',
    'general',
    'Third Wednesday Phenomenon - recurring anomalous demand spikes',
    '{
        "frequency": "every_third_wednesday",
        "magnitude": "15-30% increase",
        "duration": "4-8 hours",
        "detection_method": "calendar_overlay_analysis"
    }',
    ARRAY['Monthly events', 'Food truck rallies', 'Community gatherings', 'Scheduled activities'],
    ARRAY['third', 'wednesday', 'anomaly', 'spike', 'event']
),

(
    'seasonality',
    'coastal',
    'Tourist destination seasonal demand variation',
    '{
        "summer_increase": "30-40%",
        "winter_decrease": "15-20%",
        "peak_months": ["June", "July", "August"],
        "shoulder_months": ["May", "September"],
        "planning_horizon": "quarterly"
    }',
    ARRAY['Tourism patterns', 'Weather dependency', 'School schedules', 'Event calendars'],
    ARRAY['seasonal', 'tourist', 'coastal', 'summer', 'winter']
);

-- PART 4: Decision Frameworks for Expert-Level Analysis
INSERT INTO decision_frameworks (framework_name, decision_type, trigger_conditions, decision_matrix, expected_outcomes, context_triggers) VALUES

(
    'Occupancy-Based Dynamic Pricing',
    'pricing',
    '{
        "high_occupancy": ">90% for 2+ weeks",
        "target_range": "80-90%",
        "low_occupancy": "<50% consistently"
    }',
    '{
        "above_90": {
            "action": "increase_price",
            "increment": "$0.25-0.50",
            "timeline": "immediate",
            "monitoring": "weekly"
        },
        "below_50": {
            "action": "comprehensive_analysis",
            "consider": ["pricing", "marketing", "accessibility", "competition"],
            "caution": "price_cuts_have_limited_impact"
        },
        "target_range": {
            "action": "maintain_and_optimize",
            "focus": "fine_tuning_and_monitoring"
        }
    }',
    '{
        "revenue_increase": "10-15%",
        "occupancy_optimization": "maintain 85%",
        "customer_satisfaction": "improved availability"
    }',
    ARRAY['occupancy', 'pricing', 'dynamic', '85%', 'optimization']
),

(
    'Revenue Optimization Analysis',
    'comprehensive',
    '{
        "revpash_below_target": "<$1.50/hour",
        "occupancy_patterns": "identified",
        "competitive_context": "analyzed"
    }',
    '{
        "low_revenue_high_occupancy": {
            "diagnosis": "underpriced",
            "action": "price_increase",
            "expected": "maintain_volume_increase_yield"
        },
        "low_revenue_low_occupancy": {
            "diagnosis": "market_issue",
            "action": "comprehensive_strategy",
            "consider": ["accessibility", "marketing", "competition", "pricing"]
        },
        "high_revenue_low_occupancy": {
            "diagnosis": "price_too_high",
            "action": "careful_price_reduction",
            "caution": "monitor_volume_response"
        }
    }',
    '{
        "primary": "maximize_revpash",
        "secondary": "maintain_85%_occupancy",
        "tertiary": "customer_satisfaction"
    }',
    ARRAY['revenue', 'optimization', 'revpash', 'comprehensive']
);

-- PART 5: Operational Tactics from Expert Report
INSERT INTO operational_tactics (tactic_name, tactic_category, situation_criteria, implementation_details, expected_impact, context_triggers) VALUES

(
    'Peak Hour Rate Surge',
    'pricing',
    '{
        "occupancy": ">90% consistently",
        "peak_pattern": "predictable",
        "customer_complaints": "difficulty_finding_spots"
    }',
    'Increase rates by $0.25-0.50 during identified peak periods. Implement gradually and monitor occupancy response. Adjust after 2-3 weeks based on data.',
    '{
        "occupancy_reduction": "90% to ~85%",
        "revenue_increase": "10-15%",
        "customer_experience": "improved availability"
    }',
    ARRAY['peak', 'surge', 'pricing', 'overcrowding']
),

(
    'Off-Peak Activation Strategy',
    'marketing',
    '{
        "occupancy": "<50% during identifiable periods",
        "revenue_opportunity": "measurable",
        "competition": "analyzed"
    }',
    'Implement targeted promotions: early bird discounts, flat evening rates, business partnerships. Focus on filling empty space-hours without cannibalizing peak revenue.',
    '{
        "occupancy_increase": "moderate but valuable",
        "revenue_impact": "positive if volume increases",
        "market_positioning": "improved utilization"
    }',
    ARRAY['off-peak', 'promotion', 'underutilized', 'activation']
),

(
    'Permit Portfolio Optimization',
    'capacity',
    '{
        "permit_utilization": "measured <70%",
        "transient_demand": "strong",
        "revenue_comparison": "unfavorable_to_permits"
    }',
    'Analyze permit holder actual usage patterns. Gradually reduce permit allocation through attrition if transient demand is strong and yields higher RevPASH.',
    '{
        "revenue_per_space": "increase 15-25%",
        "flexibility": "improved",
        "risk": "permit_holder_satisfaction"
    }',
    ARRAY['permit', 'allocation', 'optimization', 'yield']
),

(
    'Operating Hours Extension',
    'operations',
    '{
        "demand_beyond_hours": "demonstrated >60% occupancy",
        "enforcement_feasible": "yes",
        "community_acceptance": "likely"
    }',
    'Extend paid parking hours when data shows sustained demand beyond current operating hours. Start with 1-2 hour extensions and monitor impact.',
    '{
        "revenue_increase": "direct from additional hours",
        "occupancy_management": "improved",
        "enforcement_cost": "consider vs revenue"
    }',
    ARRAY['hours', 'extension', 'demand', 'evening']
);

-- PART 6: Enhanced Industry Knowledge with Report Insights
INSERT INTO industry_knowledge (knowledge_type, category, industry_vertical, title, content, context_triggers, confidence_level, quantitative_benchmarks) VALUES

(
    'benchmark',
    'occupancy',
    'urban',
    'The 85% Occupancy Rule - Industry Gold Standard',
    'The 85% occupancy target is widely accepted across the parking industry as the optimal balance point. At this level, most spaces are utilized but enough remain available to prevent customer frustration and "cruising" for parking. Beyond 85%, customer experience degrades significantly.',
    ARRAY['85%', 'occupancy', 'target', 'optimal', 'benchmark'],
    0.95,
    '{
        "target": 85,
        "acceptable_range": "80-90%",
        "customer_experience_threshold": 90,
        "capacity_constraint": 95
    }'
),

(
    'best_practice',
    'pricing',
    'general',
    'Dynamic Pricing Implementation Guidelines',
    'Successful dynamic pricing requires gradual implementation with $0.25 increments, 2-3 week monitoring periods, and clear performance targets. Price increases are more effective than decreases due to demand inelasticity.',
    ARRAY['dynamic', 'pricing', 'implementation', 'guidelines'],
    0.90,
    '{
        "increment_size": 0.25,
        "monitoring_period_weeks": "2-3",
        "increase_elasticity": -0.3,
        "decrease_elasticity": -0.1
    }'
),

(
    'benchmark',
    'revenue',
    'downtown',
    'Downtown RevPASH Performance Standards',
    'Downtown parking facilities should target $1.80-2.80 per space-hour with premium locations achieving $3.00+. Performance below $1.50 indicates optimization opportunities.',
    ARRAY['downtown', 'revpash', 'revenue', 'benchmark'],
    0.85,
    '{
        "target_range": "1.80-2.80",
        "premium_threshold": 3.00,
        "optimization_trigger": 1.50,
        "excellent_performance": 2.50
    }'
);

-- Create comprehensive view for AI system integration
CREATE VIEW parking_expert_knowledge AS
SELECT
    'kpi' as knowledge_type,
    kpi_name as title,
    kpi_category as category,
    calculation_formula as content,
    context_triggers,
    COALESCE(confidence_level, 0.9) as confidence,
    interpretation_rules as metadata
FROM parking_kpis
UNION ALL
SELECT
    'principle' as knowledge_type,
    principle_name as title,
    principle_type as category,
    detailed_explanation as content,
    context_triggers,
    COALESCE(confidence_level, 0.9) as confidence,
    threshold_values as metadata
FROM parking_principles
UNION ALL
SELECT
    'framework' as knowledge_type,
    framework_name as title,
    decision_type as category,
    CONCAT('Trigger conditions: ', trigger_conditions::text) as content,
    context_triggers,
    0.85 as confidence,
    decision_matrix as metadata
FROM decision_frameworks
UNION ALL
SELECT
    'tactic' as knowledge_type,
    tactic_name as title,
    tactic_category as category,
    implementation_details as content,
    context_triggers,
    0.8 as confidence,
    expected_impact as metadata
FROM operational_tactics;