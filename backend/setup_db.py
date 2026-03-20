"""One-time database setup: create extensions and run initial migration."""

import asyncio
import sys

from sqlalchemy import text

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import engine


async def setup():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        print("PostgreSQL extensions created: pg_trgm, uuid-ossp")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup())
