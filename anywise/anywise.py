import typing as ty
from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MethodType

from ididi import DependencyGraph

from ._itypes import CallableMeta, ContextedHandler
from ._registry import GuardRegistry, HandlerRegistry, ListenerRegistry, MethodMeta
from .guard import Guard


class AsyncHandler:
    def __init__(
        self,
        anywise: "AnyWise",
        meta: CallableMeta[ty.Any],
    ):
        self._anywise = anywise
        self._meta = meta
        self._handler: ty.Callable[[ty.Any], ty.Any] = self._meta.handler
        self._is_async = self._meta.is_async
        self._is_contexted = self._meta.is_contexted
        self._is_solved = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self._handler})"

    async def __call__(self, message: ty.Any) -> ty.Any:
        if self._is_solved:
            return await self._handler(message)

        if isinstance(self._meta, MethodMeta):
            instance: ty.Any = await self._anywise.resolve(self._meta.owner_type)
            self._handler = MethodType(self._handler, instance)
        elif not self._is_async:
            self._handler = partial(to_thread, self._handler)

        self._is_solved = True
        return await self._handler(message)


class ContextHandler:

    def __init__(
        self,
        anywise: "AnyWise",
        meta: CallableMeta[ty.Any],
    ):
        self._anywise = anywise
        self._meta = meta
        self._handler: ContextedHandler = self._meta.handler
        self._is_async = self._meta.is_async
        self._is_solved: bool = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self._handler})"

    async def __call__(self, message: ty.Any, context: dict[str, ty.Any]) -> ty.Any:
        if self._is_solved:
            return await self._handler(message, context)

        if isinstance(self._meta, MethodMeta):
            instance: ty.Any = await self._anywise.resolve(self._meta.owner_type)
            self._handler = MethodType(self._handler, instance)
        elif not self._is_async:
            self._handler = partial(to_thread, self._handler)

        self._is_solved = True
        return await self._handler(message, context)


def create_handler(
    anywise: "AnyWise",
    meta: CallableMeta[ty.Any],
) -> AsyncHandler | ContextHandler:
    if meta.is_contexted:
        return ContextHandler(anywise=anywise, meta=meta)
    else:
        return AsyncHandler(anywise, meta)


class Sender:
    _handlers: dict[type, AsyncHandler | ContextHandler | Guard]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._handlers = {}

    def include(self, registry: HandlerRegistry[ty.Any]) -> None:
        for msg_type, handler_meta in registry:
            handler = create_handler(self._anywise, handler_meta)
            self._handlers[msg_type] = handler

    async def send(self, msg: ty.Any) -> ty.Any:
        worker = self._handlers[type(msg)]

        if isinstance(worker, (ContextHandler, Guard)):
            return await worker(msg, dict())
        else:
            return await worker(msg)

    def include_guards(self, registry: GuardRegistry):
        for msg_type, guards in registry:
            if not (handler := self._handlers.get(msg_type)):
                continue

            base = handler
            for guard in guards:
                guard.nxt = base
                base = guard

            self._handlers[msg_type] = base


class Publisher:
    _subscribers: defaultdict[type, list[AsyncHandler | ContextHandler]]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._subscribers = defaultdict(list)

    def include(self, registry: ListenerRegistry[ty.Any]) -> None:
        for msg_type, listener_metas in registry:
            if msg_type not in self._subscribers:
                self._subscribers[msg_type] = list()
            workers = [(create_handler(self._anywise, meta)) for meta in listener_metas]
            self._subscribers[msg_type].extend(workers)

    async def publish(self, msg: ty.Any) -> None:
        subscribers = self._subscribers[type(msg)]
        for sub in subscribers:
            if isinstance(sub, ContextHandler):
                await sub(msg, dict())
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
        registries: ty.Sequence[
            HandlerRegistry[ty.Any] | GuardRegistry | ListenerRegistry[ty.Any]
        ],
    ):
        for registry in registries:
            if registry.graph:
                self._dg.merge(registry.graph)
            if isinstance(registry, HandlerRegistry):
                self._sender.include(registry)
            elif isinstance(registry, GuardRegistry):
                self._sender.include_guards(registry)
            else:
                self._publisher.include(registry)
        self._dg.static_resolve_all()

    async def resolve[T](self, dep_type: type[T]) -> T:
        return await self._dg.aresolve(dep_type)

    async def send(self, msg: ty.Any) -> ty.Any:
        return await self._sender.send(msg)

    async def publish(self, msg: ty.Any) -> None:
        await self._publisher.publish(msg)
