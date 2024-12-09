from asyncio import TaskGroup
from typing import Any

from .anywise import Publisher


class ConcurrentPublisher(Publisher):
    async def publish(self, msg: Any) -> None:
        subscribers = self._subscribers[type(msg)]
        async with TaskGroup() as tg:
            [tg.create_task(sub.handle(msg)) for sub in subscribers]
