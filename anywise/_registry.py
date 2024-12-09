import inspect
from collections import defaultdict
from typing import Callable, overload

from ididi import DependencyGraph, INode

from ._itypes import FuncMeta, HandlerMapping, ListenerMapping, MethodMeta
from ._visitor import Target, collect_handlers, collect_listeners
from .guard import Guard, GuardFunc, PostHandle

# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """
#     ...
# from functools import lru_cache


# @lru_cache
def handler_registry[C](msg_type: type[C]) -> "HandlerRegistry[C]":
    return HandlerRegistry[C](msg_type)


# @lru_cache
def listener_registry[E](msg_type: type[E]) -> "ListenerRegistry[E]":
    return ListenerRegistry[E](msg_type)


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

                    if meta.is_contexted:
                        ignore = (msg_type, "context")
                    else:
                        ignore = msg_type

                    entry = self._graph.entry(ignore=ignore)(listener)
                    metas[i] = FuncMeta(
                        message_type=msg_type,
                        handler=entry,
                        is_async=inspect.iscoroutinefunction(listener),
                        is_contexted=meta.is_contexted,
                    )
            self._mapping[msg_type].extend(metas)

        return handler


class HandlerRegistry[Command](RegistryBase[Command]):
    def __init__(self, message_type: type[Command]):
        super().__init__(message_type)
        self._mapping: HandlerMapping[Command] = {}

    def __iter__(self):
        items = self._mapping.items()
        for msg_type, funcmeta in items:
            yield (msg_type, funcmeta)

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
                    is_contexted=meta.is_contexted,
                )
        self._mapping.update(mappings)
        return handler


# class GuardRegistry[Command](RegistryBase[Command]):
#     def __init__(self, message_type: type[Command]):
#         super().__init__(message_type=message_type)
#         self._mapping: defaultdict[Command, list[GuardFunc]] = defaultdict(list)

#     def guard(self, message_type: type):
#         "like middleware in starlette"

#         """
#         register guard into guard registry
#         when included in anywise, match handler by command type
#         a guard of base command will be added to all handlers of subcommand, meaning

#         guard(UserCommand)

#         will be added to handle of CreateUser, UpdateUser, etc.


#         class AuthService:
#             @guard(UserCommand)
#             def validate_user(self, command: UserCommand, context: AuthContext):
#                 user = self._get_user(context.token.sub)
#                 if user.user_id != command.user_id:
#                     raise ValidationError
#                 context["user"] = user

#         @guard.pre_handle
#         def validate_user(self): ...


#         auth_guard = guard(AuthGuard, *arsg, **kwargs)
#         logging_guard = guard(LoggingGuard, *args, **kwargs)

#         auth_guard.bind([UserCommand, ProductCommand])
#         """

#     def pre_handler(self, func: GuardFunc):
#         self._mapping[self._message_type] = Guard(pre_handle=func)

#     def bind(self, message_type: type | list[type]):
#         """
#         which command this guard belongs to
#         """


class GuardRegistry:
    def __init__(self):
        # self._pre_handlers: defaultdict[type, list[GuardFunc]] = defaultdict(list)
        # self._post_hanlders: defaultdict[type, list[PostHandle]] = defaultdict(list)
        self._guards: defaultdict[type, list[Guard]] = defaultdict(list)
        self.graph = None

    def __iter__(self):
        mappings = self._guards.items()

        for msg_type, guards in mappings:
            yield (msg_type, guards)

    # def pre_handle(self, command_type: type):
    #     def receive(func: GuardFunc) -> GuardFunc:
    #         self._pre_handlers[command_type].append(func)
    #         return func

    #     return receive

    # def post_handle(self, command_type: type):
    #     def receive(func: PostHandle) -> PostHandle:
    #         self._post_hanlders[command_type].append(func)
    #         return func

    #     return receive

    def register(self, command_type: type):
        def receive(func: GuardFunc):
            self._guards[command_type].append(Guard(pre_handle=func))
            return func

        return receive
