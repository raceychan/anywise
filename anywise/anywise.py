import typing as ty
from collections import defaultdict
from types import MethodType

from ididi import DependencyGraph

from ._itypes import CallableMeta
from ._registry import HandlerRegistry, ListenerRegistry, MethodMeta

# class WorkUnit[Context, Message]:
#     type Handler = ty.Callable[[Context, Message], Context]

#     def __init__(self, context: Context, message_type: type[Message], handler: Handler):
#         self.context = context
#         self.message_type = message_type
#         self.handler = handler


class Worker[Message]:
    def __init__(
        self,
        anywise: "AnyWise",  # Message here should be a contravariant
        meta: CallableMeta[Message],
    ):
        self._anywise = anywise
        self._meta = meta
        self._handler: ty.Callable[[Message], ty.Any] | None = None

    # type Context = dict[str, Any]
    # handle(self, context: Context, msg: Message)
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


# class AsyncWorker:
# ...


# class AsyncWise[MessageType]:
#     ...


class Sender:
    _handlers: dict[type, Worker[ty.Any]]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._handlers = {}

    def include(self, registry: HandlerRegistry[ty.Any]) -> None:
        for msg_type, handler_meta in registry:
            self._handlers[msg_type] = Worker[ty.Any](self._anywise, handler_meta)

    def send(self, msg: ty.Any) -> ty.Any:
        worker = self._handlers[type(msg)]
        return worker.handle(msg)


class Publisher:
    _subscribes: defaultdict[type, list[Worker[ty.Any]]]

    def __init__(self, anywise: "AnyWise"):
        self._anywise = anywise
        self._subscribes = defaultdict(list)

    def include(self, registry: ListenerRegistry[ty.Any]) -> None:
        for msg_type, listener_metas in registry:
            if msg_type not in self._subscribes:
                self._subscribes[msg_type] = list()
            workers = [Worker[ty.Any](self._anywise, meta) for meta in listener_metas]
            self._subscribes[msg_type].extend(workers)

    def publish(self, msg: ty.Any) -> None:
        subscribers = self._subscribes[type(msg)]
        for sub in subscribers:
            sub.handle(msg)


class AnyWise:

    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
        sender: Sender | None = None,
        publisher: Publisher | None = None,
    ):
        self._dg = dg or DependencyGraph()
        self._sender = sender or Sender(self)
        self._publisher = publisher or Publisher(self)
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

    def resolve[T](self, dep_type: type[T]) -> T:
        return self._dg.resolve(dep_type)

    def send(self, msg: ty.Any) -> ty.Any:
        return self._sender.send(msg)

    def publish(self, msg: ty.Any) -> None:
        self._publisher.publish(msg)
