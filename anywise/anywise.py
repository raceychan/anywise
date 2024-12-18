from asyncio import to_thread
from collections import defaultdict
from functools import lru_cache, partial
from types import MappingProxyType, MethodType
from typing import Any, Callable, Mapping, Sequence, cast

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


class Sender:
    _handlers: dict[type, AnyHandler[CommandContext] | IGuard]

    def __init__(self):
        self._handlers = {}
        self._guards: GuardMapping[Any] = defaultdict(list)

    def include_handlers(
        self, mapping: Mapping[type, AnyHandler[CommandContext] | IGuard]
    ) -> None:
        self._handlers.update(mapping)

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

    async def send(self, msg: object, context: CommandContext) -> Any:
        try:
            handler = self._get_handler(type(msg))
        except KeyError:
            raise UnregisteredMessageError(msg)

        if isinstance(handler, Handler):
            return await handler(msg)
        else:
            return await handler(msg, context)

    def include_guards(self, message_guards: defaultdict[type, list[IGuard]]):
        for target, guards in message_guards.items():
            self._guards[target].extend(guards)


class Publisher:
    _subscribers: defaultdict[type, list[AnyHandler[EventContext]]]

    def __init__(self):
        self._subscribers = defaultdict(list)

    def include_listeners(
        self, mapping: Mapping[type, Sequence[AnyHandler[EventContext]]]
    ) -> None:
        for msg_type, workers in mapping.items():
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
        sender: Sender | None = None,
        publisher: Publisher | None = None,
    ):
        self._dg = dg or DependencyGraph()
        self._sender = sender or Sender()
        self._publisher = publisher or Publisher()
        self._dg.register_dependent(self, self.__class__)

        """
        self._resolved_hanlders: dict[type, Handler / ContextedHandler] = {}
        """

    def _include_handlers(self, command_mapping: HandlerMapping[Any]):
        handler_mapping = {
            msg_type: self._create_handler(meta)
            for msg_type, meta in command_mapping.items()
        }
        self._sender.include_handlers(handler_mapping)

    def _include_guards(self, guard_mapping: GuardMapping[Any]):
        self._sender.include_guards(guard_mapping)

    def _include_listeners(self, event_mapping: ListenerMapping[Any]):
        listener_mapping = {
            msg_type: [(self._create_handler(meta)) for meta in metas]
            for msg_type, metas in event_mapping.items()
        }
        self._publisher.include_listeners(listener_mapping)

    def _create_handler(self: "Anywise", meta: "FuncMeta[Any]"):
        raw_handler = meta.handler
        if not meta.is_async:
            raw_handler = partial(to_thread, cast(Any, raw_handler))

        if isinstance(meta, MethodMeta):
            owner_type = meta.owner_type
        else:
            owner_type = None
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
        res = await self._sender.send(msg, context)
        return res

    async def publish(self, msg: Any, context: EventContext | None = None) -> None:
        context = context or MappingProxyType[str, Any]({})
        await self._publisher.publish(msg, context)
