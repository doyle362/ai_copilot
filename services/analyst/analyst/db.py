import asyncpg
import json
import logging
from typing import Optional, Dict, Any, List
from .config import settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        if not settings.supabase_db_url:
            raise ValueError("SUPABASE_DB_URL must be set")

        self._pool = await asyncpg.create_pool(
            settings.supabase_db_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")

    async def close(self):
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")

    async def execute(self, query: str, *args, **kwargs) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)

    async def fetch(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args, **kwargs)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *args, **kwargs)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args, **kwargs):
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)

    def transaction(self):
        return self._pool.acquire()

    async def set_jwt_claims(self, conn: asyncpg.Connection, claims: Dict[str, Any]):
        claims_json = json.dumps(claims)
        await conn.execute("SET LOCAL request.jwt.claims = $1", claims_json)


# Global database instance
db = Database()


async def get_db():
    return db