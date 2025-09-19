import asyncio
import asyncpg
import os

async def get_all_zones():
    # Use the same connection string as the app
    db_url = "postgresql://postgres:%40Seasenor93@db.xzokblkebghmqargqgjb.supabase.co:5432/postgres?sslmode=require"

    try:
        conn = await asyncpg.connect(db_url)

        # Get all distinct zones
        zones = await conn.fetch("SELECT DISTINCT zone FROM historical_transactions WHERE zone IS NOT NULL ORDER BY zone;")

        print(f"Total zones found: {len(zones)}")
        print("All zones:")
        for zone in zones:
            print(f"  z-{zone['zone']}")

        # Get Friday evening data for all zones
        friday_data = await conn.fetch("""
            SELECT zone, COUNT(*) as session_count
            FROM historical_transactions
            WHERE zone IS NOT NULL
            AND EXTRACT(dow FROM start_park_date) = 5
            AND EXTRACT(hour FROM start_park_time) BETWEEN 17 AND 21
            GROUP BY zone
            ORDER BY zone;
        """)

        print(f"\nFriday evening sessions across all {len(friday_data)} zones:")
        total = 0
        for row in friday_data:
            print(f"  z-{row['zone']}: {row['session_count']} sessions")
            total += row['session_count']
        print(f"Total Friday evening sessions: {total}")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_all_zones())