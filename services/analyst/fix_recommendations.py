#!/usr/bin/env python3
"""Fix recommendations by generating for actual active zones"""

import asyncio
import sys
from pathlib import Path

# Add the analyst package to the path
sys.path.insert(0, str(Path(__file__).parent))

from analyst.db import Database
from analyst.core.expert_recommendation_engine import ExpertRecommendationEngine

async def main():
    # Set up database connection using environment
    db = Database()
    await db.initialize()

    try:
        print("🔧 FIXING RECOMMENDATIONS FOR ACTUAL ZONES...")

        # Get the top zones with transaction data
        zones_query = """
            SELECT DISTINCT zone, COUNT(*) as transaction_count
            FROM historical_transactions
            WHERE zone IS NOT NULL
            AND zone::text ~ '^[0-9]+$'  -- Only numeric zone IDs
            GROUP BY zone
            ORDER BY transaction_count DESC
            LIMIT 5
        """

        zones = await db.fetch(zones_query)
        print(f"📊 Top zones with transaction data:")

        active_zones = []
        for zone in zones:
            zone_id = str(zone['zone'])  # Convert to string
            count = zone['transaction_count']
            active_zones.append(zone_id)
            print(f"  - Zone {zone_id}: {count} transactions")

        print(f"\n🎯 GENERATING EXPERT RECOMMENDATIONS FOR ACTIVE ZONES...")

        # Generate expert recommendations for these zones
        expert_engine = ExpertRecommendationEngine(db)
        new_recs = await expert_engine.generate_recommendations_for_all_zones(active_zones)

        print(f"✅ Generated {len(new_recs)} new recommendations")
        for rec in new_recs:
            if rec:
                print(f"  - Zone: {rec.get('zone_id')}, Type: {rec.get('type')}")

        # Check final state
        print(f"\n📊 FINAL RECOMMENDATIONS STATE...")

        final_query = """
            SELECT zone_id, type, status, COUNT(*) as count
            FROM recommendations
            WHERE zone_id = ANY($1)
            GROUP BY zone_id, type, status
            ORDER BY zone_id, type
        """

        final_results = await db.fetch(final_query, active_zones)
        print(f"📊 Recommendations for active zones:")
        for result in final_results:
            print(f"  - Zone {result['zone_id']}: {result['count']} {result['type']} ({result['status']})")

        # Test the exact API query that would be used
        print(f"\n🧪 TESTING API QUERY FOR ACTIVE ZONES...")

        api_query = """
            SELECT id, zone_id, type, status, created_at
            FROM recommendations
            WHERE zone_id = ANY($1)
            ORDER BY created_at DESC
            LIMIT 10
        """

        api_results = await db.fetch(api_query, active_zones)
        print(f"✅ API query returned {len(api_results)} recommendations")

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