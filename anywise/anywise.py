from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MethodType
from typing import Any, Callable, Sequence, cast

from ididi import DependencyGraph

from ._itypes import CallableMeta
from ._registry import GuardRegistry, HandlerRegistry, ListenerRegistry, MethodMeta
from .guard import Guard

type ContextedHandler = Callable[[Any, dict[str, Any]], Any]


class HandlerBase[HandlerType]:
    def __init__(
        self,
        anywise: "AnyWise",
        handler: HandlerType,
        owner_type: type | None,
    ):
        self._anywise = anywise
        self._handler: HandlerType = handler
        self._owner_type = owner_type
        self._is_solved = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self._handler})"

    @classmethod
    def from_meta(cls, anywise: "AnyWise", meta: "CallableMeta[Any]"):
        handler = meta.handler
        if not meta.is_async:
            handler = partial(to_thread, cast(Any, handler))

        if isinstance(meta, MethodMeta):
            owner_type = meta.owner_type
        else:
            owner_type = None

        return cls(anywise, cast(HandlerType, handler), owner_type)


class Handler(HandlerBase[Callable[[Any], Any]]):
    async def __call__(self, message: Any) -> Any:
        if self._is_solved:
            return await self._handler(message)
        if self._owner_type:
            instance: Any = await self._anywise.resolve(self._owner_type)
            self._handler = MethodType(self._handler, instance)
        self._is_solved = True
        return await self._handler(message)


class ContextHandler(HandlerBase[ContextedHandler]):
    async def __call__(self, message: Any, context: dict[str, Any]) -> Any:
        if self._is_solved:
            return await self._handler(message, context)

        if self._owner_type:
            instance: Any = await self._anywise.resolve(self._owner_type)
            self._handler = MethodType(self._handler, instance)

        self._is_solved = True
        return await self._handler(message, context)


def create_handler(
    anywise: "AnyWise",
    meta: CallableMeta[Any],
) -> Handler | ContextHandler:
    if meta.is_contexted:
        return ContextHandler.from_meta(anywise=anywise, meta=meta)
    else:
        return Handler.from_meta(anywise, meta)


class Sender:
    _handlers: dict[type, Handler | ContextHandler | Guard]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._handlers = {}

    def include(self, registry: HandlerRegistry[Any]) -> None:
        for msg_type, handler_meta in registry:
            handler = create_handler(self._anywise, handler_meta)
            self._handlers[msg_type] = handler

    async def send(self, msg: Any) -> Any:
        worker = self._handlers[type(msg)]
        if isinstance(worker, (ContextHandler, Guard)):
            return await worker(msg, dict())
        else:
            return await worker(msg)

    def include_guards(self, guard_registry: GuardRegistry):
        for msg_type, guards in guard_registry:
            # TODO: look for msg_type.__mro__
            if not (handler := self._handlers.get(msg_type)):
                continue
            self._handlers[msg_type] = guard_registry.build_guard(msg_type, handler)


class Publisher:
    _subscribers: defaultdict[type, list[Handler | ContextHandler]]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._subscribers = defaultdict(list)

    def include(self, registry: ListenerRegistry[Any]) -> None:
        for msg_type, listener_metas in registry:
            if msg_type not in self._subscribers:
                self._subscribers[msg_type] = list()
            workers = [(create_handler(self._anywise, meta)) for meta in listener_metas]
            self._subscribers[msg_type].extend(workers)

    async def publish(self, msg: Any) -> None:
        subscribers = self._subscribers[type(msg)]
        context: dict[str, Any] = {}
        for sub in subscribers:
            if isinstance(sub, ContextHandler):
                await sub(msg, context)
            else:
                await sub(msg)


class AnyWise:
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
            if registry.graph:
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

    async def send(self, msg: Any) -> Any:
        return await self._sender.send(msg)

    async def publish(self, msg: Any) -> None:
        await self._publisher.publish(msg)
