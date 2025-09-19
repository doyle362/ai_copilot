-- Industry Knowledge Table Structure
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

-- Example industry knowledge entries
INSERT INTO industry_knowledge (knowledge_type, category, industry_vertical, title, content, context_triggers) VALUES
(
    'benchmark',
    'occupancy',
    'downtown',
    'Downtown Occupancy Standards',
    'Typical downtown parking occupancy rates range from 65-85% during peak hours. Rates above 90% indicate high demand and pricing optimization opportunities. Rates below 50% suggest underutilization.',
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
    'regulation',
    'pricing',
    'airport',
    'Airport Parking Regulations',
    'Airport parking rates are often subject to regulatory approval and must demonstrate public benefit. Rate increases above 15% annually may require public hearings in some jurisdictions.',
    ARRAY['airport', 'regulation', 'rate', 'increase', 'approval']
),
(
    'seasonal_pattern',
    'demand',
    'retail',
    'Retail Seasonal Patterns',
    'Retail parking demand typically peaks November-December (holiday shopping) and shows 30-40% increases. Summer months may see 15-20% decreases except in tourist areas.',
    ARRAY['seasonal', 'retail', 'holiday', 'shopping', 'demand']
);