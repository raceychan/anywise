import typing as ty

from ididi import DependencyGraph, INode

from ._itypes import FuncMeta, HandlerMapping, ListenerMapping, MethodMeta
from ._visitor import Target, collect_handlers, collect_listeners


class RegistryBase:
    def __init__(self, graph: DependencyGraph):
        self._graph = graph

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    def factory[**P, R](self, factory: INode[P, R]) -> INode[P, R]:
        self._graph.node(factory)
        return factory

    def guard(self, func: ty.Any):
        "like middleware in starlette"


class ListenerRegistry[Event](RegistryBase):
    def __init__(self, message_type: type[Event]):
        super().__init__(DependencyGraph())
        self._message_type = message_type
        self._mapping: ListenerMapping[Event] = {}

    def __iter__(self):
        items = self._mapping.items()
        for msg_type, listener_metas in items:
            yield (msg_type, listener_metas)

    def register(self, handler: Target):
        mappings = collect_listeners(self._message_type, handler)

        for msg_type, metas in mappings.items():
            if msg_type not in self._mapping:
                self._mapping[msg_type] = list()

            for i, meta in enumerate(metas):
                if isinstance(meta, MethodMeta):
                    self._graph.node(ignore=msg_type)(meta.owner_type)
                else:
                    listener = meta.handler
                    entry = self._graph.entry(ignore=msg_type)(listener)
                    metas[i] = FuncMeta(message_type=msg_type, handler=entry)
            self._mapping[msg_type].extend(metas)


class HandlerRegistry[Message](RegistryBase):
    "A pure container that collects handlers"

    def __init__(self, message_type: type[Message]):
        super().__init__(DependencyGraph())
        self._message_type = message_type
        self._mapping: HandlerMapping[Message] = {}

    def __iter__(self):
        items = self._mapping.items()
        for msg_type, handler_meta in items:
            yield (msg_type, handler_meta)

    @ty.overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @ty.overload
    def register[**P, R](self, handler: ty.Callable[P, R]) -> ty.Callable[P, R]: ...

    def register(self, handler: Target):
        mappings = collect_handlers(self._message_type, handler)
        for msg_type, meta in mappings.items():
            f = meta.handler
            if isinstance(meta, MethodMeta):
                self._graph.node(ignore=msg_type)(meta.owner_type)
            else:
                entry = self._graph.entry(ignore=msg_type)(f)
                mappings[msg_type] = FuncMeta(message_type=msg_type, handler=entry)
        self._mapping.update(mappings)
        return handler


# from functools import lru_cache


# @lru_cache
def command_registry[C](msg_type: type[C]) -> HandlerRegistry[C]:
    return HandlerRegistry[C](msg_type)


# @lru_cache
def event_registry[E](msg_type: type[E]) -> ListenerRegistry[E]:
    return ListenerRegistry[E](msg_type)
