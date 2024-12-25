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
            async for row in cursor.mappings():
                yield mapping_to_event(row)

    async def all_event_streams(self) -> AsyncGenerator[list[Event], None]:
        grouped = defaultdict[str, list[Event]](list)
        current_id: str = ""
        async for e in self.list_all_events():
            if current_id and current_id != e.entity_id:
                yield grouped[current_id]
                del grouped[current_id]  # Free memory for the yielded group
            current_id = e.entity_id
            grouped[e.entity_id].append(e)

        # Yield the final group after the loop
        if current_id:
            yield grouped[current_id]

    async def event_stream(
        self, entity_id: str, version: str = "1"
    ) -> list[Event] | None:
        stmt = select(Events).where(
            Events.entity_id == entity_id and Events.version == version
        )
        async with self._engine.begin() as conn:
            cursor = await conn.execute(stmt)
            mapping = cursor.mappings().all()
            if not mapping:
                return None
            return [mapping_to_event(row) for row in mapping]
