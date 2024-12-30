from collections import defaultdict
from typing import AsyncGenerator

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

from .model import IEvent
from .table import EventTable, event_to_mapping, mapping_to_event


class EventStore:
    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    async def add(self, event: IEvent):
        stmt = insert(EventTable).values(**event_to_mapping(event))
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def list_events(self, entity_id: str) -> list[IEvent]:
        stmt = select(EventTable).where(EventTable.entity_id == entity_id)
        async with self._engine.begin() as conn:
            cursor = await conn.execute(stmt)
            mappings = cursor.mappings().all()
            return [mapping_to_event(mapping) for mapping in mappings]

    async def list_all_events(self) -> AsyncGenerator[IEvent, None]:
        stmt = select(EventTable)
        async with self._engine.begin() as conn:
            cursor = await conn.stream(stmt)
            async for row in cursor.mappings():
                yield mapping_to_event(row)

    async def all_event_streams(self) -> AsyncGenerator[list[IEvent], None]:
        grouped = defaultdict[str, list[IEvent]](list)
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
    ) -> list[IEvent] | None:
        stmt = select(EventTable).where(
            EventTable.entity_id == entity_id and EventTable.version == version
        )
        async with self._engine.begin() as conn:
            cursor = await conn.execute(stmt)
            mapping = cursor.mappings().all()
            if not mapping:
                return None
            return [mapping_to_event(row) for row in mapping]
