import typing as ty
from collections import defaultdict
from types import MethodType

from ididi import DependencyGraph

from .mark import FuncMeta, HandlerRegistry, MethodMeta, ResolvedFunc

# async def ask(self, msg) -> R: ...


class Worker[Message]:
    def __init__(
        self,
        anywise: "AnyWise[Message]",
        handler_detail: FuncMeta[Message],
    ):
        self._anywise = anywise
        self._meta = handler_detail
        self._handler: ResolvedFunc[Message] | None = None

    def handle(self, msg: Message):
        if self._handler:
            return self._handler(msg)

        msg_handler = self._meta.handler

        if isinstance(self._meta, MethodMeta):
            instance: ty.Any = self._anywise.resolve(self._meta.owner_type)
            self._handler = MethodType(msg_handler, instance)
        else:
            self._handler = msg_handler
        return self._handler(msg)


class AnyWise[MessageType]:
    _handlers: dict[type, Worker[MessageType]]
    _subscribes: defaultdict[type, list[Worker[MessageType]]]

    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
    ):
        self._dg = dg or DependencyGraph()
        self._handlers = {}
        self._subscribes = defaultdict(list)
        self._dg.register_dependent(self, self.__class__)

    def merge_registries(self, registries: ty.Sequence[HandlerRegistry[MessageType]]):
        for registry in registries:
            self._dg.merge(registry.graph)
            for msg_type, handler_meta in registry:
                self._handlers[msg_type] = Worker[MessageType](self, handler_meta)
        self._dg.static_resolve_all()

    def resolve[T](self, dep_type: type[T]) -> T:
        return self._dg.resolve(dep_type)

    def send(self, msg: MessageType) -> None:
        worker = self._handlers[type(msg)]
        return worker.handle(msg)

    async def publish(self, msg: MessageType, concurrent: bool = False) -> None:
        """
        if concurrent
        """
        subscribers = self._subscribes[type(msg)]

        for sub in subscribers:
            await sub.handle(msg)
            # if event.to_sink:
            # await self._event_sink.write(event)
