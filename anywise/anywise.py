from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MappingProxyType, MethodType
from typing import Any, Awaitable, Callable, cast

from ididi import AsyncScope, DependencyGraph

from ._itypes import EventContext, FuncMeta, IContext, IGuard
from ._registry import (
    GuardMapping,
    HandlerMapping,
    ListenerMapping,
    MessageRegistry,
    MethodMeta,
)
from ._visitor import gather_commands
from .errors import UnregisteredMessageError

type EventListeners = list[Callable[[Any, Any], Any]]
type CommandHandler = Callable[[Any, IContext], Any] | IGuard
type SendStrategy = Callable[[Any, IContext, CommandHandler], Any]
type PublishStrategy = Callable[[Any, EventContext, EventListeners], Awaitable[None]]


async def default_send(
    message: Any, context: IContext, handler: Callable[[Any, IContext], Any]
) -> Any:
    return await handler(message, context)


async def default_publish(
    message: Any,
    context: EventContext,
    listeners: list[Callable[[Any, EventContext], Awaitable[None]]],
) -> None:
    for listener in listeners:
        await listener(message, context)


def context_wrapper(origin: Callable[[Any], Any]):
    async def inner(message: Any, _: Any):
        return await origin(message)

    return inner


class InjectMixin:
    def __init__(self, dg: DependencyGraph):
        self._dg = dg

    def entry(self, message_type: type, func: Callable[..., Any]):
        ignore = (message_type, "context")
        return self._dg.entry(ignore=ignore)(func)

    async def _resolve_meta(self, meta: "FuncMeta[Any]", *, scope: AsyncScope):
        handler = meta.handler

        if not meta.is_async:
            handler = partial(to_thread, cast(Any, handler))

        if isinstance(meta, MethodMeta):
            instance = await scope.resolve(meta.owner_type)
            handler = MethodType(handler, instance)
        else:
            handler = self.entry(meta.message_type, handler)

        if not meta.is_contexted:
            handler = context_wrapper(handler)
        return handler


class HandlerManager(InjectMixin):
    def __init__(self, dg: DependencyGraph):
        super().__init__(dg)
        self._handler_metas: dict[type, FuncMeta[Any]] = {}
        self._guard_mapping: GuardMapping = defaultdict(list)

        """
        TODO: collect global command guard
        self._global_guard: list[IGuard]

        @user_registry.pre_handle
        async def logging(command: Any, context: IContext) -> None:
        """

    def include_handlers(self, command_mapping: HandlerMapping[Any]):
        handler_mapping = {msg_type: meta for msg_type, meta in command_mapping.items()}
        self._handler_metas.update(handler_mapping)

    def include_guards(self, guard_mapping: GuardMapping):
        # gather commands
        for origin_target, guad_meta in guard_mapping.items():
            drived_target = gather_commands(origin_target)
            for target in drived_target:
                self._guard_mapping[target].extend(guad_meta)

    async def _chain_guards(
        self,
        msg_type: Any,
        handler: Callable[..., Any],
        *,
        scope: AsyncScope,
    ):

        metas = self._guard_mapping[msg_type]
        if not metas:
            return handler

        guards: list[IGuard] = [
            (
                await scope.resolve(meta.guard)
                if isinstance(meta.guard, type)
                else meta.guard
            )
            for meta in metas
        ]

        for i in range(len(guards) - 1):
            guards[i].chain_next(guards[i + 1])

        guards[-1].chain_next(handler)
        return guards[0]

    async def resolve_handler(self, msg_type: type, scope: AsyncScope):
        try:
            meta = self._handler_metas[msg_type]
        except KeyError:
            raise UnregisteredMessageError(msg_type)

        resolved_handler = await self._resolve_meta(meta, scope=scope)
        guarded_handler = await self._chain_guards(
            msg_type, resolved_handler, scope=scope
        )
        return guarded_handler


class ListenerManager(InjectMixin):
    def __init__(self, dg: DependencyGraph):
        super().__init__(dg)
        self._listener_metas: defaultdict[type, list[FuncMeta[Any]]] = defaultdict(list)

    def include_listeners(self, event_mapping: ListenerMapping[Any]):
        listener_mapping = {
            msg_type: [meta for meta in metas]
            for msg_type, metas in event_mapping.items()
        }
        for msg_type, metas in listener_mapping.items():
            self._listener_metas[msg_type].extend(metas)

    async def get_listener(
        self, msg_type: type, *, scope: AsyncScope
    ) -> EventListeners:
        try:
            listener_metas = self._listener_metas[msg_type]
        except KeyError:
            raise UnregisteredMessageError(msg_type)

        resolved_listeners = [
            await self._resolve_meta(meta, scope=scope) for meta in listener_metas
        ]
        return resolved_listeners


class Anywise(InjectMixin):
    """

    ## Args:

    - send_strategy: `Callable[[Any, MutableMapping[Any, Any], CommandHandler], Any]`

        ```py
        async def sender(msg: Any, context: CommandContext, handler: CommandHandler) -> Any:
            await handler(msg, context)
        ```

    - publish_strategy: `Callable[[Any, Mapping[Any, Any], EventListeners], Awaitable[None]]`

        ```py
        async def publisher(msg: Any, context: Mapping[Any, Any], listeners: EventListeners)->None:
            for listener in listeners:
                await listener(msg, context)
        ```
    """

    _sender: SendStrategy
    _publisher: PublishStrategy

    def __init__(
        self,
        *registries: MessageRegistry[Any, Any],
        dependency_graph: DependencyGraph | None = None,
        sender: SendStrategy = default_send,
        publisher: PublishStrategy = default_publish,
    ):
        dependency_graph = dependency_graph or DependencyGraph()
        super().__init__(dependency_graph)

        self._sender = sender
        self._publisher = publisher
        self._handler_manager = HandlerManager(self._dg)
        self._listener_manager = ListenerManager(self._dg)
        self._dg.register_dependent(self)

        self.include(*registries)

    def include(self, *registries: MessageRegistry[Any, Any]) -> None:
        for msg_registry in registries:
            self._dg.merge(msg_registry.graph)
            self._handler_manager.include_handlers(msg_registry.command_mapping)
            self._handler_manager.include_guards(msg_registry.guard_mapping)
            self._listener_manager.include_listeners(msg_registry.event_mapping)
        self._dg.static_resolve_all()

    def scope(self, name: str | None = None):
        return self._dg.scope(name)

    async def send(self, msg: object, *, context: IContext | None = None) -> Any:
        if context is None:
            context = {}
        scope_proxy = self._dg.use_scope(create_on_miss=True, as_async=True)

        async with scope_proxy as scope:
            handler = await self._handler_manager.resolve_handler(type(msg), scope)
            return await self._sender(msg, context, handler)

    async def publish(self, msg: object, context: EventContext | None = None) -> None:
        if context is None:
            context = MappingProxyType[str, Any]({})
        scope_proxy = self._dg.use_scope(create_on_miss=True, as_async=True)

        async with scope_proxy as scope:
            resolved_listeners = await self._listener_manager.get_listener(
                type(msg), scope=scope
            )
            return await self._publisher(msg, context, resolved_listeners)
