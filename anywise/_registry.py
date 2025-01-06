import inspect
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Unpack, cast, overload

from ididi import DependencyGraph, INode, INodeConfig

from ._itypes import (
    MISSING,
    FuncMeta,
    HandlerMapping,
    IGuard,
    ListenerMapping,
    Maybe,
    MethodMeta,
    Missed,
)
from ._visitor import Target, gather_types
from .errors import (
    HandlerRegisterFailError,
    InvalidHandlerError,
    MessageHandlerNotFoundError,
    NotSupportedHandlerTypeError,
)
from .guard import Guard, GuardFunc, PostHandle

type GuardMapping = defaultdict[type, list[GuardMeta]]


def get_funcmetas(msg_base: type, func: Callable[..., Any]) -> list[FuncMeta[Any]]:
    params = inspect.Signature.from_callable(func).parameters.values()
    if not params:
        raise MessageHandlerNotFoundError(msg_base, func)

    msg, *rest = params
    is_async: bool = inspect.iscoroutinefunction(func)
    is_contexted: bool = bool(rest) and rest[0].name == "context"
    derived_msgtypes = gather_types(msg.annotation)

    for msg_type in derived_msgtypes:
        if not issubclass(msg_type, msg_base):
            raise InvalidHandlerError(msg_base, msg_type, func)

    metas = [
        FuncMeta[Any](
            message_type=t,
            handler=func,
            is_async=is_async,
            is_contexted=is_contexted,
            ignore=tuple(derived_msgtypes),
        )
        for t in derived_msgtypes
    ]
    return metas


def get_methodmetas(msg_base: type, cls: type) -> list[MethodMeta[Any]]:
    cls_members = inspect.getmembers(cls, predicate=inspect.isfunction)
    method_metas: list[MethodMeta[Any]] = []
    for name, func in cls_members:
        if name.startswith("_"):
            continue
        params = inspect.Signature.from_callable(func).parameters.values()
        if len(params) == 1:
            continue

        _, msg, *rest = params  # ignore `self`
        is_async: bool = inspect.iscoroutinefunction(func)
        is_contexted: bool = bool(rest) and rest[0].name == "context"
        derived_msgtypes = gather_types(msg.annotation)

        if not all(issubclass(msg_type, msg_base) for msg_type in derived_msgtypes):
            continue

        metas = [
            MethodMeta[Any](
                message_type=t,
                handler=func,
                is_async=is_async,
                is_contexted=is_contexted,
                ignore=tuple(derived_msgtypes),
                owner_type=cls,
            )
            for t in derived_msgtypes
        ]
        method_metas.extend(metas)

    if not method_metas:
        raise MessageHandlerNotFoundError(msg_base, cls)

    return method_metas


@dataclass(frozen=True, slots=True, kw_only=True)
class GuardMeta:
    guard_target: type
    guard: IGuard | type[IGuard]


# TODO: Guard Registry
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

        self.guard_mapping: GuardMapping = defaultdict(list)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(command_base={self._command_base}, event_base={self._event_base})"

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

    @overload
    def factory(self, **config: Unpack[INodeConfig]) -> INode[..., Any]: ...

    @overload
    def factory[
        **P, R
    ](self, factory: INode[P, R] | None = None, **config: Unpack[INodeConfig]) -> INode[
        P, R
    ]: ...

    def factory[
        **P, R
    ](self, factory: INode[P, R] | None = None, **config: Unpack[INodeConfig]) -> INode[
        P, R
    ]:
        if factory is None:
            return cast(INode[P, R], partial(self.factory, **config))

        self._graph.node(**config)(factory)
        return factory

    def _register_commandhanlders(self, handler: Target) -> None:
        if not self._command_base:
            return

        if inspect.isfunction(handler):
            metas = get_funcmetas(self._command_base, handler)
        elif inspect.isclass(handler):
            metas = get_methodmetas(self._command_base, handler)
        else:
            raise NotSupportedHandlerTypeError(handler)

        mapping = {meta.message_type: meta for meta in metas}
        self.command_mapping.update(mapping)

    def _register_eventlisteners(self, listener: Target) -> None:
        if not self._event_base:
            return

        if inspect.isfunction(listener):
            metas = get_funcmetas(self._event_base, listener)
        elif inspect.isclass(listener):
            metas = get_methodmetas(self._event_base, listener)
        else:
            raise NotSupportedHandlerTypeError(listener)

        for meta in metas:
            msg_type = meta.message_type
            if msg_type not in self.event_mapping:
                self.event_mapping[msg_type] = [meta]
            else:
                self.event_mapping[msg_type].append(meta)

    @overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def register(self, handler: Target):
        try:
            self._register_commandhanlders(handler)
        except HandlerRegisterFailError:
            self._register_eventlisteners(handler)
        return handler

    def register_all[
        **P, R
    ](
        self,
        *handlers: Callable[P, R],
        pre_hanldes: list[GuardFunc] | None = None,
        post_handles: list[PostHandle[R]] | None = None,
    ) -> None:
        for handler in handlers:
            self.register(handler)

        if pre_hanldes:
            for pre_handle in pre_hanldes:
                self.pre_handle(pre_handle)

        if post_handles:
            for post_handle in post_handles:
                self.post_handle(post_handle)

    # TODO? separate guard registry from message registry
    def _extra_guardfunc_annotation(self, func: Callable[..., Any]) -> type:
        if isinstance(func, type):
            f = func.__call__
            command_index = 1
        else:
            f = func
            command_index = 0

        func_params = list(inspect.signature(f).parameters.values())
        try:
            cmd_type = func_params[command_index].annotation
        except IndexError:
            raise Exception("can't extract command type from annotation")
        return cmd_type

    def pre_handle(self, func: GuardFunc) -> GuardFunc:
        target = self._extra_guardfunc_annotation(func)
        meta = GuardMeta(guard_target=target, guard=Guard(pre_handle=func))
        self.guard_mapping[meta.guard_target].append(meta)
        return func

    def post_handle[R](self, func: PostHandle[R]) -> PostHandle[R]:
        target = self._extra_guardfunc_annotation(func)
        meta = GuardMeta(guard_target=target, guard=Guard(post_handle=func))
        self.guard_mapping[meta.guard_target].append(meta)
        return func

    def add_guards(self, *guards: IGuard | type[IGuard]) -> None:
        for guard in guards:
            target = self._extra_guardfunc_annotation(guard)
            meta = GuardMeta(guard_target=target, guard=guard)
            self.guard_mapping[target].append(meta)

    # def guard[
    #     **P, R
    # ](self, func_or_cls: IGuard | type[IGuard]) -> IGuard | type[IGuard]:
    #     """
    #     @registry.guard
    #     async def guard_func(command: Command, context: IContext, next: GuardFunc):
    #         # do something before
    #         response = await next(command, context)
    #         # do something after

    #     @registry.guard
    #     class LoggingGuard(BaseGuard):
    #         async def __call__(self, command: Command, context: IContext):
    #             # do something before
    #             response = await self._next_guard
    #             # do something after
    #     """
