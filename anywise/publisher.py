from asyncio import TaskGroup
from typing import Any

from .anywise import AnyHandler, EventContext


async def concurrent_publish(
    msg: Any, context: EventContext, subscribers: list[AnyHandler[EventContext]]
) -> None:
    async with TaskGroup() as tg:
        for sub in subscribers:
            tg.create_task(sub(msg, context))
