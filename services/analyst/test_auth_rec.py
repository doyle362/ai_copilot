#!/usr/bin/env python3
"""Test script to check authentication and recommendations"""

import asyncio
import sys
from pathlib import Path

# Add the analyst package to the path
sys.path.insert(0, str(Path(__file__).parent))

from analyst.db import Database

async def main():
    # Set up database connection using environment
    db = Database()
    await db.initialize()

    try:
        print("🔍 CHECKING RECOMMENDATIONS AND ZONE ACCESS...")

        # Check all recommendations with their zone IDs
        all_recs_query = """
            SELECT id, zone_id, type, status, created_at
            FROM recommendations
            ORDER BY created_at DESC
            LIMIT 20
        """

        all_recs = await db.fetch(all_recs_query)
        print(f"📊 All recommendations in database ({len(all_recs)}):")
        zone_counts = {}
        for rec in all_recs:
            zone_id = rec['zone_id']
            zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1
            print(f"  - Zone: {zone_id}, Type: {rec['type']}, Status: {rec['status']}, ID: {rec['id']}")

        print(f"\n📊 Recommendations by Zone:")
        for zone_id, count in zone_counts.items():
            print(f"  - Zone {zone_id}: {count} recommendations")

        # Check what zone IDs a typical user might have access to
        print(f"\n🔍 CHECKING HISTORICAL TRANSACTIONS FOR ZONE CONTEXT...")

        zones_query = """
            SELECT DISTINCT zone, COUNT(*) as transaction_count
            FROM historical_transactions
            WHERE zone IS NOT NULL
            GROUP BY zone
            ORDER BY transaction_count DESC
            LIMIT 10
        """

        zones = await db.fetch(zones_query)
        print(f"📊 Active zones from historical transactions:")
        for zone in zones:
            zone_id = zone['zone']
            count = zone['transaction_count']
            rec_count = zone_counts.get(zone_id, 0)
            print(f"  - Zone {zone_id}: {count} transactions, {rec_count} recommendations")

        # Test specific zone access
        print(f"\n🧪 TESTING API-COMPATIBLE RECOMMENDATION QUERY...")

        # Test with the most common zones
        test_zones = [zone['zone'] for zone in zones[:5]]  # Top 5 zones

        # Simulate the API query structure
        api_query = """
            SELECT id, location_id, zone_id, type,
                   CASE
                     WHEN proposal IS NOT NULL THEN proposal::jsonb
                     ELSE '{}'::jsonb
                   END as proposal,
                   rationale_text, expected_lift_json, confidence, requires_approval,
                   COALESCE(memory_ids_used, '{}') as memory_ids_used,
                   prompt_version_id, thread_id, status, created_at
            FROM recommendations
            WHERE zone_id = ANY($1)
            ORDER BY created_at DESC
            LIMIT 50
        """

        api_results = await db.fetch(api_query, test_zones)
        print(f"✅ API-compatible query returned {len(api_results)} recommendations")

        for rec in api_results:
            print(f"  - Zone: {rec['zone_id']}, Type: {rec['type']}, Status: {rec['status']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())