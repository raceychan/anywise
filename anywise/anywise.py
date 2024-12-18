from asyncio import to_thread
from collections import defaultdict
from functools import lru_cache, partial
from types import MappingProxyType, MethodType
from typing import Any, Awaitable, Callable, cast

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
type EventListeners = list[AnyHandler[EventContext]]
type CommandHandler = AnyHandler[CommandContext] | IGuard
type SendStrategy = Callable[[Any, CommandContext, CommandHandler], Any]
type PublishStrategy = Callable[[Any, EventContext, EventListeners], Awaitable[None]]


async def default_send(
    message: Any, context: CommandContext, handler: AnyHandler[CommandContext] | IGuard
) -> Any:
    return await handler(message, context)


async def default_publish(
    message: Any, context: EventContext, listeners: list[AnyHandler[EventContext]]
) -> Any:

    for listener in listeners:
        await listener(message, context)


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

    def update_handler(self, solved_obj: Any):
        """
        if handler._owner_type and not handler._solved:
            ...
        """
        self._handler = MethodType(self._handler, solved_obj)
        self._is_solved = True


class Anywise:
    """
    send_strategy: SendingStrategy
    def _(msg: object, context: CommandContext, handler): ...

    publish_strategy: PublishingStrategy
    def _(msg: object, context: CommandContext, listeners): ...

    """

    def __init__(
        self,
        *,
        dg: DependencyGraph | None = None,
        sender: SendStrategy | None = None,
        publisher: PublishStrategy | None = None,
    ):
        self._dg = dg or DependencyGraph()
        self._sender: SendStrategy = sender or default_send
        self._publisher: PublishStrategy = publisher or default_publish
        self._dg.register_dependent(self, self.__class__)

        """
        # TODO: don't let handlers depend on anywise
        self._resolved_hanlders: dict[type, Handler / ContextedHandler] = {}
        """

        self._handlers: dict[type, AnyHandler[CommandContext] | IGuard] = {}
        self._guards: GuardMapping[Any] = defaultdict(list)

        self._subscribers: defaultdict[type, list[AnyHandler[EventContext]]] = (
            defaultdict(list)
        )

    @lru_cache(maxsize=None)
    def _get_handler(self, msg_type: Any):
        handler = self._handlers[msg_type]

        guards: list[IGuard] = []
        """
        we don't need to look up msg_type.__mro__, 
        but instead, when we add guard in `MessageRegistry.extract_gurad_target`
        we lookthrough its subclass by command.__subclasses__()
        """

        for guard in self._guards[msg_type]:
            guards.append(guard)

        if not guards:
            return handler

        for i in range(len(guards) - 1):
            guards[i].chain_next(guards[i + 1])

        guards[-1].chain_next(handler)

        return guards[0]

    def _include_handlers(self, command_mapping: HandlerMapping[Any]):
        handler_mapping = {
            msg_type: self._create_handler(meta)
            for msg_type, meta in command_mapping.items()
        }
        self._handlers.update(handler_mapping)

    def _include_guards(self, guard_mapping: GuardMapping[Any]):
        for target, guards in guard_mapping.items():
            self._guards[target].extend(guards)

    def _include_listeners(self, event_mapping: ListenerMapping[Any]):
        listener_mapping = {
            msg_type: [(self._create_handler(meta)) for meta in metas]
            for msg_type, metas in event_mapping.items()
        }
        for msg_type, workers in listener_mapping.items():
            self._subscribers[msg_type].extend(workers)

    def _create_handler(self: "Anywise", meta: "FuncMeta[Any]"):
        raw_handler = meta.handler
        if not meta.is_async:
            raw_handler = partial(to_thread, cast(Any, raw_handler))

        if isinstance(meta, MethodMeta):
            owner_type = meta.owner_type
        else:
            owner_type = None
            # return EntryHandler
            raw_handler = self.entry(meta.message_type, raw_handler)

        handler = (
            ContextedHandler(
                anywise=self,
                handler=raw_handler,
                owner_type=owner_type,
            )
            if meta.is_contexted
            else Handler(
                anywise=self,
                handler=raw_handler,
                owner_type=owner_type,
            )
        )
        return handler

    def include(self, *registries: MessageRegistry[Any, Any]) -> None:
        for msg_registry in registries:
            self._dg.merge(msg_registry.graph)
            self._include_handlers(msg_registry.command_mapping)
            self._include_listeners(msg_registry.event_mapping)
            self._include_guards(msg_registry.message_guards)

        self._dg.static_resolve_all()

    async def resolve[T](self, dep_type: type[T]) -> T:
        return await self._dg.aresolve(dep_type)

    def entry(self, message_type: type, func: Callable[..., Any]):
        ignore = (message_type, "context")
        return self._dg.entry(ignore=ignore)(func)

    def scope(self, name: str | None = None):
        return self._dg.scope(name)

    async def send(self, msg: Any, context: CommandContext | None = None) -> Any:
        # TODO: iter through handlers of _sender, generate type stub file.
        context = context or {}

        try:
            handler = self._get_handler(type(msg))
        except KeyError:
            raise UnregisteredMessageError(msg)

        res = await self._sender(msg, context, handler)
        return res

    async def publish(self, msg: Any, context: EventContext | None = None) -> None:
        context = context or MappingProxyType[str, Any]({})
        await self._publisher(msg, context, self._subscribers[type(msg)])
