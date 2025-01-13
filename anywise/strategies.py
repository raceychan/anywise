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
from typing import Any, Awaitable, Callable

from .Interface import EventListeners, IContext, IEventContext


async def default_send(
    message: Any, context: IContext | None, handler: Callable[[Any, IContext], Any]
) -> Any:
    if context is None:
        context = dict()
    return await handler(message, context)


async def default_publish(
    message: Any,
    context: IEventContext | None,
    listeners: list[Callable[[Any, IEventContext], Awaitable[None]]],
) -> None:
    if context is None:
        context = MappingProxyType({})

    for listener in listeners:
        await listener(message, context)


async def concurrent_publish(
    msg: Any, context: IEventContext | None, subscribers: EventListeners
) -> None:
    if not context:
        context = {}
    async with TaskGroup() as tg:
        for sub in subscribers:
            tg.create_task(sub(msg, context))
