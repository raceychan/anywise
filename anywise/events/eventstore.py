from collections import defaultdict
from typing import AsyncGenerator

from ididi import use
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .model import Event
from .table import Events, event_to_mapping, mapping_to_event


def engine_factory() -> AsyncEngine:
    url = "sqlite+aiosqlite:///demo/db.db"
    return create_async_engine(url)


class EventStore:
    def __init__(self, engine: AsyncEngine = use(engine_factory)):
        self._engine = engine

    async def add(self, event: Event):
        stmt = insert(Events).values(**event_to_mapping(event))
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def list_all_events(self) -> AsyncGenerator[Event, None]:
        stmt = select(Events)
        async with self._engine.begin() as conn:
            cursor = await conn.stream(stmt)
            async for row in cursor:
                mapping = row._mapping
                yield mapping_to_event(mapping)

    async def event_streams(self) -> AsyncGenerator[list[Event], None]:
        grouped = defaultdict[str, list[Event]](list)
        current_id: str = ""
        async for e in self.list_all_events():
            if current_id and current_id != e.aggregate_id:
                yield grouped[current_id]
            current_id = e.aggregate_id
            grouped[e.aggregate_id].append(e)
