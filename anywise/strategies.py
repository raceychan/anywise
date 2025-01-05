from asyncio import TaskGroup
from typing import Any

from .anywise import EventContext, EventListeners


async def concurrent_publish(
    msg: Any, context: EventContext | None, subscribers: EventListeners
) -> None:
    if not context:
        context = {}
    async with TaskGroup() as tg:
        for sub in subscribers:
            tg.create_task(sub(msg, context))
