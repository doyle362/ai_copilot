from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from uuid import UUID
from ..deps.auth import get_current_user, UserContext
from ..db import get_db, Database
from ..models.recommendations import (
    RecommendationCreate, RecommendationResponse, RecommendationListResponse,
    RecommendationGenerateRequest
)
from ..models.common import BaseResponse, PaginationParams
from ..core.recommendation_engine import RecommendationEngine
from ..core.expert_recommendation_engine import ExpertRecommendationEngine
from ..core.daily_refresh import ensure_daily_refresh

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/", response_model=RecommendationListResponse)
async def list_recommendations(
    zone_id: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    refresh: bool = Query(False, description="Regenerate insights and recommendations on demand"),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    await ensure_daily_refresh(db, user.zone_ids, force_refresh=refresh)

    where_clauses = []
    params = []
    param_idx = 1

    # Zone access enforced by RLS
    zone_filter = f"zone_id = ANY(${param_idx})"
    params.append(user.zone_ids)
    where_clauses.append(zone_filter)
    param_idx += 1

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

    if status:
        where_clauses.append(f"status = ${param_idx}")
        params.append(status)
        param_idx += 1

    where_clause = " AND ".join(where_clauses)

    query = f"""
        SELECT id, location_id, zone_id, type,
               CASE
                 WHEN proposal IS NOT NULL THEN proposal::jsonb
                 ELSE '{{}}'::jsonb
               END as proposal,
               rationale_text, expected_lift_json, confidence, requires_approval,
               COALESCE(memory_ids_used, '{{}}') as memory_ids_used,
               prompt_version_id, thread_id, status, created_at
        FROM recommendations
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])

    count_query = f"""
        SELECT COUNT(*) FROM recommendations WHERE {where_clause}
    """

    try:
        # Execute the zone-filtered query with proper parameters
        results = await db.fetch(query, *params)
        total_result = await db.fetchval(count_query, *params[:-2])  # Exclude limit and offset for count
        total = total_result or 0

        # Parse recommendations and handle JSON fields
        recommendations = []
        for row in results:
            row_dict = dict(row)
            # Ensure proposal is a dict if it comes as a string
            if isinstance(row_dict.get('proposal'), str):
                import json
                try:
                    row_dict['proposal'] = json.loads(row_dict['proposal'])
                except (json.JSONDecodeError, TypeError):
                    row_dict['proposal'] = {}
            elif row_dict.get('proposal') is None:
                row_dict['proposal'] = {}

            # Ensure expected_lift_json is a dict if it comes as a string
            if isinstance(row_dict.get('expected_lift_json'), str):
                import json
                try:
                    row_dict['expected_lift_json'] = json.loads(row_dict['expected_lift_json'])
                except (json.JSONDecodeError, TypeError):
                    row_dict['expected_lift_json'] = {}
            elif row_dict.get('expected_lift_json') is None:
                row_dict['expected_lift_json'] = {}

            recommendations.append(RecommendationResponse(**row_dict))
        return RecommendationListResponse(
            recommendations=recommendations,
            total=total,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations: {str(e)}")


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: UUID,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        SELECT id, location_id, zone_id, type, proposal, rationale_text,
               expected_lift_json, confidence, requires_approval, memory_ids_used,
               prompt_version_id, thread_id, status, created_at
        FROM recommendations
        WHERE id = $1
    """

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            result = await conn.fetchrow(query, recommendation_id)

        if not result:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        # Handle JSON parsing for single recommendation
        result_dict = dict(result)
        if isinstance(result_dict.get('proposal'), str):
            import json
            try:
                result_dict['proposal'] = json.loads(result_dict['proposal'])
            except (json.JSONDecodeError, TypeError):
                result_dict['proposal'] = {}
        elif result_dict.get('proposal') is None:
            result_dict['proposal'] = {}

        return RecommendationResponse(**result_dict)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendation: {str(e)}")


@router.post("/generate", response_model=BaseResponse)
async def generate_recommendations(
    request: RecommendationGenerateRequest,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if request.zone_id not in user.zone_ids:
        raise HTTPException(status_code=403, detail="Access denied to zone")

    try:
        engine = RecommendationEngine(db)

        # Run recommendation generation in background
        background_tasks.add_task(
            engine.generate_recommendations_for_zone,
            request.zone_id,
            request.location_id,
            request.context,
            request.force_reason_model,
            user.sub
        )

        return BaseResponse(message="Recommendation generation started")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting recommendation generation: {str(e)}")


@router.post("/", response_model=RecommendationResponse)
async def create_recommendation(
    recommendation: RecommendationCreate,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if recommendation.zone_id not in user.zone_ids:
        raise HTTPException(status_code=403, detail="Access denied to zone")

    query = """
        INSERT INTO recommendations (location_id, zone_id, type, proposal, rationale_text,
                                   expected_lift_json, confidence, requires_approval, thread_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, location_id, zone_id, type, proposal, rationale_text,
                  expected_lift_json, confidence, requires_approval, memory_ids_used,
                  prompt_version_id, thread_id, status, created_at
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
                recommendation.location_id,
                recommendation.zone_id,
                recommendation.type,
                recommendation.proposal,
                recommendation.rationale_text,
                recommendation.expected_lift_json,
                recommendation.confidence,
                recommendation.requires_approval,
                recommendation.thread_id
            )

        return RecommendationResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating recommendation: {str(e)}")


@router.post("/generate-expert", response_model=BaseResponse)
async def generate_expert_recommendations(
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Generate expert recommendations for all user zones using parking industry knowledge"""

    try:
        expert_engine = ExpertRecommendationEngine(db)

        # Run expert recommendation generation in background
        background_tasks.add_task(
            expert_engine.generate_recommendations_for_all_zones,
            user.zone_ids
        )

        return BaseResponse(message=f"Expert recommendation generation started for {len(user.zone_ids)} zones")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting expert recommendation generation: {str(e)}")


@router.patch("/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: UUID,
    status: str,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if status not in ["draft", "pending", "approved", "rejected", "applied"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    query = """
        UPDATE recommendations
        SET status = $2
        WHERE id = $1
        RETURNING id, location_id, zone_id, type, proposal, rationale_text,
                  expected_lift_json, confidence, requires_approval, memory_ids_used,
                  prompt_version_id, thread_id, status, created_at
    """

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            result = await conn.fetchrow(query, recommendation_id, status)

        if not result:
            raise HTTPException(status_code=404, detail="Recommendation not found or access denied")

        return RecommendationResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating recommendation: {str(e)}")
