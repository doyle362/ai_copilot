from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from ..deps.auth import get_current_user, UserContext
from ..db import get_db, Database
from ..models.common import BaseResponse, PaginationParams, TimeWindow

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/daily")
async def get_daily_metrics(
    zone_id: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    pagination: PaginationParams = Depends(),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    # Build query with zone filtering
    where_clauses = []
    params = []
    param_idx = 1

    # Filter by user's accessible zones
    zone_filter = f"zone_id = ANY(${param_idx})"
    params.append(user.zone_ids)
    where_clauses.append(zone_filter)
    param_idx += 1

    if zone_id:
        if zone_id not in user.zone_ids:
            return BaseResponse(success=False, message="Access denied to zone")
        where_clauses.append(f"zone_id = ${param_idx}")
        params.append(zone_id)
        param_idx += 1

    if location_id:
        where_clauses.append(f"location_id = ${param_idx}")
        params.append(location_id)
        param_idx += 1

    if start_date:
        where_clauses.append(f"date >= ${param_idx}")
        params.append(start_date)
        param_idx += 1

    if end_date:
        where_clauses.append(f"date <= ${param_idx}")
        params.append(end_date)
        param_idx += 1

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
        SELECT date, location_id, zone_id, rev, occupancy_pct, avg_ticket
        FROM mart_metrics_daily
        WHERE {where_clause}
        ORDER BY date DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([pagination.limit, pagination.offset])

    # Count query
    count_query = f"""
        SELECT COUNT(*) FROM mart_metrics_daily WHERE {where_clause}
    """

    try:
        async with db.transaction() as conn:
            # Set JWT claims for RLS
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            results = await conn.fetch(query, *params[:-2])
            total = await conn.fetchval(count_query, *params[:-2])

        return BaseResponse(data={
            "metrics": [dict(row) for row in results],
            "total": total,
            "offset": pagination.offset,
            "limit": pagination.limit
        })

    except Exception as e:
        return BaseResponse(success=False, message=f"Error fetching metrics: {str(e)}")


@router.get("/hourly")
async def get_hourly_metrics(
    zone_id: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    start_ts: Optional[datetime] = Query(None),
    end_ts: Optional[datetime] = Query(None),
    pagination: PaginationParams = Depends(),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    # Similar structure to daily metrics but for hourly data
    where_clauses = []
    params = []
    param_idx = 1

    zone_filter = f"zone_id = ANY(${param_idx})"
    params.append(user.zone_ids)
    where_clauses.append(zone_filter)
    param_idx += 1

    if zone_id:
        if zone_id not in user.zone_ids:
            return BaseResponse(success=False, message="Access denied to zone")
        where_clauses.append(f"zone_id = ${param_idx}")
        params.append(zone_id)
        param_idx += 1

    if location_id:
        where_clauses.append(f"location_id = ${param_idx}")
        params.append(location_id)
        param_idx += 1

    if start_ts:
        where_clauses.append(f"ts >= ${param_idx}")
        params.append(start_ts)
        param_idx += 1

    if end_ts:
        where_clauses.append(f"ts <= ${param_idx}")
        params.append(end_ts)
        param_idx += 1

    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
        SELECT ts, location_id, zone_id, rev, occupancy_pct, avg_ticket
        FROM mart_metrics_hourly
        WHERE {where_clause}
        ORDER BY ts DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([pagination.limit, pagination.offset])

    count_query = f"""
        SELECT COUNT(*) FROM mart_metrics_hourly WHERE {where_clause}
    """

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            results = await conn.fetch(query, *params[:-2])
            total = await conn.fetchval(count_query, *params[:-2])

        return BaseResponse(data={
            "metrics": [dict(row) for row in results],
            "total": total,
            "offset": pagination.offset,
            "limit": pagination.limit
        })

    except Exception as e:
        return BaseResponse(success=False, message=f"Error fetching hourly metrics: {str(e)}")