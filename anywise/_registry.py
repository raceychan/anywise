import inspect
from collections import defaultdict
from functools import partial
from typing import Any, Callable, Unpack, cast, overload

from ididi import DependencyGraph, INode, INodeConfig

from ._itypes import (
    CTX_MARKER,
    MISSING,
    Context,
    FrozenContext,
    FuncMeta,
    GuardMeta,
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
from .guard import BaseGuard, Guard, GuardFunc, PostHandle

type GuardMapping = defaultdict[type, list[GuardMeta]]


IGNORE_TYPES = (Context, FrozenContext)


def is_contextparam(param: list[inspect.Parameter]) -> bool:
    if not param:
        return False

    param_type = param[0].annotation

    v = getattr(param_type, "__value__", None)
    if not v:
        return False

    metas = getattr(v, "__metadata__", [])
    return CTX_MARKER in metas


def get_funcmetas(msg_base: type, func: Callable[..., Any]) -> list[FuncMeta[Any]]:
    params = inspect.Signature.from_callable(func).parameters.values()
    if not params:
        raise MessageHandlerNotFoundError(msg_base, func)

    msg, *rest = params
    is_async: bool = inspect.iscoroutinefunction(func)
    is_contexted: bool = is_contextparam(rest)
    derived_msgtypes = gather_types(msg.annotation)

    for msg_type in derived_msgtypes:
        if not issubclass(msg_type, msg_base):
            raise InvalidHandlerError(msg_base, msg_type, func)

    ignore = tuple(derived_msgtypes) + IGNORE_TYPES

    metas = [
        FuncMeta[Any](
            message_type=t,
            handler=func,
            is_async=is_async,
            is_contexted=is_contexted,
            ignore=ignore,  # type: ignore
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
        is_contexted: bool = is_contextparam(rest)
        derived_msgtypes = gather_types(msg.annotation)

        if not all(issubclass(msg_type, msg_base) for msg_type in derived_msgtypes):
            continue

        ignore = tuple(derived_msgtypes) + IGNORE_TYPES

        metas = [
            MethodMeta[Any](
                message_type=t,
                handler=func,
                is_async=is_async,
                is_contexted=is_contexted,
                ignore=ignore,  # type: ignore
                owner_type=cls,
            )
            for t in derived_msgtypes
        ]
        method_metas.extend(metas)

    if not method_metas:
        raise MessageHandlerNotFoundError(msg_base, cls)

    return method_metas


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
        return self._register(handler)

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
    def _register[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def _register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def _register(self, handler: Target):
        try:
            self._register_commandhanlders(handler)
        except HandlerRegisterFailError:
            self._register_eventlisteners(handler)
            return handler

        try:
            self._register_eventlisteners(handler)
        except HandlerRegisterFailError:
            pass
        return handler

    def register(
        self,
        *handlers: Callable[..., Any] | type[BaseGuard],
        pre_hanldes: list[GuardFunc] | None = None,
        post_handles: list[PostHandle[Any]] | None = None,
    ) -> None:
        for handler in handlers:
            if inspect.isclass(handler):
                if issubclass(handler, BaseGuard):
                    self.add_guards(handler)
                    continue
            self._register(handler)

        if pre_hanldes:
            for pre_handle in pre_hanldes:
                self.pre_handle(pre_handle)

        if post_handles:
            for post_handle in post_handles:
                self.post_handle(post_handle)

    # TODO? separate guard registry from message registry
    def get_guardtarget(self, func: Callable[..., Any]) -> set[type]:
        if inspect.isclass(func):
            func_params = list(inspect.signature(func.__call__).parameters.values())
            cmd_type = func_params[1].annotation
        elif inspect.isfunction(func):
            func_params = list(inspect.signature(func).parameters.values())
            cmd_type = func_params[0].annotation
        else:
            raise MessageHandlerNotFoundError(self._command_base, func)

        return gather_types(cmd_type)

    def pre_handle(self, func: GuardFunc) -> GuardFunc:
        targets = self.get_guardtarget(func)
        for target in targets:
            meta = GuardMeta(guard_target=target, guard=Guard(pre_handle=func))
            self.guard_mapping[target].append(meta)
        return func

    def post_handle[R](self, func: PostHandle[R]) -> PostHandle[R]:
        targets = self.get_guardtarget(func)
        for target in targets:
            meta = GuardMeta(guard_target=target, guard=Guard(post_handle=func))
            self.guard_mapping[target].append(meta)
        return func

    def add_guards(self, *guards: IGuard | type[IGuard]) -> None:
        for guard in guards:
            targets = self.get_guardtarget(guard)
            for target in targets:
                meta = GuardMeta(guard_target=target, guard=guard)
                self.guard_mapping[target].append(meta)
