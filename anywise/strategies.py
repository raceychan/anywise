"""
- send_strategy: `Callable[[Any, MutableMapping[Any, Any], CommandHandler], Any]`

    ```py
    async def sender(msg: Any, context: dict[Any, Any], handler: CommandHandler) -> Any:
        await handler(msg, context)
    ```

- publish_strategy: `Callable[[Any, Mapping[Any, Any], EventListeners], Awaitable[None]]`

    ```py
    async def publisher(msg: Any, context: Mapping[Any, Any], listeners: EventListeners)->None:
        for listener in listeners:
            await listener(msg, context)
    ```
"""

from asyncio import TaskGroup
from types import MappingProxyType
from typing import Any

from .Interface import CommandHandler, EventListeners, IContext, IEventContext


async def default_send[
    C
](message: C, context: IContext | None, handler: CommandHandler[C]) -> Any:
    if context is None:
        context = dict()
    return await handler(message, context)


# TODO: dependency injection, maybe sink here?
async def default_publish[
    E
](message: E, context: IEventContext | None, listeners: EventListeners[E],) -> None:
    if context is None:
        context = MappingProxyType({})

    for listener in listeners:
        await listener(message, context)


async def concurrent_publish[
    E
](msg: E, context: IEventContext | None, subscribers: EventListeners[E]) -> None:
    if not context:
        context = {}
    async with TaskGroup() as tg:
        for sub in subscribers:
            tg.create_task(sub(msg, context))
