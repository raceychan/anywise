import inspect
import sys
from collections import defaultdict
from functools import lru_cache
from types import UnionType
from typing import (
    Any,
    Callable,
    Iterator,
    Sequence,
    Union,
    get_args,
    get_origin,
    overload,
)

from ididi import DependencyGraph, INode

from ._itypes import FuncMeta, HandlerMapping, IGuard, ListenerMapping, MethodMeta
from ._visitor import Target, collect_handlers, collect_listeners
from .guard import Guard, GuardFunc, PostHandle

# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """


@lru_cache
def handler_registry[C](msg_type: type[C]) -> "HandlerRegistry[C]":
    return HandlerRegistry[C](msg_type)


@lru_cache
def listener_registry[E](msg_type: type[E]) -> "ListenerRegistry[E]":
    return ListenerRegistry[E](msg_type)


@overload
def make_registry[T](*, command_base: type[T]) -> "HandlerRegistry[T]": ...


@overload
def make_registry[T](*, event_base: type[T]) -> "ListenerRegistry[T]": ...


def make_registry[
    T
](
    *, command_base: type[T] | None = None, event_base: type[T] | None = None
) -> "HandlerRegistry[T] | ListenerRegistry[T]":
    if command_base:
        return HandlerRegistry(command_base)

    if event_base:
        return ListenerRegistry(event_base)

    raise Exception("Must provide either base command or base event")


class RegistryBase[Message]:
    def __init__(
        self, message_type: type[Message], *, graph: DependencyGraph | None = None
    ):
        self._message_type = message_type
        self._graph = graph or DependencyGraph()

    @property
    def graph(self) -> DependencyGraph:
        return self._graph

    def factory[**P, R](self, factory: INode[P, R]) -> INode[P, R]:
        self._graph.node(factory)
        return factory

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
        return iter(self._mapping.items())

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
                    metas[i] = FuncMeta(
                        message_type=msg_type,
                        handler=meta.handler,
                        is_async=meta.is_async,
                        is_contexted=meta.is_contexted,
                    )
            self._mapping[msg_type].extend(metas)
        return handler


class HandlerRegistry[Command](RegistryBase[Command]):
    def __init__(self, message_type: type[Command]):
        super().__init__(message_type)
        self._mapping: HandlerMapping[Command] = {}

    def __iter__(self):
        return iter(self._mapping.items())

    @overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @overload
    def register[**P, R](self, handler: Callable[P, R]) -> Callable[P, R]: ...

    def register(self, handler: Target):
        mappings = collect_handlers(self._message_type, handler)
        for msg_type, meta in mappings.items():
            if isinstance(meta, MethodMeta):
                self._graph.node(ignore=msg_type)(meta.owner_type)
            else:
                mappings[msg_type] = FuncMeta(
                    message_type=msg_type,
                    handler=meta.handler,
                    is_async=meta.is_async,
                    is_contexted=meta.is_contexted,
                )
        self._mapping.update(mappings)
        return handler


class GuardRegistry:
    """
    register guard into guard registry
    when included in anywise, match handler by command type
    a guard of base command will be added to all handlers of subcommand, meaning

    guard(UserCommand)

    will be added to handle of CreateUser, UpdateUser, etc.


    class AuthService:
        @guard(UserCommand)
        def validate_user(self, command: UserCommand, context: AuthContext):
            user = self._get_user(context.token.sub)
            if user.user_id != command.user_id:
                raise ValidationError
            context["user"] = user

    @guard.pre_handle
    def log_request(command, message): ...
    """

    def __init__(self):
        self._guards: defaultdict[type, list[IGuard]] = defaultdict(list)
        self._dg = DependencyGraph()

    def __iter__(self) -> Iterator[tuple[type, list[IGuard]]]:
        return iter(self._guards.items())

    @property
    def graph(self):
        return self._dg

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

    def pre_handle(self, func: GuardFunc):
        """
        TODO?: we should transform gurad into funcmeta
        """
        for cmdtype in self.extract_gurad_target(func):
            self._guards[cmdtype].append(Guard(pre_handle=func))
        return func

    def post_handle[R](self, func: PostHandle[R]) -> PostHandle[R]:
        for cmdtype in self.extract_gurad_target(func):
            self._guards[cmdtype].append(Guard(post_handle=func))
        return func

    def register(self, message_type: type, guard: IGuard) -> None:
        self._guards[message_type].append(guard)


class MessageRegistry:

    def __init__(self, command_base: type | None, event_base: type | None):
        self._command_base = command_base
        self._event_base = event_base

        self._message_guards: defaultdict[type, list[IGuard]] = defaultdict(list)

    def register(self): ...
