#!/usr/bin/env python3
"""
CLI script to schedule elasticity probe experiments.

Usage:
    python scripts/probe_schedule.py z-110 evening 1 --deltas=-0.05,0.02,0.05 --horizon=14
"""
import asyncio
import argparse
import json
import sys
import os
from datetime import datetime

# Add services path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../services/analyst'))

from analyst.db import db
from analyst.deps.auth import UserContext
from analyst.core.elasticity_probe import schedule_probe
from analyst.config import settings


async def main():
    parser = argparse.ArgumentParser(description='Schedule elasticity probe experiment')
    parser.add_argument('zone_id', help='Zone ID (e.g., z-110)')
    parser.add_argument('daypart', choices=['morning', 'evening'], help='Time period')
    parser.add_argument('dow', type=int, choices=range(7), help='Day of week (0=Sunday, 6=Saturday)')
    parser.add_argument('--deltas', help='Comma-separated delta values (e.g., -0.05,0.02,0.05)')
    parser.add_argument('--horizon', type=int, default=14, help='Experiment duration in days (default: 14)')
    parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format')

    args = parser.parse_args()

    # Parse deltas
    deltas = []
    if args.deltas:
        try:
            deltas = [float(d.strip()) for d in args.deltas.split(',')]
        except ValueError as e:
            print(f"Error parsing deltas: {e}", file=sys.stderr)
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

        # Schedule the probe
        result = await schedule_probe(
            db=db.pool,
            ctx=ctx,
            zone_id=args.zone_id,
            daypart=args.daypart,
            dow=args.dow,
            deltas=deltas,
            horizon_days=args.horizon
        )

        if args.format == 'json':
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"✅ Elasticity probe scheduled successfully!")
            print(f"   Experiment ID: {result['experiment_id']}")
            print(f"   Zone: {args.zone_id}")
            print(f"   Daypart: {args.daypart}")
            print(f"   Day of week: {args.dow}")
            print(f"   Horizon: {args.horizon} days")
            print(f"   Ends at: {result['ends_at']}")
            print(f"   Arms: {len(result['arms'])}")

            if result['arms']:
                print("\n   Delta values:")
                for arm in result['arms']:
                    status = "CONTROL" if arm['control'] else f"{arm['delta']:+.1%}"
                    print(f"     • {status}")

    except Exception as e:
        print(f"❌ Error scheduling probe: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())