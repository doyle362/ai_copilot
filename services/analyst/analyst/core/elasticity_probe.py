"""
Elasticity probe functionality for safe price testing.
"""
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional

from ..config import settings
from ..deps.auth import UserContext


def round_to_quarter(amount: float) -> float:
    """Round amount to nearest $0.25."""
    decimal_amount = Decimal(str(amount))
    quarter = Decimal('0.25')
    return float(decimal_amount.quantize(quarter, rounding=ROUND_HALF_UP))


def build_probe_arms(
    zone_id: str,
    daypart: str,
    dow: int,
    base_tiers: List[Dict[str, Any]],
    deltas: List[float],
    guardrails: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Build experiment arms with delta-adjusted pricing tiers.

    Returns list of arms, each with:
    - delta: price change percentage
    - proposal: adjusted tier structure
    - control: whether this is the control arm (delta=0)
    """
    arms = []
    max_change_pct = guardrails.get('max_change_pct', 0.20)
    probe_max_delta = settings.analyst_probe_max_delta

    # Ensure control arm (delta=0) is included
    if 0.0 not in deltas:
        deltas = [0.0] + list(deltas)

    for delta in deltas:
        # Validate delta against limits
        if abs(delta) > probe_max_delta:
            continue  # Skip deltas beyond system limit
        if abs(delta) > max_change_pct:
            continue  # Skip deltas beyond guardrail limit

        # Build adjusted tiers
        adjusted_tiers = []
        for tier in base_tiers:
            current_rate = float(tier.get('rate_per_hour', 0))
            adjusted_rate = current_rate * (1 + delta)

            # Round to sensible increment ($0.25)
            adjusted_rate = round_to_quarter(adjusted_rate)

            adjusted_tier = {
                **tier,
                'rate_per_hour': adjusted_rate,
                'original_rate': current_rate,
                'delta_applied': delta
            }
            adjusted_tiers.append(adjusted_tier)

        arm = {
            'delta': delta,
            'proposal': {
                'zone_id': zone_id,
                'daypart': daypart,
                'dow': dow,
                'tiers': adjusted_tiers,
                'effective_date': datetime.utcnow().isoformat(),
            },
            'control': delta == 0.0
        }
        arms.append(arm)

    return arms


async def schedule_probe(
    db,
    ctx: UserContext,
    zone_id: str,
    daypart: str,
    dow: int,
    deltas: List[float],
    horizon_days: int
) -> Dict[str, Any]:
    """
    Schedule a new elasticity probe experiment.

    Returns dict with experiment_id, arms, status, and ends_at.
    """
    # Validate zone access
    if zone_id not in ctx.zone_ids:
        raise ValueError(f"Zone {zone_id} not accessible to user")

    # Parse default deltas if none provided
    if not deltas:
        default_deltas_str = settings.analyst_probe_default_deltas
        deltas = json.loads(default_deltas_str)

    # Get base tiers (simplified - would normally query inferred_rate_plans)
    # For demo, create reasonable default tiers
    base_tiers = [
        {'duration_max_min': 60, 'rate_per_hour': 4.00, 'tier_name': 'First hour'},
        {'duration_max_min': 180, 'rate_per_hour': 6.00, 'tier_name': 'Up to 3 hours'},
        {'duration_max_min': 480, 'rate_per_hour': 8.00, 'tier_name': 'Half day'},
        {'duration_max_min': 1440, 'rate_per_hour': 10.00, 'tier_name': 'Full day'},
    ]

    # Snapshot current guardrails
    guardrails_snapshot = {
        'max_change_pct': 0.15,
        'min_approval_required': True,
        'created_at': datetime.utcnow().isoformat()
    }

    # Build experiment arms
    arms = build_probe_arms(zone_id, daypart, dow, base_tiers, deltas, guardrails_snapshot)

    # Calculate end time
    ends_at = datetime.utcnow() + timedelta(days=horizon_days)

    # Insert experiment
    experiment_id = str(uuid.uuid4())
    experiment_query = """
        INSERT INTO pricing_experiments
        (id, zone_id, daypart, dow, deltas, guardrails_snapshot, horizon_days, ends_at, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
    """

    await db.execute(
        experiment_query,
        experiment_id,
        zone_id,
        daypart,
        dow,
        deltas,
        json.dumps(guardrails_snapshot),
        horizon_days,
        ends_at,
        uuid.UUID(ctx.sub)
    )

    # Insert arms
    arm_ids = []
    for arm in arms:
        arm_id = str(uuid.uuid4())
        arm_query = """
            INSERT INTO pricing_experiment_arms
            (id, experiment_id, delta, proposal, control)
            VALUES ($1, $2, $3, $4, $5)
        """

        await db.execute(
            arm_query,
            arm_id,
            experiment_id,
            arm['delta'],
            json.dumps(arm['proposal']),
            arm['control']
        )
        arm_ids.append(arm_id)

    return {
        'experiment_id': experiment_id,
        'arms': arms,
        'status': 'scheduled',
        'ends_at': ends_at.isoformat(),
        'horizon_days': horizon_days
    }


async def evaluate_probe(db, experiment_id: str) -> Dict[str, Any]:
    """
    Evaluate probe experiment results and compute lift metrics.

    Returns summary of results with lift calculations.
    """
    # Get experiment details
    experiment = await db.fetchrow(
        "SELECT * FROM pricing_experiments WHERE id = $1",
        uuid.UUID(experiment_id)
    )

    if not experiment:
        raise ValueError(f"Experiment {experiment_id} not found")

    # Get arms
    arms = await db.fetch(
        "SELECT * FROM pricing_experiment_arms WHERE experiment_id = $1",
        uuid.UUID(experiment_id)
    )

    # For demo purposes, simulate results
    # In production, this would query actual transaction/occupancy data
    results = []
    control_metrics = {'rev_psh': 8.50, 'occupancy': 0.65}  # Baseline

    for arm in arms:
        arm_dict = dict(arm)
        delta = float(arm_dict['delta'])

        if arm_dict['control']:
            # Control arm gets baseline metrics
            rev_psh = control_metrics['rev_psh']
            occupancy = control_metrics['occupancy']
            lift_rev_psh = 0.0
            lift_occupancy = 0.0
        else:
            # Simulate elasticity effects
            # Simplified model: higher prices reduce demand but may increase revenue
            occupancy_impact = -delta * 0.3  # 30% demand elasticity
            revenue_impact = delta + (occupancy_impact * 0.5)  # Net effect

            occupancy = control_metrics['occupancy'] * (1 + occupancy_impact)
            rev_psh = control_metrics['rev_psh'] * (1 + revenue_impact)

            lift_rev_psh = revenue_impact
            lift_occupancy = occupancy_impact

        # Insert or update results
        result_query = """
            INSERT INTO pricing_experiment_results
            (experiment_id, arm_id, metric_window, rev_psh, occupancy, lift_rev_psh, lift_occupancy)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (experiment_id, arm_id, metric_window)
            DO UPDATE SET
                rev_psh = EXCLUDED.rev_psh,
                occupancy = EXCLUDED.occupancy,
                lift_rev_psh = EXCLUDED.lift_rev_psh,
                lift_occupancy = EXCLUDED.lift_occupancy,
                computed_at = now()
        """

        metric_window = f"[{experiment['created_at'].date()},{experiment['ends_at'].date()})"

        await db.execute(
            result_query,
            uuid.UUID(experiment_id),
            arm_dict['id'],
            metric_window,
            rev_psh,
            occupancy,
            lift_rev_psh,
            lift_occupancy
        )

        results.append({
            'arm_id': str(arm_dict['id']),
            'delta': delta,
            'control': arm_dict['control'],
            'rev_psh': round(rev_psh, 2),
            'occupancy': round(occupancy, 3),
            'lift_rev_psh': round(lift_rev_psh, 3),
            'lift_occupancy': round(lift_occupancy, 3)
        })

    return {
        'experiment_id': experiment_id,
        'status': 'evaluated',
        'results': results,
        'evaluated_at': datetime.utcnow().isoformat()
    }