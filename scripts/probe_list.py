#!/usr/bin/env python3
"""
CLI script to list elasticity probe experiments.

Usage:
    python scripts/probe_list.py
    python scripts/probe_list.py --zone=z-110 --status=scheduled
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
from analyst.config import settings


async def main():
    parser = argparse.ArgumentParser(description='List elasticity probe experiments')
    parser.add_argument('--zone', help='Filter by zone ID')
    parser.add_argument('--status', choices=['scheduled', 'running', 'complete', 'aborted'], help='Filter by status')
    parser.add_argument('--limit', type=int, default=20, help='Maximum number of results (default: 20)')
    parser.add_argument('--format', choices=['json', 'table'], default='table', help='Output format')

    args = parser.parse_args()

    # Create user context (use dev zones for CLI)
    ctx = UserContext(
        sub="00000000-0000-0000-0000-000000000000",
        zone_ids=settings.dev_zone_ids_list,
        org_id=settings.org_id
    )

    try:
        # Initialize database
        await db.initialize()

        # Build query conditions
        conditions = []
        params = []
        param_idx = 1

        # Zone filter
        if args.zone:
            if args.zone not in ctx.zone_ids:
                print(f"❌ Zone {args.zone} not accessible", file=sys.stderr)
                sys.exit(1)
            conditions.append(f"e.zone_id = ${param_idx}")
            params.append(args.zone)
            param_idx += 1
        else:
            # Filter to accessible zones
            zone_placeholders = ", ".join([f"${i}" for i in range(param_idx, param_idx + len(ctx.zone_ids))])
            conditions.append(f"e.zone_id IN ({zone_placeholders})")
            params.extend(ctx.zone_ids)
            param_idx += len(ctx.zone_ids)

        # Status filter
        if args.status:
            conditions.append(f"e.status = ${param_idx}")
            params.append(args.status)
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
                COUNT(a.id) as arms_count,
                COUNT(r.experiment_id) as results_count
            FROM pricing_experiments e
            LEFT JOIN pricing_experiment_arms a ON e.id = a.experiment_id
            LEFT JOIN pricing_experiment_results r ON e.id = r.experiment_id
            {where_clause}
            GROUP BY e.id, e.zone_id, e.daypart, e.dow, e.status, e.created_at, e.ends_at
            ORDER BY e.created_at DESC
            LIMIT ${param_idx}
        """
        params.append(args.limit)

        rows = await db.pool.fetch(query, *params)

        if args.format == 'json':
            experiments = [
                {
                    "experiment_id": str(row['experiment_id']),
                    "zone_id": row['zone_id'],
                    "daypart": row['daypart'],
                    "dow": row['dow'],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat(),
                    "ends_at": row['ends_at'].isoformat() if row['ends_at'] else None,
                    "arms_count": row['arms_count'],
                    "results_count": row['results_count']
                }
                for row in rows
            ]
            print(json.dumps(experiments, indent=2))
        else:
            if not rows:
                print("No experiments found.")
                return

            print(f"📊 Found {len(rows)} experiment(s):\n")

            # Table header
            print(f"{'ID':<8} {'Zone':<8} {'Daypart':<8} {'DOW':<3} {'Status':<10} {'Arms':<5} {'Results':<7} {'Created':<19}")
            print("─" * 80)

            # Table rows
            for row in rows:
                exp_id = str(row['experiment_id'])[:8]
                created = row['created_at'].strftime('%Y-%m-%d %H:%M')
                results_str = str(row['results_count']) if row['results_count'] > 0 else "-"

                print(f"{exp_id:<8} {row['zone_id']:<8} {row['daypart']:<8} {row['dow']:<3} {row['status']:<10} {row['arms_count']:<5} {results_str:<7} {created:<19}")

    except Exception as e:
        print(f"❌ Error listing experiments: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())