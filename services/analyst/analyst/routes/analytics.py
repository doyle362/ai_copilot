from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from ..deps.auth import get_current_user, UserContext
from ..db import get_db, Database
from ..core.parking_expert_ai import ParkingExpertAI

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/session-counts")
async def get_session_counts(
    time_filter: Optional[str] = Query(None, description="Legacy time filter: 'friday_evening', 'weekday', 'weekend', etc."),
    zone_filter: Optional[str] = Query(None, description="Zone filter: specific zone number or 'all'"),
    day_of_week: Optional[str] = Query(None, description="Day of week: 0-6 (Sunday=0) or comma-separated list"),
    hour_start: Optional[int] = Query(None, description="Start hour (0-23)"),
    hour_end: Optional[int] = Query(None, description="End hour (0-23)"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get session counts with various filters"""

    try:
        base_query = """
            SELECT
                ht.zone,
                COUNT(*) as session_count,
                AVG(ht.paid_minutes) as avg_duration_minutes,
                SUM(CAST(ht.payment_amount AS NUMERIC)) as total_revenue,
                l.capacity,
                l.name as location_name,
                CASE
                    WHEN l.capacity > 0 THEN
                        ROUND((COUNT(*) / COUNT(DISTINCT DATE(ht.start_park_date))::NUMERIC / l.capacity) * 100, 2)
                    ELSE NULL
                END as avg_daily_occupancy_ratio,
                CASE
                    WHEN l.capacity > 0 THEN
                        ROUND((SUM(ht.paid_minutes) / (COUNT(DISTINCT DATE(ht.start_park_date)) * 1440.0 * l.capacity)) * 100, 2)
                    ELSE NULL
                END as avg_utilization_ratio
            FROM historical_transactions ht
            LEFT JOIN locations l ON ht.zone::text = l.zone_id
            WHERE ht.zone IS NOT NULL
        """

        params = []

        # Add time filters - support both legacy and dynamic filtering
        if day_of_week is not None or hour_start is not None or hour_end is not None:
            # Dynamic filtering
            if day_of_week is not None:
                if ',' in day_of_week:
                    # Multiple days
                    days = [int(d.strip()) for d in day_of_week.split(',')]
                    day_placeholders = ",".join([f"${len(params) + i + 1}" for i in range(len(days))])
                    base_query += f" AND EXTRACT(dow FROM start_park_date) IN ({day_placeholders})"
                    params.extend(days)
                else:
                    # Single day
                    base_query += f" AND EXTRACT(dow FROM start_park_date) = ${len(params) + 1}"
                    params.append(int(day_of_week))

            if hour_start is not None and hour_end is not None:
                base_query += f" AND EXTRACT(hour FROM start_park_time) BETWEEN ${len(params) + 1} AND ${len(params) + 2}"
                params.extend([hour_start, hour_end])
            elif hour_start is not None:
                base_query += f" AND EXTRACT(hour FROM start_park_time) >= ${len(params) + 1}"
                params.append(hour_start)
            elif hour_end is not None:
                base_query += f" AND EXTRACT(hour FROM start_park_time) <= ${len(params) + 1}"
                params.append(hour_end)

        elif time_filter:
            # Legacy filtering for backward compatibility
            if time_filter == "friday_evening":
                base_query += " AND EXTRACT(dow FROM start_park_date) = 5 AND EXTRACT(hour FROM start_park_time) BETWEEN 17 AND 21"
            elif time_filter == "tuesday_morning":
                base_query += " AND EXTRACT(dow FROM start_park_date) = 2 AND EXTRACT(hour FROM start_park_time) BETWEEN 6 AND 11"
            elif time_filter == "weekday":
                base_query += " AND EXTRACT(dow FROM start_park_date) BETWEEN 1 AND 5"
            elif time_filter == "weekend":
                base_query += " AND EXTRACT(dow FROM start_park_date) IN (0, 6)"
            elif time_filter == "morning_peak":
                base_query += " AND EXTRACT(hour FROM start_park_time) BETWEEN 7 AND 9"
            elif time_filter == "evening_peak":
                base_query += " AND EXTRACT(hour FROM start_park_time) BETWEEN 17 AND 19"

        # Add zone filters
        if zone_filter and zone_filter != "all":
            # Handle user zone access
            if f"z-{zone_filter}" in user.zone_ids:
                base_query += f" AND ht.zone::text = ${len(params) + 1}"
                params.append(zone_filter)
            else:
                raise HTTPException(status_code=403, detail="Access denied to zone")
        else:
            # Filter to only zones user has access to
            accessible_zones = [z.replace('z-', '') for z in user.zone_ids if z.startswith('z-')]
            if accessible_zones:
                start_idx = len(params) + 1
                placeholders = ",".join([f"${start_idx + i}" for i in range(len(accessible_zones))])
                base_query += f" AND ht.zone::text IN ({placeholders})"
                params.extend(accessible_zones)

        base_query += " GROUP BY ht.zone, l.capacity, l.name ORDER BY session_count DESC"

        results = await db.fetch(base_query, *params)

        return {
            "success": True,
            "data": {
                "sessions": [dict(row) for row in results],
                "total_sessions": sum(row['session_count'] for row in results),
                "filter_applied": time_filter or "none"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying session data: {str(e)}")


@router.get("/zone-summary")
async def get_zone_summary(
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get overall summary for all accessible zones"""

    try:
        # Get accessible zones
        accessible_zones = [z.replace('z-', '') for z in user.zone_ids if z.startswith('z-')]
        if not accessible_zones:
            return {"success": True, "data": {"zones": []}}

        placeholders = ",".join([f"${i}" for i in range(1, len(accessible_zones) + 1)])

        query = f"""
            SELECT
                ht.zone,
                COUNT(*) as total_sessions,
                COUNT(DISTINCT DATE(ht.start_park_date)) as active_days,
                AVG(ht.paid_minutes) as avg_duration_minutes,
                MIN(ht.start_park_date) as first_transaction,
                MAX(ht.start_park_date) as last_transaction,
                SUM(CAST(ht.payment_amount AS NUMERIC)) as total_revenue,
                l.capacity,
                l.name as location_name,
                CASE
                    WHEN l.capacity > 0 THEN
                        ROUND((COUNT(*) / COUNT(DISTINCT DATE(ht.start_park_date))::NUMERIC / l.capacity) * 100, 2)
                    ELSE NULL
                END as avg_daily_occupancy_ratio,
                CASE
                    WHEN l.capacity > 0 THEN
                        ROUND((SUM(ht.paid_minutes) / (COUNT(DISTINCT DATE(ht.start_park_date)) * 1440.0 * l.capacity)) * 100, 2)
                    ELSE NULL
                END as avg_utilization_ratio
            FROM historical_transactions ht
            LEFT JOIN locations l ON ht.zone::text = l.zone_id
            WHERE ht.zone::text IN ({placeholders})
            GROUP BY ht.zone, l.capacity, l.name
            ORDER BY total_sessions DESC
        """

        results = await db.fetch(query, *accessible_zones)

        return {
            "success": True,
            "data": {
                "zones": [dict(row) for row in results],
                "summary": {
                    "total_zones": len(results),
                    "total_sessions": sum(row['total_sessions'] for row in results),
                    "total_revenue": sum(float(row['total_revenue'] or 0) for row in results)
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting zone summary: {str(e)}")


@router.get("/time-patterns")
async def get_time_patterns(
    zone: Optional[str] = Query(None, description="Specific zone to analyze"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get time-based usage patterns"""

    try:
        base_query = """
            SELECT
                EXTRACT(dow FROM start_park_date) as day_of_week,
                EXTRACT(hour FROM start_park_time) as hour_of_day,
                COUNT(*) as session_count
            FROM historical_transactions
            WHERE zone IS NOT NULL
        """

        params = []

        if zone:
            if f"z-{zone}" in user.zone_ids:
                base_query += f" AND zone::text = ${len(params) + 1}"
                params.append(zone)
            else:
                raise HTTPException(status_code=403, detail="Access denied to zone")
        else:
            # Filter to accessible zones
            accessible_zones = [z.replace('z-', '') for z in user.zone_ids if z.startswith('z-')]
            if accessible_zones:
                start_idx = len(params) + 1
                placeholders = ",".join([f"${start_idx + i}" for i in range(len(accessible_zones))])
                base_query += f" AND zone::text IN ({placeholders})"
                params.extend(accessible_zones)

        base_query += """
            GROUP BY day_of_week, hour_of_day
            ORDER BY day_of_week, hour_of_day
        """

        results = await db.fetch(base_query, *params)

        # Transform data for easier consumption
        patterns = {}
        for row in results:
            dow = int(row['day_of_week'])
            hour = int(row['hour_of_day'])
            day_name = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][dow]

            if day_name not in patterns:
                patterns[day_name] = {}
            patterns[day_name][hour] = row['session_count']

        return {
            "success": True,
            "data": {
                "patterns": patterns,
                "zone_filter": zone or "all_accessible"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting time patterns: {str(e)}")


@router.get("/occupancy-analysis")
async def get_occupancy_analysis(
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get occupancy and capacity utilization analysis for all accessible zones"""

    try:
        # Get accessible zones
        accessible_zones = [z.replace('z-', '') for z in user.zone_ids if z.startswith('z-')]
        if not accessible_zones:
            return {"success": True, "data": {"zones": []}}

        placeholders = ",".join([f"${i}" for i in range(1, len(accessible_zones) + 1)])

        query = f"""
            SELECT
                ht.zone,
                l.name as location_name,
                l.capacity,
                COUNT(*) as total_sessions,
                COUNT(DISTINCT DATE(ht.start_park_date)) as active_days,
                AVG(ht.paid_minutes) as avg_duration_minutes,
                CASE
                    WHEN l.capacity > 0 THEN
                        ROUND((COUNT(*) / COUNT(DISTINCT DATE(ht.start_park_date))::NUMERIC / l.capacity) * 100, 2)
                    ELSE NULL
                END as avg_daily_occupancy_ratio,
                CASE
                    WHEN l.capacity > 0 THEN
                        ROUND((SUM(ht.paid_minutes) / (COUNT(DISTINCT DATE(ht.start_park_date)) * 1440.0 * l.capacity)) * 100, 2)
                    ELSE NULL
                END as avg_utilization_ratio,
                CASE
                    WHEN l.capacity > 0 AND COUNT(*) / COUNT(DISTINCT DATE(ht.start_park_date))::NUMERIC / l.capacity > 0.8 THEN 'high_demand'
                    WHEN l.capacity > 0 AND COUNT(*) / COUNT(DISTINCT DATE(ht.start_park_date))::NUMERIC / l.capacity < 0.3 THEN 'underutilized'
                    WHEN l.capacity > 0 THEN 'optimal'
                    ELSE 'no_capacity_data'
                END as occupancy_status
            FROM historical_transactions ht
            LEFT JOIN locations l ON ht.zone::text = l.zone_id
            WHERE ht.zone::text IN ({placeholders})
            GROUP BY ht.zone, l.capacity, l.name
            ORDER BY avg_daily_occupancy_ratio DESC NULLS LAST
        """

        results = await db.fetch(query, *accessible_zones)

        # Categorize zones by occupancy status
        categorized = {
            'high_demand': [],
            'optimal': [],
            'underutilized': [],
            'no_capacity_data': []
        }

        for row in results:
            status = row['occupancy_status']
            categorized[status].append(dict(row))

        return {
            "success": True,
            "data": {
                "zones": [dict(row) for row in results],
                "categorized": categorized,
                "summary": {
                    "total_zones": len(results),
                    "zones_with_capacity_data": len([r for r in results if r['capacity']]),
                    "high_demand_zones": len(categorized['high_demand']),
                    "underutilized_zones": len(categorized['underutilized']),
                    "optimal_zones": len(categorized['optimal'])
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting occupancy analysis: {str(e)}")


@router.get("/kpi-knowledge")
async def get_kpi_knowledge(
    context: Optional[str] = Query(None, description="Context keywords to find relevant KPIs"),
    category: Optional[str] = Query(None, description="KPI category filter"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get relevant KPI knowledge based on context keywords"""

    try:
        base_query = """
            SELECT
                kpi_name,
                kpi_category,
                calculation_formula,
                interpretation_rules,
                context_triggers,
                industry_benchmarks,
                recommended_actions,
                related_kpis
            FROM parking_kpis
            WHERE is_active = true
        """

        params = []

        # Filter by category if provided
        if category:
            base_query += f" AND kpi_category = ${len(params) + 1}"
            params.append(category)

        # Filter by context keywords if provided
        if context:
            keywords = [word.strip().lower() for word in context.split(',')]
            # Use PostgreSQL array overlap operator to find matching triggers
            for i, keyword in enumerate(keywords):
                base_query += f" AND (${len(params) + 1} = ANY(context_triggers) OR kpi_name ILIKE '%' || ${len(params) + 1} || '%')"
                params.append(keyword)

        base_query += " ORDER BY kpi_category, kpi_name"

        results = await db.fetch(base_query, *params)

        return {
            "success": True,
            "data": {
                "kpis": [dict(row) for row in results],
                "total_found": len(results),
                "context_applied": context or "none",
                "category_filter": category or "none"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving KPI knowledge: {str(e)}")


@router.get("/analytical-patterns")
async def get_analytical_patterns(
    context: Optional[str] = Query(None, description="Context keywords to find relevant patterns"),
    pattern_type: Optional[str] = Query(None, description="Pattern type filter"),
    significance: Optional[str] = Query(None, description="Significance level filter"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get relevant analytical patterns based on context"""

    try:
        base_query = """
            SELECT
                pattern_name,
                pattern_type,
                description,
                detection_criteria,
                significance_level,
                typical_causes,
                recommended_analysis,
                example_insights,
                context_triggers
            FROM analytical_patterns
            WHERE is_active = true
        """

        params = []

        # Filter by pattern type if provided
        if pattern_type:
            base_query += f" AND pattern_type = ${len(params) + 1}"
            params.append(pattern_type)

        # Filter by significance level if provided
        if significance:
            base_query += f" AND significance_level = ${len(params) + 1}"
            params.append(significance)

        # Filter by context keywords if provided
        if context:
            keywords = [word.strip().lower() for word in context.split(',')]
            for i, keyword in enumerate(keywords):
                base_query += f" AND (${len(params) + 1} = ANY(context_triggers) OR pattern_name ILIKE '%' || ${len(params) + 1} || '%' OR description ILIKE '%' || ${len(params) + 1} || '%')"
                params.append(keyword)

        base_query += " ORDER BY significance_level DESC, pattern_type, pattern_name"

        results = await db.fetch(base_query, *params)

        return {
            "success": True,
            "data": {
                "patterns": [dict(row) for row in results],
                "total_found": len(results),
                "context_applied": context or "none",
                "filters": {
                    "pattern_type": pattern_type or "none",
                    "significance": significance or "none"
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytical patterns: {str(e)}")


@router.get("/industry-knowledge")
async def get_industry_knowledge(
    context: Optional[str] = Query(None, description="Context keywords to find relevant knowledge"),
    knowledge_type: Optional[str] = Query(None, description="Knowledge type filter"),
    category: Optional[str] = Query(None, description="Knowledge category filter"),
    industry_vertical: Optional[str] = Query(None, description="Industry vertical filter"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get relevant industry knowledge based on context"""

    try:
        base_query = """
            SELECT
                knowledge_type,
                category,
                industry_vertical,
                geographic_region,
                title,
                content,
                context_triggers,
                confidence_level,
                source,
                last_updated
            FROM industry_knowledge
            WHERE is_active = true
        """

        params = []

        # Filter by knowledge type if provided
        if knowledge_type:
            base_query += f" AND knowledge_type = ${len(params) + 1}"
            params.append(knowledge_type)

        # Filter by category if provided
        if category:
            base_query += f" AND category = ${len(params) + 1}"
            params.append(category)

        # Filter by industry vertical if provided
        if industry_vertical:
            base_query += f" AND (industry_vertical = ${len(params) + 1} OR industry_vertical IS NULL)"
            params.append(industry_vertical)

        # Filter by context keywords if provided
        if context:
            keywords = [word.strip().lower() for word in context.split(',')]
            for i, keyword in enumerate(keywords):
                base_query += f" AND (${len(params) + 1} = ANY(context_triggers) OR title ILIKE '%' || ${len(params) + 1} || '%' OR content ILIKE '%' || ${len(params) + 1} || '%')"
                params.append(keyword)

        base_query += " ORDER BY confidence_level DESC NULLS LAST, knowledge_type, category, title"

        results = await db.fetch(base_query, *params)

        return {
            "success": True,
            "data": {
                "knowledge": [dict(row) for row in results],
                "total_found": len(results),
                "context_applied": context or "none",
                "filters": {
                    "knowledge_type": knowledge_type or "none",
                    "category": category or "none",
                    "industry_vertical": industry_vertical or "none"
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving industry knowledge: {str(e)}")


@router.get("/kpi-analysis-suggestions")
async def get_kpi_analysis_suggestions(
    zone_data: Optional[str] = Query(None, description="JSON string with zone metrics for analysis"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get KPI analysis suggestions based on current zone performance"""

    try:
        import json

        suggestions = []

        # If zone data provided, analyze and suggest relevant KPIs
        if zone_data:
            try:
                data = json.loads(zone_data)

                # Determine relevant analysis templates based on the data
                context_keywords = []

                if 'avg_daily_occupancy_ratio' in data:
                    occupancy = float(data['avg_daily_occupancy_ratio'] or 0)
                    if occupancy > 85:
                        context_keywords.extend(['revenue', 'optimization', 'capacity'])
                    elif occupancy < 50:
                        context_keywords.extend(['efficiency', 'pricing', 'marketing'])
                    else:
                        context_keywords.extend(['performance', 'optimization'])

                if 'total_revenue' in data:
                    context_keywords.extend(['revenue', 'performance'])

                if 'avg_duration_minutes' in data:
                    duration = float(data['avg_duration_minutes'] or 0)
                    if duration < 60:
                        context_keywords.append('turnover')
                    elif duration > 240:
                        context_keywords.extend(['duration', 'premium'])

            except (json.JSONDecodeError, ValueError):
                context_keywords = ['general', 'performance']
        else:
            context_keywords = ['general', 'performance']

        # Get relevant analysis templates
        if context_keywords:
            keywords_str = ','.join(context_keywords)
            template_query = """
                SELECT
                    template_name,
                    kpi_combination,
                    analysis_type,
                    insight_template,
                    action_recommendations,
                    context_triggers
                FROM kpi_analysis_templates
                WHERE context_triggers && $1::text[]
                ORDER BY template_name
            """

            templates = await db.fetch(template_query, context_keywords)

            for template in templates:
                template_dict = dict(template)

                # Get the KPIs for this template
                if template_dict['kpi_combination']:
                    kpi_names = template_dict['kpi_combination']
                    kpi_placeholders = ','.join([f"${i+1}" for i in range(len(kpi_names))])

                    kpi_query = f"""
                        SELECT kpi_name, calculation_formula, interpretation_rules
                        FROM parking_kpis
                        WHERE kpi_name = ANY($1::text[]) AND is_active = true
                    """

                    related_kpis = await db.fetch(kpi_query, kpi_names)
                    template_dict['related_kpis'] = [dict(kpi) for kpi in related_kpis]

                suggestions.append(template_dict)

        return {
            "success": True,
            "data": {
                "suggestions": suggestions,
                "context_detected": context_keywords,
                "total_suggestions": len(suggestions)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating KPI analysis suggestions: {str(e)}")


@router.get("/expert-analysis/{zone_id}")
async def get_expert_analysis(
    zone_id: str,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get comprehensive expert analysis for a specific zone using parking industry expertise"""

    try:
        # Check zone access
        if zone_id not in user.zone_ids:
            raise HTTPException(status_code=403, detail="Access denied to zone")

        # Remove 'z-' prefix if present to match database format
        db_zone = zone_id.replace('z-', '')

        # Get zone statistics (same query as in insight generator)
        query = """
        SELECT
            COUNT(*) as total_transactions,
            AVG(ht.paid_minutes) as avg_duration_minutes,
            MIN(ht.paid_minutes) as min_duration_minutes,
            MAX(ht.paid_minutes) as max_duration_minutes,
            AVG(
                CASE
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^[0-9]+\.?[0-9]*$'
                    THEN ht.parking_amount::NUMERIC
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^\$[0-9]+\.?[0-9]*$'
                    THEN REPLACE(ht.parking_amount, '$', '')::NUMERIC
                    ELSE NULL
                END
            ) as avg_amount,
            SUM(
                CASE
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^[0-9]+\.?[0-9]*$'
                    THEN ht.parking_amount::NUMERIC
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^\$[0-9]+\.?[0-9]*$'
                    THEN REPLACE(ht.parking_amount, '$', '')::NUMERIC
                    ELSE NULL
                END
            ) as total_revenue,
            COUNT(DISTINCT ht.start_park_date) as active_days,
            COUNT(DISTINCT EXTRACT(DOW FROM ht.start_park_date)) as active_weekdays,
            MIN(ht.start_park_date) as first_transaction,
            MAX(ht.start_park_date) as last_transaction,
            l.capacity,
            l.name as location_name,
            CASE
                WHEN l.capacity > 0 THEN
                    ROUND((COUNT(*)::NUMERIC / COUNT(DISTINCT ht.start_park_date)::NUMERIC / l.capacity::NUMERIC) * 100, 2)
                ELSE NULL
            END as avg_daily_occupancy_ratio,
            CASE
                WHEN l.capacity > 0 THEN
                    ROUND((SUM(ht.paid_minutes)::NUMERIC / (COUNT(DISTINCT ht.start_park_date)::NUMERIC * 1440.0 * l.capacity::NUMERIC)) * 100, 2)
                ELSE NULL
            END as avg_utilization_ratio
        FROM historical_transactions ht
        LEFT JOIN locations l ON ht.zone::text = l.zone_id
        WHERE ht.zone::text = $1
        AND ht.paid_minutes IS NOT NULL
        GROUP BY l.capacity, l.name
        """

        result = await db.fetchrow(query, db_zone)

        if not result or result['total_transactions'] == 0:
            return {
                "success": False,
                "message": "No data available for expert analysis",
                "data": None
            }

        # Convert result to dict for expert analysis
        zone_stats = dict(result)
        zone_stats['zone_id'] = zone_id

        # Get expert analysis
        expert_ai = ParkingExpertAI(db)
        expert_analysis = await expert_ai.analyze_with_expert_knowledge(zone_stats)

        return {
            "success": True,
            "data": {
                "zone_id": zone_id,
                "zone_stats": zone_stats,
                "expert_analysis": expert_analysis
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing expert analysis: {str(e)}")