import typing as ty
from asyncio import TaskGroup, to_thread
from collections import defaultdict
from functools import partial
from types import MethodType

from ididi import DependencyGraph

from ._itypes import CallableMeta
from ._registry import HandlerRegistry, ListenerRegistry, MethodMeta


class AsyncWorker[Message]:
    def __init__(
        self,
        anywise: "AnyWise",  # Message here should be a contravariant
        meta: CallableMeta[Message],
    ):
        self._anywise = anywise
        self._meta = meta
        self._is_async = self._meta.is_async
        self._handler: ty.Callable[[Message], ty.Any] | None = None

    # type Context = dict[str, Any]
    # handle(self, context: Context, msg: Message)
    async def handle(self, msg: Message) -> ty.Any:
        if self._handler:
            return await self._handler(msg)

        msg_handler = self._meta.handler

        if isinstance(self._meta, MethodMeta):
            instance: ty.Any = await self._anywise.resolve(self._meta.owner_type)
            self._handler = MethodType(msg_handler, instance)
        else:
            if self._is_async:
                self._handler = msg_handler
            else:
                self._handler = partial(to_thread, msg_handler)
        return await self._handler(msg)


class Sender:
    _handlers: dict[type, AsyncWorker[ty.Any]]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._handlers = {}

    def include(self, registry: HandlerRegistry[ty.Any]) -> None:
        for msg_type, handler_meta in registry:
            self._handlers[msg_type] = AsyncWorker[ty.Any](self._anywise, handler_meta)

    async def send(self, msg: ty.Any) -> ty.Any:
        worker = self._handlers[type(msg)]
        return await worker.handle(msg)


class Publisher:
    _subscribers: defaultdict[type, list[AsyncWorker[ty.Any]]]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._subscribers = defaultdict(list)

    def include(self, registry: ListenerRegistry[ty.Any]) -> None:
        for msg_type, listener_metas in registry:
            if msg_type not in self._subscribers:
                self._subscribers[msg_type] = list()
            workers = [
                (AsyncWorker[ty.Any](self._anywise, meta)) for meta in listener_metas
            ]
            self._subscribers[msg_type].extend(workers)

    async def publish(self, msg: ty.Any) -> None:
        subscribers = self._subscribers[type(msg)]
        for sub in subscribers:
            await sub.handle(msg)


class ConcurrentPublisher(Publisher):
    async def publish(self, msg: ty.Any) -> None:
        subscribers = self._subscribers[type(msg)]
        async with TaskGroup() as tg:
            [tg.create_task(sub.handle(msg)) for sub in subscribers]


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
        registries: ty.Sequence[HandlerRegistry[ty.Any] | ListenerRegistry[ty.Any]],
    ):
        for registry in registries:
            self._dg.merge(registry.graph)
            if isinstance(registry, HandlerRegistry):
                self._sender.include(registry)
            else:
                self._publisher.include(registry)
        self._dg.static_resolve_all()

    async def resolve[T](self, dep_type: type[T]) -> T:
        return await self._dg.aresolve(dep_type)

    async def send(self, msg: ty.Any) -> ty.Any:
        return await self._sender.send(msg)

    async def publish(self, msg: ty.Any) -> None:
        await self._publisher.publish(msg)
