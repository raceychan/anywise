import typing as ty
from collections import defaultdict
from types import MethodType

from ididi import DependencyGraph

from ._itypes import CallableMeta
from ._registry import HandlerRegistry, ListenerRegistry, MethodMeta, RegistryBase

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

"""
class Sender: ...
class Publisher: ...
"""


class AnyWise:
    _handlers: dict[type, Worker[ty.Any]]
    _subscribes: defaultdict[type, list[Worker[ty.Any]]]

    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
    ):
        self._dg = dg or DependencyGraph()
        self._handlers = {}
        self._subscribes = defaultdict(list)
        self._dg.register_dependent(self, self.__class__)

    def _include_handlers(self, registry: HandlerRegistry[ty.Any]):
        for msg_type, handler_meta in registry:
            self._handlers[msg_type] = Worker[ty.Any](self, handler_meta)

    def _include_listeners(self, registry: ListenerRegistry[ty.Any]):
        for msg_type, listener_metas in registry:
            if msg_type not in self._subscribes:
                self._subscribes[msg_type] = list()
            workers = [Worker[ty.Any](self, meta) for meta in listener_metas]
            self._subscribes[msg_type].extend(workers)

    def include(
        self,
        registries: ty.Sequence[HandlerRegistry[ty.Any] | ListenerRegistry[ty.Any]],
    ):
        for registry in registries:
            self._dg.merge(registry.graph)
            if isinstance(registry, HandlerRegistry):
                self._include_handlers(registry)
            else:
                self._include_listeners(registry)
        self._dg.static_resolve_all()

    def resolve[T](self, dep_type: type[T]) -> T:
        return self._dg.resolve(dep_type)

    def send(self, msg: ty.Any) -> ty.Any:
        worker = self._handlers[type(msg)]
        return worker.handle(msg)

    def publish(self, msg: ty.Any) -> None:
        subscribers = self._subscribes[type(msg)]
        for sub in subscribers:
            sub.handle(msg)
