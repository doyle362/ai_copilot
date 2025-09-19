#!/usr/bin/env python3
"""Test script to check recommendations directly from database"""

import asyncio
import os
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
        print("🔍 CHECKING CURRENT RECOMMENDATIONS IN DATABASE...")

        # Check existing recommendations
        existing_recs = await db.fetch(
            "SELECT id, zone_id, type, proposal::text, status, created_at FROM recommendations ORDER BY created_at DESC LIMIT 10"
        )

        print(f"📊 Found {len(existing_recs)} recommendations in database:")
        for rec in existing_recs:
            print(f"  - ID: {rec['id']}, Zone: {rec['zone_id']}, Type: {rec['type']}, Status: {rec['status']}")

        print("\n🎯 TESTING EXPERT RECOMMENDATION ENGINE...")

        # Test zone analytics
        expert_engine = ExpertRecommendationEngine(db)

        # Test with a known zone ID
        test_zone = "69720"
        print(f"🧪 Testing analytics for zone {test_zone}...")

        zone_stats = await expert_engine._get_zone_analytics(test_zone)
        if zone_stats:
            print(f"✅ Zone analytics successful: {zone_stats.keys()}")
            print(f"  - Total sessions: {zone_stats.get('total_sessions')}")
            print(f"  - Revenue per space hour: ${zone_stats.get('revenue_per_space_hour', 0):.2f}")
            print(f"  - Occupancy ratio: {zone_stats.get('occupancy_ratio', 0):.1%}")
        else:
            print(f"❌ No analytics data for zone {test_zone}")

        print("\n🚀 GENERATING ONE TEST RECOMMENDATION...")

        # Try to generate one recommendation
        test_zones = ["69720"]
        new_recs = await expert_engine.generate_recommendations_for_all_zones(test_zones)

        print(f"✅ Generated {len(new_recs)} new recommendations")
        for rec in new_recs:
            if rec:
                print(f"  - New recommendation: {rec.get('type')} for zone {rec.get('zone_id')}")

        # Check again after generation
        print("\n📊 CHECKING RECOMMENDATIONS AFTER GENERATION...")
        final_recs = await db.fetch(
            "SELECT id, zone_id, type, proposal::text, status, created_at FROM recommendations ORDER BY created_at DESC LIMIT 5"
        )

        print(f"📊 Total recommendations now: {len(final_recs)}")
        for rec in final_recs:
            print(f"  - ID: {rec['id']}, Zone: {rec['zone_id']}, Type: {rec['type']}, Status: {rec['status']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())