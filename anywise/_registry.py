import inspect
import sys
from collections import defaultdict
from types import UnionType
from typing import Any, Callable, Sequence, Union, get_args, get_origin, overload

from ididi import DependencyGraph, INode

from ._itypes import (
    MISSING,
    FuncMeta,
    GuardMapping,
    HandlerMapping,
    IGuard,
    ListenerMapping,
    Maybe,
    MethodMeta,
    Missed,
)
from ._visitor import Target, collect_handlers, collect_listeners
from .errors import MessageHandlerNotFoundError
from .guard import Guard, GuardFunc, PostHandle

# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """


class MessageRegistry[C, E]:
    @overload
    def __init__(
        self,
        *,
        command_base: type[C],
        event_base: type[E] = Missed,
        graph: Maybe[DependencyGraph] = MISSING,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        event_base: type[E],
        command_base: type[C] = Missed,
        graph: Maybe[DependencyGraph] = MISSING,
    ) -> None: ...

    def __init__(
        self,
        *,
        command_base: Maybe[type[C]] = MISSING,
        event_base: Maybe[type[E]] = MISSING,
        graph: Maybe[DependencyGraph] = MISSING,
    ):
        self._command_base = command_base
        self._event_base = event_base
        self._graph = graph or DependencyGraph()

        self.command_mapping: HandlerMapping[Any] = {}
        self.event_mapping: ListenerMapping[Any] = {}
        self.message_guards: GuardMapping[Any] = defaultdict(list)

    @overload
    def __call__[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def __call__[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def __call__[
        **P, R
    ](self, handler: type[R] | Callable[P, R]) -> type[R] | Callable[P, R]:
        return self.register(handler)

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    def factory[**P, R](self, factory: INode[P, R]) -> INode[P, R]:
        self._graph.node(factory)
        return factory

    def _register_commandhanlders(self, handler: Target):
        if not self._command_base:
            return

        try:
            command_mapping = collect_handlers(self._command_base, handler)
        except MessageHandlerNotFoundError:
            command_mapping = {}

        for msg_type, meta in command_mapping.items():
            if isinstance(meta, MethodMeta):
                self._graph.node(ignore=msg_type)(meta.owner_type)
            else:
                command_mapping[msg_type] = FuncMeta(
                    message_type=msg_type,
                    handler=meta.handler,
                    is_async=meta.is_async,
                    is_contexted=meta.is_contexted,
                )
        self.command_mapping.update(command_mapping)

    def _register_eventlisteners(self, listeners: Target):
        if not self._event_base:
            return

        try:
            event_mapping = collect_listeners(self._event_base, listeners)
        except MessageHandlerNotFoundError:
            event_mapping = {}

        for msg_type, metas in event_mapping.items():
            if msg_type not in self.event_mapping:
                self.event_mapping[msg_type] = list()
            for i, meta in enumerate(metas):
                if isinstance(meta, MethodMeta):
                    self._graph.node(ignore=msg_type)(meta.owner_type)
                else:
                    metas[i] = FuncMeta(
                        message_type=msg_type,
                        handler=meta.handler,
                        is_async=meta.is_async,
                        is_contexted=meta.is_contexted,
                    )
            self.event_mapping[msg_type].extend(metas)

    @overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    # accepts many handler
    def register(self, handler: Target):
        if self._command_base:
            try:
                command_mapping = collect_handlers(self._command_base, handler)
            except MessageHandlerNotFoundError:
                command_mapping = {}

            for msg_type, meta in command_mapping.items():
                if isinstance(meta, MethodMeta):
                    self._graph.node(ignore=msg_type)(meta.owner_type)
                else:
                    command_mapping[msg_type] = FuncMeta(
                        message_type=msg_type,
                        handler=meta.handler,
                        is_async=meta.is_async,
                        is_contexted=meta.is_contexted,
                    )
            self.command_mapping.update(command_mapping)

        self._register_eventlisteners(handler)
        return handler

    def extract_gurad_target(self, func: GuardFunc | PostHandle[Any]) -> Sequence[type]:
        func_params = list(inspect.signature(func).parameters.values())

        if sys.version_info >= (3, 10):
            union_meta = (UnionType, Union)
        else:
            union_meta = (Union,)

        if not func_params:
            return []

        cmd_param = func_params[0]

        cmd_type = cmd_param.annotation
        if get_origin(cmd_type) in union_meta:
            cmd_types = get_args(cmd_type)
        else:
            cmd_types = [cmd_type]

        return cmd_types

    def pre_handle(self, func: GuardFunc) -> GuardFunc:
        """
        TODO?: we should transform gurad into funcmeta
        """
        for cmdtype in self.extract_gurad_target(func):
            self.message_guards[cmdtype].append(Guard(pre_handle=func))
        return func

    def post_handle[R](self, func: PostHandle[R]) -> PostHandle[R]:
        for cmdtype in self.extract_gurad_target(func):
            self.message_guards[cmdtype].append(Guard(post_handle=func))
        return func

    def add_guard(self, targets: type[C] | Sequence[type[C]], guard: IGuard) -> IGuard:
        if not isinstance(targets, Sequence):
            targets = [targets]

        for target in targets:
            self.message_guards[target].append(guard)

        return guard
