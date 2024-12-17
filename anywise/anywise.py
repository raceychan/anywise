from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MappingProxyType, MethodType
from typing import Any, Callable, Sequence, cast

from ididi import DependencyGraph

from ._itypes import CommandContext, EventContext, FuncMeta, IGuard
from ._registry import (
    GuardMapping,
    HandlerMapping,
    ListenerMapping,
    MessageRegistry,
    MethodMeta,
)
from .errors import UnregisteredMessageError

type AnyHandler[CTX] = "HandlerBase[Callable[[Any], Any] | Callable[[Any, CTX], Any]]"


class HandlerBase[HandlerType]:
    def __init__(
        self,
        *,
        anywise: "Anywise",
        handler: HandlerType,
        owner_type: type | None,
    ):
        self._anywise = anywise

        self._handler: HandlerType = handler
        self._owner_type = owner_type
        self._is_solved = False

    def __repr__(self):
        handler_repr = (
            f"{self._owner_type}: {self._handler}"
            if self._owner_type
            else {self._handler}
        )
        return f"{self.__class__.__name__}({handler_repr})"

    async def __call__(self, message: Any, context: Any) -> Any: ...
class Handler(HandlerBase[Callable[[Any], Any]]):
    async def __call__(self, message: Any, _: Any = None) -> Any:
        "For compatibility with ContextedHandler, we use `_` to receive context"
        if self._is_solved:
            return await self._handler(message)
        if self._owner_type:
            instance: Any = await self._anywise.resolve(self._owner_type)
            self._handler = MethodType(self._handler, instance)
        self._is_solved = True
        return await self._handler(message)


class ContextedHandler[Ctx](HandlerBase[Callable[[Any, Ctx], Any]]):
    async def __call__(self, message: Any, context: Ctx) -> Any:
        if self._is_solved:
            return await self._handler(message, context)
        if self._owner_type:
            instance: Any = await self._anywise.resolve(self._owner_type)
            self._handler = MethodType(self._handler, instance)
        self._is_solved = True
        return await self._handler(message, context)


def create_handler(anywise: "Anywise", meta: "FuncMeta[Any]"):
    raw_handler = meta.handler
    if not meta.is_async:
        raw_handler = partial(to_thread, cast(Any, raw_handler))

    if isinstance(meta, MethodMeta):
        owner_type = meta.owner_type
    else:
        owner_type = None
        raw_handler = anywise.entry(meta.message_type, raw_handler)

    handler = (
        ContextedHandler(
            anywise=anywise,
            handler=raw_handler,
            owner_type=owner_type,
        )
        if meta.is_contexted
        else Handler(
            anywise=anywise,
            handler=raw_handler,
            owner_type=owner_type,
        )
    )
    return handler


class Sender:
    _handlers: dict[
        type,
        AnyHandler[CommandContext] | IGuard,
    ]

    def __init__(self, anywise: "Anywise"):
        self._anywise = anywise
        self._handlers = {}
        self._guards: GuardMapping[Any] = defaultdict(list)

    def include(self, mapping: HandlerMapping[Any]) -> None:
        for msg_type, handler_meta in mapping.items():
            handler = create_handler(self._anywise, handler_meta)
            self._handlers[msg_type] = handler

    async def send(self, msg: Any, context: CommandContext) -> Any:
        try:
            worker = self._handlers[type(msg)]
        except KeyError:
            raise UnregisteredMessageError(msg)

        if isinstance(worker, Handler):
            return await worker(msg)
        else:
            return await worker(msg, context)

    def include_guards(self, message_guards: defaultdict[type, list[IGuard]]):
        """
        TODO: currently implementation has bug with include guards
        if user call include twice
        include guards will not work properly

        we should probably separate guards and handlers
        only combine them at runtime
        """
        # TODO: improve logic
        for guard_target, guards in message_guards.items():
            mapping: list[tuple[type, AnyHandler[CommandContext] | IGuard]] = []

            for command_type, handler in self._handlers.items():
                if guard_target in command_type.__mro__:
                    mapping.append((command_type, handler))

            if not mapping:
                continue

            for handler_cmd, handler in mapping:
                base = handler
                for guard in reversed(guards):
                    guard.chain_next(base)
                    base = guard
                self._handlers[handler_cmd] = base


class Publisher:
    _subscribers: defaultdict[type, list[AnyHandler[EventContext]]]

    def __init__(self, anywise: "Anywise"):
        self._anywise = anywise
        self._subscribers = defaultdict(list)

    def include(self, mapping: ListenerMapping[Any]) -> None:
        for msg_type, listener_metas in mapping.items():
            if msg_type not in self._subscribers:
                self._subscribers[msg_type] = list()
            workers = [(create_handler(self._anywise, meta)) for meta in listener_metas]
            self._subscribers[msg_type].extend(workers)

    async def publish(self, msg: Any, context: EventContext) -> None:
        subscribers = self._subscribers[type(msg)]

        for handler in subscribers:
            if isinstance(handler, Handler):
                await handler(msg)
            else:
                await handler(msg, context)


class Anywise:
    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
        sender_factory: type[Sender] = Sender,
        publisher_factory: type[Publisher] = Publisher,
    ):
        self._dg = dg or DependencyGraph()
        self._sender = sender_factory(self)
        self._publisher = publisher_factory(self)
        self._dg.register_dependent(self, self.__class__)

    def include(
        self,
        registries: Sequence[MessageRegistry],
    ):

        message_guards: GuardMapping[Any] = defaultdict(list)

        for msg_registry in registries:
            self._dg.merge(msg_registry.graph)
            self._sender.include(msg_registry.command_mapping)
            self._publisher.include(msg_registry.event_mapping)

            for cmd_type, guards in msg_registry.message_guards.items():
                if cmd_type not in message_guards:
                    message_guards[cmd_type] = guards
                else:
                    message_guards[cmd_type].extend(guards)

        self._sender.include_guards(message_guards)

        self._dg.static_resolve_all()

    async def resolve[T](self, dep_type: type[T]) -> T:
        return await self._dg.aresolve(dep_type)

    def entry(self, message_type: type, func: Callable[..., Any]):
        ignore = (message_type, "context")
        return self._dg.entry(ignore=ignore)(func)

    def scope(self, name: str):
        return self._dg.scope(name)

    async def send(self, msg: Any, context: CommandContext | None = None) -> Any:
        # TODO: iter through handlers of _sender, generate type stub file.
        context = context or {}
        res = await self._sender.send(msg, context)
        return res

    async def publish(self, msg: Any, context: EventContext | None = None) -> None:
        context = context or MappingProxyType[str, Any]({})
        await self._publisher.publish(msg, context)
