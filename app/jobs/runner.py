import asyncio
import traceback

from app.db.database import async_session


async def run_in_background(coro_factory, *args, **kwargs):
    async def _wrapper():
        async with async_session() as db:
            try:
                await coro_factory(db, *args, **kwargs)
            except Exception:
                traceback.print_exc()

    asyncio.create_task(_wrapper())
