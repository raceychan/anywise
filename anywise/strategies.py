from asyncio import TaskGroup
from typing import Any

from .anywise import EventListeners, IEventContext


async def concurrent_publish(
    msg: Any, context: IEventContext | None, subscribers: EventListeners
) -> None:
    if not context:
        context = {}
    async with TaskGroup() as tg:
        for sub in subscribers:
            tg.create_task(sub(msg, context))
