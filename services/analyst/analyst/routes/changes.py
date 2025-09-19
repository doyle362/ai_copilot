from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID
from ..deps.auth import get_current_user, UserContext, require_role
from ..db import get_db, Database
from ..models.changes import (
    PriceChangeCreate, PriceChangeResponse, ChangeListResponse,
    ApplyChangeRequest, RevertChangeRequest
)
from ..models.common import BaseResponse, PaginationParams
from ..core.policy_guardrails import PolicyGuardrails
from ..config import settings

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("/", response_model=ChangeListResponse)
async def list_price_changes(
    zone_id: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
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
        SELECT id, location_id, zone_id, prev_price, new_price, change_pct,
               policy_version, recommendation_id, applied_by, applied_at,
               revert_to, revert_if, expires_at, status, created_at
        FROM price_changes
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])

    count_query = f"""
        SELECT COUNT(*) FROM price_changes WHERE {where_clause}
    """

    try:
        # Execute the zone-filtered query with proper parameters
        results = await db.fetch(query, *params)
        total_result = await db.fetchval(count_query, *params[:-2])  # Exclude limit and offset for count
        total = total_result or 0

        changes = [PriceChangeResponse(**dict(row)) for row in results]
        return ChangeListResponse(
            changes=changes,
            total=total,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price changes: {str(e)}")


@router.post("/", response_model=PriceChangeResponse)
async def create_price_change(
    change: PriceChangeCreate,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if change.zone_id not in user.zone_ids:
        raise HTTPException(status_code=403, detail="Access denied to zone")

    # Validate against guardrails
    guardrails = PolicyGuardrails(db)
    validation_result = await guardrails.validate_price_change(change)

    if not validation_result.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Guardrail violation: {validation_result.reason}"
        )

    # Calculate change percentage if not provided
    change_pct = change.change_pct
    if change.prev_price and not change_pct:
        change_pct = (change.new_price - change.prev_price) / change.prev_price

    query = """
        INSERT INTO price_changes (location_id, zone_id, prev_price, new_price, change_pct,
                                 policy_version, recommendation_id, revert_to, revert_if, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, location_id, zone_id, prev_price, new_price, change_pct,
                  policy_version, recommendation_id, applied_by, applied_at,
                  revert_to, revert_if, expires_at, status, created_at
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
                change.location_id,
                change.zone_id,
                change.prev_price,
                change.new_price,
                change_pct,
                change.policy_version,
                change.recommendation_id,
                change.revert_to,
                change.revert_if,
                change.expires_at
            )

        return PriceChangeResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating price change: {str(e)}")


@router.post("/apply", response_model=BaseResponse)
async def apply_price_change(
    request: ApplyChangeRequest,
    user: UserContext = Depends(require_role("approver")),
    db: Database = Depends(get_db)
):
    if settings.analyst_require_approval and not request.force:
        if "approver" not in user.roles:
            raise HTTPException(
                status_code=403,
                detail="Approval required for price changes"
            )

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            # Get the change details
            change_result = await conn.fetchrow(
                "SELECT * FROM price_changes WHERE id = $1",
                request.change_id
            )

            if not change_result:
                raise HTTPException(status_code=404, detail="Price change not found")

            change = dict(change_result)

            if change["status"] != "pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot apply change with status: {change['status']}"
                )

            # Re-validate guardrails
            guardrails = PolicyGuardrails(db)
            change_obj = PriceChangeCreate(**{
                k: v for k, v in change.items()
                if k in PriceChangeCreate.__fields__
            })
            validation_result = await guardrails.validate_price_change(change_obj)

            if not validation_result.is_valid and not request.force:
                raise HTTPException(
                    status_code=400,
                    detail=f"Guardrail violation: {validation_result.reason}"
                )

            # Update the change status
            await conn.execute("""
                UPDATE price_changes
                SET status = 'applied', applied_by = $2, applied_at = NOW()
                WHERE id = $1
            """, request.change_id, UUID(user.sub) if user.sub != "dev-user" else None)

            # TODO: Here you would integrate with actual pricing system
            # For now, we just simulate the application

        return BaseResponse(message="Price change applied successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying price change: {str(e)}")


@router.post("/revert", response_model=BaseResponse)
async def revert_price_change(
    request: RevertChangeRequest,
    user: UserContext = Depends(require_role("approver")),
    db: Database = Depends(get_db)
):
    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            # Get the change details
            change_result = await conn.fetchrow(
                "SELECT * FROM price_changes WHERE id = $1",
                request.change_id
            )

            if not change_result:
                raise HTTPException(status_code=404, detail="Price change not found")

            change = dict(change_result)

            if change["status"] != "applied":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot revert change with status: {change['status']}"
                )

            # Update the change status
            await conn.execute("""
                UPDATE price_changes
                SET status = 'reverted'
                WHERE id = $1
            """, request.change_id)

            # TODO: Here you would integrate with actual pricing system to revert
            # For now, we just simulate the reversion

        return BaseResponse(message="Price change reverted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reverting price change: {str(e)}")


@router.get("/{change_id}", response_model=PriceChangeResponse)
async def get_price_change(
    change_id: UUID,
    user: UserContext = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = """
        SELECT id, location_id, zone_id, prev_price, new_price, change_pct,
               policy_version, recommendation_id, applied_by, applied_at,
               revert_to, revert_if, expires_at, status, created_at
        FROM price_changes
        WHERE id = $1
    """

    try:
        async with db.transaction() as conn:
            await db.set_jwt_claims(conn, {
                "sub": user.sub,
                "org_id": user.org_id,
                "zone_ids": user.zone_ids
            })

            result = await conn.fetchrow(query, change_id)

        if not result:
            raise HTTPException(status_code=404, detail="Price change not found")

        return PriceChangeResponse(**dict(result))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price change: {str(e)}")