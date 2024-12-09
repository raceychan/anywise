import inspect
from typing import Any, Callable, overload

from ididi import DependencyGraph, INode

from ._itypes import FuncMeta, HandlerMapping, ListenerMapping, MethodMeta
from ._visitor import Target, collect_handlers, collect_listeners

# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """
#     ...


class RegistryBase[Message]:
    def __init__(
        self, message_type: type[Message], *, graph: DependencyGraph | None = None
    ):
        self._message_type = message_type
        if graph is None:
            graph = DependencyGraph()
        self._graph = graph

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    def factory[**P, R](self, factory: INode[P, R]) -> INode[P, R]:
        self._graph.node(factory)
        return factory

    def guard(self, func: Any):
        "like middleware in starlette"

    @overload
    def register[R](self, handler: type[R]) -> type[R]: ...

    @overload
    def register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def register[
        **P, R
    ](self, handler: type[R] | Callable[P, R]) -> type[R] | Callable[P, R]: ...

    @overload
    def __call__[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def __call__[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def __call__[
        **P, R
    ](self, handler: type[R] | Callable[P, R]) -> type[R] | Callable[P, R]:
        """
        register a class or a function
        """
        return self.register(handler)


class ListenerRegistry[Event](RegistryBase[Event]):
    def __init__(self, message_type: type[Event]):
        super().__init__(message_type)
        self._mapping: ListenerMapping[Event] = {}

    def __iter__(self):
        items = self._mapping.items()
        for msg_type, listener_metas in items:
            yield (msg_type, listener_metas)

    @overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def register[
        **P, R
    ](self, handler: type[R] | Callable[P, R]) -> type[R] | Callable[P, R]:
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
                    metas[i] = FuncMeta(
                        message_type=msg_type,
                        handler=entry,
                        is_async=inspect.iscoroutinefunction(listener),
                    )
            self._mapping[msg_type].extend(metas)

        return handler


class HandlerRegistry[Command](RegistryBase[Command]):
    def __init__(self, message_type: type[Command]):
        super().__init__(message_type)
        self._mapping: HandlerMapping[Command] = {}

    def __iter__(self):
        items = self._mapping.items()
        for msg_type, handler_meta in items:
            yield (msg_type, handler_meta)

    @overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def register(self, handler: Target):
        mappings = collect_handlers(self._message_type, handler)
        for msg_type, meta in mappings.items():
            f = meta.handler
            if isinstance(meta, MethodMeta):
                self._graph.node(ignore=msg_type)(meta.owner_type)
            else:
                entry = self._graph.entry(ignore=msg_type)(f)
                mappings[msg_type] = FuncMeta(
                    message_type=msg_type,
                    handler=entry,
                    is_async=inspect.iscoroutinefunction(f),
                )
        self._mapping.update(mappings)
        return handler


# from functools import lru_cache


# @lru_cache
def handler_registry[C](msg_type: type[C]) -> HandlerRegistry[C]:
    return HandlerRegistry[C](msg_type)


# @lru_cache
def listener_registry[E](msg_type: type[E]) -> ListenerRegistry[E]:
    return ListenerRegistry[E](msg_type)
