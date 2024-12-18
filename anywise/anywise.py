from asyncio import to_thread
from collections import defaultdict
from functools import lru_cache, partial
from types import MappingProxyType, MethodType
from typing import Any, Awaitable, Callable, cast

from ididi import DependencyGraph

from ._itypes import CommandContext, EventContext, FuncMeta, IGuard
from ._registry import (
    GuardMapping,
    HandlerMapping,
    ListenerMapping,
    MessageRegistry,
    MethodMeta,
)
from .errors import UnregisteredMessageError

type EventListeners = list[Callable[[Any, Any], Any]]
type CommandHandler = Callable[[Any, CommandContext], Any] | IGuard
type SendStrategy = Callable[[Any, CommandContext, CommandHandler], Any]
type PublishStrategy = Callable[[Any, EventContext, EventListeners], Awaitable[None]]


async def default_send(
    message: Any, context: CommandContext, handler: Callable[[Any, CommandContext], Any]
) -> Any:
    return await handler(message, context)


async def default_publish(
    message: Any,
    context: EventContext,
    listeners: list[Callable[[Any, EventContext], Awaitable[None]]],
) -> None:
    for listener in listeners:
        await listener(message, context)


def context_wrapper(origin: Callable[[Any], Any]):
    async def inner(message: Any, context: Any):
        return await origin(message)

    return inner


class InjectMixin:
    def __init__(self, dg: DependencyGraph):
        self._dg = dg

    def entry(self, message_type: type, func: Callable[..., Any]):
        ignore = (message_type, "context")
        return self._dg.entry(ignore=ignore)(func)

    async def _resolve_meta(self, meta: "FuncMeta[Any]"):
        handler = meta.handler

        if not meta.is_async:
            handler = partial(to_thread, cast(Any, handler))

        if isinstance(meta, MethodMeta):
            instance: Any = await self._dg.aresolve(meta.owner_type)
            handler = MethodType(handler, instance)
        else:
            handler = self.entry(meta.message_type, handler)

        if not meta.is_contexted:
            handler = context_wrapper(handler)

        return handler


class HandlerManager(InjectMixin):
    def __init__(self, dg: DependencyGraph):
        super().__init__(dg)
        self._handler_metas: dict[type, FuncMeta[Any]] = {}
        self._resolved_handler: dict[type, Callable[..., Any]] = {}
        self._guards: GuardMapping[Any] = defaultdict(list)

    def include_handlers(self, command_mapping: HandlerMapping[Any]):
        handler_mapping = {msg_type: meta for msg_type, meta in command_mapping.items()}
        self._handler_metas.update(handler_mapping)

    def include_guards(self, guard_mapping: GuardMapping[Any]):
        for target, guards in guard_mapping.items():
            self._guards[target].extend(guards)

    @lru_cache(maxsize=None)
    def _build_handler(self, msg_type: Any, handler: Callable[..., Any]):
        guards: list[IGuard] = []

        for guard in self._guards[msg_type]:
            guards.append(guard)

        if not guards:
            return handler

        for i in range(len(guards) - 1):
            guards[i].chain_next(guards[i + 1])

        guards[-1].chain_next(handler)
        return guards[0]

    async def get_handler(self, msg_type: type):
        if resolved_handler := self._resolved_handler.get(msg_type):
            return resolved_handler

        try:
            meta = self._handler_metas[msg_type]
        except KeyError:
            raise UnregisteredMessageError(msg_type)

        resolved_handler = await self._resolve_meta(meta)
        guarded_handler = self._build_handler(msg_type, resolved_handler)
        self._resolved_handler[msg_type] = guarded_handler
        return guarded_handler


class ListenerManager(InjectMixin):
    def __init__(self, dg: DependencyGraph):
        super().__init__(dg)
        self._listener_metas: defaultdict[type, list[FuncMeta[Any]]] = defaultdict(list)
        self._resolved_listeners: defaultdict[type, list[Callable[..., Any]]] = (
            defaultdict(list)
        )

    def include_listeners(self, event_mapping: ListenerMapping[Any]):
        listener_mapping = {
            msg_type: [meta for meta in metas]
            for msg_type, metas in event_mapping.items()
        }
        for msg_type, metas in listener_mapping.items():
            self._listener_metas[msg_type].extend(metas)

    async def get_listener(self, msg_type: type) -> EventListeners:
        if resolved_listeners := self._resolved_listeners.get(msg_type):
            return resolved_listeners

        try:
            listener_metas = self._listener_metas[msg_type]
        except KeyError:
            raise UnregisteredMessageError(msg_type)

        resolved_listeners = [await self._resolve_meta(meta) for meta in listener_metas]
        self._resolved_listeners[msg_type].extend(resolved_listeners)
        return resolved_listeners


class Anywise(InjectMixin):
    """
    send_strategy: SendingStrategy
    def _(msg: object, context: CommandContext, handler): ...

    publish_strategy: PublishingStrategy
    def _(msg: object, context: CommandContext, listeners): ...

    """

    _sender: SendStrategy
    _publisher: PublishStrategy

    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
        sender: SendStrategy | None = None,
        publisher: PublishStrategy | None = None,
    ):
        dg = dg or DependencyGraph()
        super().__init__(dg)
        self._sender = sender or default_send
        self._publisher = publisher or default_publish
        self._handler_manager = HandlerManager(self._dg)
        self._listener_manager = ListenerManager(self._dg)
        self._dg.register_dependent(self, self.__class__)

    def include(self, *registries: MessageRegistry[Any, Any]) -> None:
        for msg_registry in registries:
            self._dg.merge(msg_registry.graph)
            self._handler_manager.include_handlers(msg_registry.command_mapping)
            self._handler_manager.include_guards(msg_registry.message_guards)
            self._listener_manager.include_listeners(msg_registry.event_mapping)
        self._dg.static_resolve_all()

    def scope(self, name: str | None = None):
        return self._dg.scope(name)

    async def send(self, msg: object, context: CommandContext | None = None) -> Any:
        context = context or {}
        handler = await self._handler_manager.get_handler(type(msg))
        res = await self._sender(msg, context, handler)
        return res

    async def publish(self, msg: object, context: EventContext | None = None) -> None:
        context = context or MappingProxyType[str, Any]({})
        resolved_listeners = await self._listener_manager.get_listener(type(msg))
        await self._publisher(msg, context, resolved_listeners)
