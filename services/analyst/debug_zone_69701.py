#!/usr/bin/env python3
"""Debug script to analyze zone 69701 data accuracy"""

import asyncio
import sys
from pathlib import Path

# Add the analyst package to the path
sys.path.insert(0, str(Path(__file__).parent))

from analyst.db import Database
from analyst.core.expert_recommendation_engine import ExpertRecommendationEngine

async def main():
    # Set up database connection
    db = Database()
    await db.initialize()

    try:
        print("🔍 DETAILED ANALYSIS OF ZONE 69701...")

        # Check raw transaction data for zone 69701
        raw_data_query = """
            SELECT
                COUNT(*) as total_transactions,
                COUNT(DISTINCT start_park_date) as active_days,
                AVG(paid_minutes) as avg_duration_minutes,
                MIN(start_park_date) as first_date,
                MAX(start_park_date) as last_date,
                SUM(
                    CASE
                        WHEN parking_amount IS NOT NULL
                             AND parking_amount != ''
                             AND parking_amount != '-'
                             AND parking_amount != 'null'
                             AND parking_amount ~ '^[0-9]+\\.?[0-9]*$'
                        THEN parking_amount::NUMERIC
                        ELSE 0
                    END
                ) as total_revenue
            FROM historical_transactions
            WHERE zone = '69701'
        """

        raw_data = await db.fetchrow(raw_data_query)
        print(f"📊 RAW TRANSACTION DATA FOR ZONE 69701:")
        print(f"  - Total transactions: {raw_data['total_transactions']}")
        print(f"  - Active days: {raw_data['active_days']}")
        print(f"  - Date range: {raw_data['first_date']} to {raw_data['last_date']}")
        print(f"  - Average duration: {raw_data['avg_duration_minutes']:.1f} minutes")
        print(f"  - Total revenue: ${raw_data['total_revenue']:.2f}")

        if raw_data['active_days'] > 0:
            transactions_per_day = raw_data['total_transactions'] / raw_data['active_days']
            print(f"  - Transactions per day: {transactions_per_day:.1f}")

        print(f"\n🧮 CURRENT EXPERT ENGINE CALCULATIONS:")

        # Test the expert recommendation engine calculations
        expert_engine = ExpertRecommendationEngine(db)
        zone_stats = await expert_engine._get_zone_analytics('69701')

        if zone_stats:
            print(f"📊 EXPERT ENGINE ANALYTICS:")
            for key, value in zone_stats.items():
                if isinstance(value, float):
                    if 'ratio' in key or 'occupancy' in key:
                        print(f"  - {key}: {value:.1%}")
                    elif 'revenue' in key or 'session' in key:
                        print(f"  - {key}: {value:.2f}")
                    else:
                        print(f"  - {key}: {value:.1f}")
                else:
                    print(f"  - {key}: {value}")

            print(f"\n🧪 MANUAL OCCUPANCY CALCULATION CHECK:")
            print(f"Using your estimate: 40 spaces, ~10 transactions/day")

            # Manual calculation with user's estimates
            actual_spaces = 40  # User's estimate
            actual_transactions_per_day = 10  # User's estimate
            avg_duration_hours = (zone_stats.get('avg_session_duration_minutes', 0) or 0) / 60

            print(f"  - Estimated spaces: {actual_spaces}")
            print(f"  - Estimated transactions/day: {actual_transactions_per_day}")
            print(f"  - Average duration: {avg_duration_hours:.1f} hours")

            if avg_duration_hours > 0:
                # Total vehicle-hours per day
                total_vehicle_hours = actual_transactions_per_day * avg_duration_hours
                # Total available space-hours per day (assuming 12-hour operation)
                total_available_hours = actual_spaces * 12
                # Real occupancy
                real_occupancy = total_vehicle_hours / total_available_hours

                print(f"  - Total vehicle-hours/day: {total_vehicle_hours:.1f}")
                print(f"  - Total available space-hours/day: {total_available_hours:.1f}")
                print(f"  - REAL occupancy ratio: {real_occupancy:.1%}")

                print(f"\n🚨 COMPARISON:")
                print(f"  - Expert engine calculated: {zone_stats.get('occupancy_ratio', 0):.1%}")
                print(f"  - Reality-based estimate: {real_occupancy:.1%}")
                print(f"  - Difference: {abs(zone_stats.get('occupancy_ratio', 0) - real_occupancy):.1%}")

            print(f"\n🔍 INVESTIGATING THE CALCULATION ERROR...")

            # Check what the engine is using for space count
            engine_spaces = zone_stats.get('total_spaces', 100)
            engine_sessions_per_day = zone_stats.get('sessions_per_day', 0)
            engine_occupancy = zone_stats.get('occupancy_ratio', 0)

            print(f"  - Engine assumes {engine_spaces} spaces (likely wrong!)")
            print(f"  - Engine calculates {engine_sessions_per_day:.1f} sessions/day")
            print(f"  - Engine calculates {engine_occupancy:.1%} occupancy")

            print(f"\n💡 THE PROBLEM:")
            if engine_spaces != actual_spaces:
                print(f"  - The engine assumes {engine_spaces} spaces but zone has {actual_spaces}")
                print(f"  - This makes occupancy look artificially high")
                print(f"  - Need to get real space counts from zone configuration data")

        else:
            print(f"❌ No analytics data returned for zone 69701")

        # Check if there's zone capacity data anywhere
        print(f"\n🔍 LOOKING FOR ZONE CAPACITY DATA...")

        # Check for any tables that might contain zone capacity info
        capacity_tables = [
            "zones", "locations", "zone_config", "parking_zones",
            "zone_metadata", "site_config"
        ]

        for table in capacity_tables:
            try:
                check_query = f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_name = '{table}'
                    AND table_schema = 'public'
                """
                result = await db.fetchrow(check_query)
                if result:
                    print(f"  ✅ Found table: {table}")

                    # Try to get zone 69701 data from this table
                    try:
                        data_query = f"SELECT * FROM {table} WHERE zone_id = '69701' OR zone = '69701' OR id = '69701' LIMIT 1"
                        zone_data = await db.fetchrow(data_query)
                        if zone_data:
                            print(f"    - Data found: {dict(zone_data)}")
                    except Exception as e:
                        print(f"    - Could not query table: {e}")

            except Exception:
                continue

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())