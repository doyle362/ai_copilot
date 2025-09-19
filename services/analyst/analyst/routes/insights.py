from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID
import logging
import json
from ..deps.auth import get_current_user, UserContext
from ..db import get_db, Database
from ..models.common import BaseResponse, PaginationParams
from ..models.insights import InsightCreate, InsightResponse, InsightListResponse
from ..core.daily_refresh import ensure_daily_refresh

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/", response_model=InsightListResponse)
async def list_insights(
    zone_id: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    kind: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    refresh: bool = Query(False, description="Generate fresh insights from historical data"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    try:
        logger.info(f"Insights route called: refresh={refresh}, limit={limit}")
        await ensure_daily_refresh(db, user.zone_ids, force_refresh=refresh)

        # Now fetch insights with filtering
        where_clauses = []
        params = []
        param_idx = 1

        # Zone access is enforced by RLS, but we still filter by accessible zones
        if user.zone_ids:
            zone_placeholders = ', '.join([f"${param_idx + i}" for i in range(len(user.zone_ids))])
            zone_filter = f"zone_id IN ({zone_placeholders})"
            params.extend(user.zone_ids)
            where_clauses.append(zone_filter)
            param_idx += len(user.zone_ids)

        if zone_id:
            if zone_id not in user.zone_ids:
                raise HTTPException(status_code=403, detail="Access denied to zone")
            where_clauses.append(f"zone_id = ${param_idx}")
            params.append(zone_id)
            param_idx += 1

        if location_id:
            where_clauses.append(f"location_id = ${param_idx}")
            params.append(location_id)
            param_idx += 1

        if kind:
            where_clauses.append(f"kind = ${param_idx}")
            params.append(kind)
            param_idx += 1

        where_clause = " AND ".join(where_clauses) or "TRUE"

        query = f"""
            SELECT id, location_id, zone_id, kind, "window", metrics_json,
                   narrative_text, confidence, created_at, created_by
            FROM insights
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        count_query = f"""
            SELECT COUNT(*) FROM insights WHERE {where_clause}
        """

        # Execute the zone-filtered query with proper parameters
        logger.info(f"🔥 Executing query with params: {params}")
        logger.info(f"🔥 Query: {query}")
        results = await db.fetch(query, *params)
        total_result = await db.fetchval(count_query, *params[:-2])  # Exclude limit and offset for count
        total = total_result or 0

        logger.info(f"🔥 Query returned {len(results)} results, total={total}")
        if results:
            zones_in_results = list(set([row['zone_id'] for row in results]))
            logger.info(f"🔥 Zones in query results: {sorted(zones_in_results)}")

        # Convert results and parse JSON fields
        parsed_results = []
        for row in results:
            row_dict = dict(row)
            # Parse the JSON string back to dict if it exists
            if row_dict.get('metrics_json'):
                try:
                    row_dict['metrics_json'] = json.loads(row_dict['metrics_json'])
                except (json.JSONDecodeError, TypeError):
                    row_dict['metrics_json'] = {}
            parsed_results.append(row_dict)

        insights = [InsightResponse(**row_dict) for row_dict in parsed_results]

        logger.info(f"🔥 Returning {len(insights)} insights to frontend")
        return InsightListResponse(
            insights=insights,
            total=total,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error in list_insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching insights: {str(e)}")


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: UUID,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        SELECT id, location_id, zone_id, kind, "window", metrics_json,
               narrative_text, confidence, created_at, created_by
        FROM insights
        WHERE id = $1
    """

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            result = await conn.fetchrow(query, insight_id)

        if not result:
            raise HTTPException(status_code=404, detail="Insight not found")

        return InsightResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching insight: {str(e)}")


@router.post("/", response_model=InsightResponse)
async def create_insight(
    insight: InsightCreate,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if insight.zone_id not in user.zone_ids:
        raise HTTPException(status_code=403, detail="Access denied to zone")

    query = """
        INSERT INTO insights (location_id, zone_id, kind, "window", metrics_json,
                             narrative_text, confidence, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, location_id, zone_id, kind, "window", metrics_json,
                  narrative_text, confidence, created_at, created_by
    """

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            result = await conn.fetchrow(
                query,
                insight.location_id,
                insight.zone_id,
                insight.kind,
                insight.window,
                insight.metrics_json,
                insight.narrative_text,
                insight.confidence,
                UUID(user.sub) if user.sub != "dev-user" else None
            )

        return InsightResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating insight: {str(e)}")
