#!/usr/bin/env python3
import asyncio
import asyncpg
import os
import sys

async def test_connection():
    # Test with URL from env
    from analyst.config import settings

    print(f"Testing connection to: {settings.supabase_db_url}")

    try:
        conn = await asyncpg.connect(settings.supabase_db_url, server_settings={'jit': 'off'})
        print("✅ Connection successful!")

        # Test basic query
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query test: {result}")

        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)