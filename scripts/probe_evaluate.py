#!/usr/bin/env python3
"""
CLI script to evaluate elasticity probe experiment results.

Usage:
    python scripts/probe_evaluate.py <experiment_id>
"""
import asyncio
import argparse
import json
import sys
import os
import uuid

# Add services path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../services/analyst'))

from analyst.db import db
from analyst.deps.auth import UserContext
from analyst.core.elasticity_probe import evaluate_probe
from analyst.config import settings


async def main():
    parser = argparse.ArgumentParser(description='Evaluate elasticity probe experiment')
    parser.add_argument('experiment_id', help='Experiment ID to evaluate')
    parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format')

    args = parser.parse_args()

    # Validate experiment ID format
    try:
        uuid.UUID(args.experiment_id)
    except ValueError:
        print(f"❌ Invalid experiment ID format: {args.experiment_id}", file=sys.stderr)
        sys.exit(1)

    # Create user context (use dev zones for CLI)
    ctx = UserContext(
        sub="00000000-0000-0000-0000-000000000000",
        zone_ids=settings.dev_zone_ids_list,
        org_id=settings.org_id
    )

    try:
        # Initialize database
        await db.initialize()

        # Check experiment exists and is accessible
        experiment = await db.pool.fetchrow(
            "SELECT zone_id, daypart, dow, status FROM pricing_experiments WHERE id = $1",
            uuid.UUID(args.experiment_id)
        )

        if not experiment:
            print(f"❌ Experiment {args.experiment_id} not found", file=sys.stderr)
            sys.exit(1)

        if experiment['zone_id'] not in ctx.zone_ids:
            print(f"❌ Experiment not accessible in zone {experiment['zone_id']}", file=sys.stderr)
            sys.exit(1)

        # Evaluate the experiment
        result = await evaluate_probe(db.pool, args.experiment_id)

        if args.format == 'json':
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"📈 Elasticity Probe Evaluation Results")
            print(f"   Experiment: {args.experiment_id}")
            print(f"   Zone: {experiment['zone_id']}")
            print(f"   Daypart: {experiment['daypart']}")
            print(f"   Day of week: {experiment['dow']}")
            print(f"   Status: {result['status']}")
            print(f"   Evaluated at: {result['evaluated_at']}")
            print()

            if result['results']:
                print("Results by arm:")
                print(f"{'Delta':<8} {'Control':<7} {'Rev/PSH':<8} {'Occupancy':<10} {'Rev Lift':<9} {'Occ Lift':<9}")
                print("─" * 60)

                for res in result['results']:
                    delta_str = "0.0%" if res['control'] else f"{res['delta']:+.1%}"
                    control_str = "YES" if res['control'] else "NO"
                    rev_psh = f"${res['rev_psh']:.2f}"
                    occupancy = f"{res['occupancy']:.1%}"
                    rev_lift = f"{res['lift_rev_psh']:+.1%}" if not res['control'] else "-"
                    occ_lift = f"{res['lift_occupancy']:+.1%}" if not res['control'] else "-"

                    print(f"{delta_str:<8} {control_str:<7} {rev_psh:<8} {occupancy:<10} {rev_lift:<9} {occ_lift:<9}")

                # Summary insights
                non_control_results = [r for r in result['results'] if not r['control']]
                if non_control_results:
                    best_rev_arm = max(non_control_results, key=lambda x: x['lift_rev_psh'])
                    best_occ_arm = max(non_control_results, key=lambda x: x['lift_occupancy'])

                    print(f"\n💡 Insights:")
                    print(f"   Best revenue lift: {best_rev_arm['delta']:+.1%} (+{best_rev_arm['lift_rev_psh']:.1%})")
                    print(f"   Best occupancy lift: {best_occ_arm['delta']:+.1%} (+{best_occ_arm['lift_occupancy']:.1%})")

                    # Check for statistical significance (simplified)
                    significant_arms = [r for r in non_control_results if abs(r['lift_rev_psh']) > 0.02]  # >2% change
                    if significant_arms:
                        print(f"   Significant arms (>2% revenue change): {len(significant_arms)}")
                    else:
                        print(f"   No statistically significant revenue changes detected")

            else:
                print("No results available yet.")

    except Exception as e:
        print(f"❌ Error evaluating experiment: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())