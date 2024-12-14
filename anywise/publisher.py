from asyncio import TaskGroup
from typing import Any

from .anywise import EventContext, Handler, Publisher


class ConcurrentPublisher(Publisher):
    async def publish(self, msg: Any, context: EventContext) -> None:
        subscribers = self._subscribers[type(msg)]
        async with TaskGroup() as tg:
            for sub in subscribers:
                if isinstance(sub, Handler):
                    tg.create_task(sub(msg))
                else:
                    tg.create_task(sub(msg, context))
