#!/usr/bin/env python3
import asyncio
import asyncpg

async def test_db():
    try:
        conn = await asyncpg.connect('postgres://ai_analyst_copilot:I%23K%26rzsO%2Acq%5E_P27HnkbZh%23DWomK9o%3DK@db.xzokblkebghmqargqgjb.supabase.co:5432/postgres')
        print("✅ Database connection successful!")
        version = await conn.fetchval("SELECT version()")
        print(f"Database version: {version}")
        await conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())