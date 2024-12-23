import inspect
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Literal, Sequence, Unpack, cast, overload

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
from ._visitor import Target, collect_handlers, collect_listeners
from .errors import MessageHandlerNotFoundError
from .guard import Guard, GuardFunc, PostHandle

type GuardType = Literal["pre_handle", "post_handle", "both"]
type GuardMapping = defaultdict[type, list[GuardMeta]]


@dataclass(frozen=True, slots=True, kw_only=True)
class GuardMeta:
    guard_target: type
    guard: IGuard | type[IGuard]


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

    def register(self, handler: Target):
        """
        a helper function to register a function handler, or method handlers within a class.

        Usage
        ---

        - register a class, method with subclass of command_base type will be registered

        ```py
        registry=MessageRegistry(command_base=Command, event_base=Event)

        @registry
        class UserService:
            async def signup(self, command: CreateUser)
        ```

        - register a function, it should declear which command it handles in its signature.

        ```py
        @register
        async def signup_user(command: CreateUser): ...
        ```
        """
        self._register_commandhanlders(handler)
        self._register_eventlisteners(handler)
        return handler

    def register_all[**P, R](self, *handlers: Callable[P, R]) -> None:
        for handler in handlers:
            self.register(handler)

    def _extra_guardfunc_annotation(self, func: GuardFunc | PostHandle[Any]):
        func_params = list(inspect.signature(func).parameters.values())
        try:
            cmd_type = func_params[0].annotation
        except IndexError:
            raise Exception

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

    def add_guard(
        self, *guards: IGuard | type[IGuard], targets: Sequence[type[C]]
    ) -> None:
        for guard in guards:
            for target in targets:
                meta = GuardMeta(guard_target=target, guard=guard)
                self.guard_mapping[target].append(meta)

    # def guard_for(self, *commands: type[C]):
    #     def receiver[T: BaseGuard](cls: type[T]) -> type[T]:
    #         # TODO: resolve cls
    #         self.add_guard(commands, cls)
    #         return cls

    #     return receiver
