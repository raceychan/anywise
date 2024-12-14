from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MappingProxyType, MethodType
from typing import Any, Callable, Sequence, cast

from ididi import DependencyGraph

from ._itypes import CallableMeta, IGuard
from ._registry import GuardRegistry, HandlerRegistry, ListenerRegistry, MethodMeta

type CommandContext = dict[str, Any]
type EventContext = MappingProxyType[str, Any]


class HandlerBase[HandlerType]:
    def __init__(
        self,
        *,
        anywise: "Anywise",
        handler: HandlerType,
        owner_type: type | None,
    ):
        self._anywise = anywise
        self._handler: HandlerType = handler
        self._owner_type = owner_type
        self._is_solved = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self._handler})"


class Handler(HandlerBase[Callable[[Any], Any]]):
    async def __call__(self, message: Any) -> Any:
        if self._is_solved:
            return await self._handler(message)
        if self._owner_type:
            instance: Any = await self._anywise.resolve(self._owner_type)
            self._handler = MethodType(self._handler, instance)
        self._is_solved = True
        return await self._handler(message)


class ContextedHandler[Ctx](HandlerBase[Callable[[Any, Ctx], Any]]):
    async def __call__(self, message: Any, context: Ctx) -> Any:
        if self._is_solved:
            return await self._handler(message, context)
        if self._owner_type:
            instance: Any = await self._anywise.resolve(self._owner_type)
            self._handler = MethodType(self._handler, instance)
        self._is_solved = True
        return await self._handler(message, context)


def create_handler(anywise: "Anywise", meta: "CallableMeta[Any]"):
    raw_handler = meta.handler
    if not meta.is_async:
        raw_handler = partial(to_thread, cast(Any, raw_handler))

    if isinstance(meta, MethodMeta):
        owner_type = meta.owner_type
    else:
        owner_type = None

    handler = (
        ContextedHandler(
            anywise=anywise,
            handler=raw_handler,
            owner_type=owner_type,
        )
        if meta.is_contexted
        else Handler(
            anywise=anywise,
            handler=raw_handler,
            owner_type=owner_type,
        )
    )
    return handler


class Sender:
    _handlers: dict[type, ContextedHandler[CommandContext] | Handler | IGuard]

    def __init__(self, anywise: "Anywise"):
        self._anywise = anywise
        self._handlers = {}

    def include(self, registry: HandlerRegistry[Any]) -> None:
        for msg_type, handler_meta in registry:
            handler = create_handler(self._anywise, handler_meta)
            self._handlers[msg_type] = handler

    async def send(self, msg: Any, context: dict[str, Any]) -> Any:
        worker = self._handlers[type(msg)]
        if isinstance(worker, Handler):
            return await worker(msg)
        else:
            return await worker(msg, context)

    def include_guards(self, guard_registry: GuardRegistry):
        for guard_target, guards in guard_registry:
            handlers: list[
                tuple[type, ContextedHandler[CommandContext] | Handler | IGuard]
            ] = []

            for command_type, handler in self._handlers.items():
                if guard_target in command_type.__mro__:
                    handlers.append((command_type, handler))

            if not handlers:
                continue

            for handler_cmd, handler in handlers:
                base = handler
                for guard in reversed(guards):
                    guard.chain_next(base)
                    base = guard
                self._handlers[handler_cmd] = base


class Publisher:
    _subscribers: defaultdict[type, list[Handler | ContextedHandler[EventContext]]]

    def __init__(self, anywise: "Anywise"):
        self._anywise = anywise
        self._subscribers = defaultdict(list)

    def include(self, registry: ListenerRegistry[Any]) -> None:
        for msg_type, listener_metas in registry:
            if msg_type not in self._subscribers:
                self._subscribers[msg_type] = list()
            workers = [(create_handler(self._anywise, meta)) for meta in listener_metas]
            self._subscribers[msg_type].extend(workers)

    async def publish(self, msg: Any, context: EventContext) -> None:
        subscribers = self._subscribers[type(msg)]

        for handler in subscribers:
            if isinstance(handler, ContextedHandler):
                await handler(msg, context)
            else:
                await handler(msg)


class Anywise:
    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
        sender_factory: type[Sender] = Sender,
        publisher_factory: type[Publisher] = Publisher,
    ):
        self._dg = dg or DependencyGraph()
        self._sender = sender_factory(self)
        self._publisher = publisher_factory(self)
        self._dg.register_dependent(self, self.__class__)

    def include(
        self,
        registries: Sequence[
            HandlerRegistry[Any] | GuardRegistry | ListenerRegistry[Any]
        ],
    ):
        guard_registries: list[GuardRegistry] = []

        for registry in registries:
            self._dg.merge(registry.graph)
            if isinstance(registry, HandlerRegistry):
                self._sender.include(registry)
            elif isinstance(registry, GuardRegistry):
                guard_registries.append(registry)
            else:
                self._publisher.include(registry)

        for guard_registry in guard_registries:
            self._sender.include_guards(guard_registry)

        self._dg.static_resolve_all()

    async def resolve[T](self, dep_type: type[T]) -> T:
        return await self._dg.aresolve(dep_type)

    async def send(self, msg: Any, context: CommandContext | None = None) -> Any:
        # TODO: iter through handlers of _sender, generate type stub file.
        context = context or {}
        return await self._sender.send(msg, context)

    async def publish(self, msg: Any, context: EventContext | None = None) -> None:
        context = context or MappingProxyType[str, Any]({})
        await self._publisher.publish(msg, context)
