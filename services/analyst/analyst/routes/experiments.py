"""
Experiments endpoints for elasticity probes and pricing tests.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..deps.auth import get_current_user, UserContext
from ..db import get_db
from ..core.elasticity_probe import schedule_probe, evaluate_probe

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ProbeRequest(BaseModel):
    zone_id: str = Field(..., description="Zone identifier to run probe in")
    daypart: str = Field(..., pattern=r"^(morning|evening)$", description="Time period: morning or evening")
    dow: int = Field(..., ge=0, le=6, description="Day of week (0=Sunday, 6=Saturday)")
    deltas: Optional[List[float]] = Field(None, description="Price change percentages (e.g., [-0.05, 0.02, 0.05])")
    horizon_days: Optional[int] = Field(14, ge=1, le=90, description="Experiment duration in days")


class ProbeResponse(BaseModel):
    experiment_id: str
    zone_id: str
    daypart: str
    dow: int
    arms: List[Dict[str, Any]]
    status: str
    ends_at: str
    horizon_days: int


class ExperimentSummary(BaseModel):
    experiment_id: str
    zone_id: str
    daypart: str
    dow: int
    status: str
    created_at: str
    ends_at: Optional[str]
    arms_count: int


class EvaluationResponse(BaseModel):
    experiment_id: str
    status: str
    results: List[Dict[str, Any]]
    evaluated_at: str


@router.post("/elasticity/probe", response_model=ProbeResponse)
async def schedule_elasticity_probe(
    request: ProbeRequest,
    db=Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """
    Schedule a new elasticity probe experiment.

    Creates experiment arms with delta-adjusted pricing tiers and schedules
    them for the specified zone, daypart, and day of week.
    """
    try:
        result = await schedule_probe(
            db=db,
            ctx=ctx,
            zone_id=request.zone_id,
            daypart=request.daypart,
            dow=request.dow,
            deltas=request.deltas or [],
            horizon_days=request.horizon_days
        )

        return ProbeResponse(
            experiment_id=result['experiment_id'],
            zone_id=request.zone_id,
            daypart=request.daypart,
            dow=request.dow,
            arms=result['arms'],
            status=result['status'],
            ends_at=result['ends_at'],
            horizon_days=result['horizon_days']
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule probe: {str(e)}")


@router.get("/", response_model=List[ExperimentSummary])
async def list_experiments(
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Field(50, ge=1, le=200),
    db=Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """
    List experiments accessible to the current user.

    Filters by zone_id and status if provided.
    """
    try:
        # Build query conditions
        conditions = []
        params = []
        param_idx = 1

        # Zone filter
        if zone_id:
            if zone_id not in ctx.zone_ids:
                raise HTTPException(status_code=403, detail=f"Zone {zone_id} not accessible")
            conditions.append(f"e.zone_id = ${param_idx}")
            params.append(zone_id)
            param_idx += 1
        else:
            # Filter to accessible zones
            zone_placeholders = ", ".join([f"${i}" for i in range(param_idx, param_idx + len(ctx.zone_ids))])
            conditions.append(f"e.zone_id IN ({zone_placeholders})")
            params.extend(ctx.zone_ids)
            param_idx += len(ctx.zone_ids)

        # Status filter
        if status:
            conditions.append(f"e.status = ${param_idx}")
            params.append(status)
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                e.id as experiment_id,
                e.zone_id,
                e.daypart,
                e.dow,
                e.status,
                e.created_at,
                e.ends_at,
                COUNT(a.id) as arms_count
            FROM pricing_experiments e
            LEFT JOIN pricing_experiment_arms a ON e.id = a.experiment_id
            {where_clause}
            GROUP BY e.id, e.zone_id, e.daypart, e.dow, e.status, e.created_at, e.ends_at
            ORDER BY e.created_at DESC
            LIMIT ${param_idx}
        """
        params.append(limit)

        rows = await db.fetch(query, *params)

        return [
            ExperimentSummary(
                experiment_id=str(row['experiment_id']),
                zone_id=row['zone_id'],
                daypart=row['daypart'],
                dow=row['dow'],
                status=row['status'],
                created_at=row['created_at'].isoformat(),
                ends_at=row['ends_at'].isoformat() if row['ends_at'] else None,
                arms_count=row['arms_count']
            )
            for row in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list experiments: {str(e)}")


@router.get("/{experiment_id}", response_model=Dict[str, Any])
async def get_experiment(
    experiment_id: str,
    db=Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """
    Get detailed experiment information including arms and results.
    """
    try:
        # Validate UUID format
        exp_uuid = uuid.UUID(experiment_id)

        # Get experiment details
        experiment = await db.fetchrow(
            """
            SELECT e.*,
                   COUNT(a.id) as arms_count,
                   COUNT(r.experiment_id) as results_count
            FROM pricing_experiments e
            LEFT JOIN pricing_experiment_arms a ON e.id = a.experiment_id
            LEFT JOIN pricing_experiment_results r ON e.id = r.experiment_id
            WHERE e.id = $1
            GROUP BY e.id
            """,
            exp_uuid
        )

        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")

        # Check zone access
        if experiment['zone_id'] not in ctx.zone_ids:
            raise HTTPException(status_code=403, detail="Experiment not accessible")

        # Get arms
        arms = await db.fetch(
            "SELECT * FROM pricing_experiment_arms WHERE experiment_id = $1 ORDER BY delta",
            exp_uuid
        )

        # Get results if available
        results = await db.fetch(
            "SELECT * FROM pricing_experiment_results WHERE experiment_id = $1",
            exp_uuid
        )

        return {
            "experiment_id": experiment_id,
            "zone_id": experiment['zone_id'],
            "daypart": experiment['daypart'],
            "dow": experiment['dow'],
            "deltas": experiment['deltas'],
            "guardrails_snapshot": experiment['guardrails_snapshot'],
            "horizon_days": experiment['horizon_days'],
            "status": experiment['status'],
            "started_at": experiment['started_at'].isoformat() if experiment['started_at'] else None,
            "ends_at": experiment['ends_at'].isoformat() if experiment['ends_at'] else None,
            "created_at": experiment['created_at'].isoformat(),
            "arms_count": experiment['arms_count'],
            "results_count": experiment['results_count'],
            "arms": [
                {
                    "arm_id": str(arm['id']),
                    "delta": float(arm['delta']),
                    "proposal": arm['proposal'],
                    "control": arm['control'],
                    "status": arm['status'],
                    "applied_change_id": str(arm['applied_change_id']) if arm['applied_change_id'] else None
                }
                for arm in arms
            ],
            "results": [
                {
                    "arm_id": str(result['arm_id']),
                    "metric_window": str(result['metric_window']),
                    "rev_psh": float(result['rev_psh']) if result['rev_psh'] else None,
                    "occupancy": float(result['occupancy']) if result['occupancy'] else None,
                    "lift_rev_psh": float(result['lift_rev_psh']) if result['lift_rev_psh'] else None,
                    "lift_occupancy": float(result['lift_occupancy']) if result['lift_occupancy'] else None,
                    "method": result['method'],
                    "computed_at": result['computed_at'].isoformat()
                }
                for result in results
            ]
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get experiment: {str(e)}")


@router.post("/{experiment_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_experiment(
    experiment_id: str,
    db=Depends(get_db),
    ctx: UserContext = Depends(get_current_user)
):
    """
    Evaluate experiment results and compute lift metrics.

    This endpoint calculates revenue per space-hour and occupancy metrics
    for each experiment arm, comparing against the control group.
    """
    try:
        # Validate UUID format
        exp_uuid = uuid.UUID(experiment_id)

        # Check experiment exists and is accessible
        experiment = await db.fetchrow(
            "SELECT zone_id FROM pricing_experiments WHERE id = $1",
            exp_uuid
        )

        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")

        if experiment['zone_id'] not in ctx.zone_ids:
            raise HTTPException(status_code=403, detail="Experiment not accessible")

        # Evaluate the experiment
        result = await evaluate_probe(db, experiment_id)

        return EvaluationResponse(
            experiment_id=result['experiment_id'],
            status=result['status'],
            results=result['results'],
            evaluated_at=result['evaluated_at']
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid experiment ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate experiment: {str(e)}")