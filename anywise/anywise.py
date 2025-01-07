from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MappingProxyType, MethodType
from typing import Any, Awaitable, Callable, cast
from weakref import ref

from ididi import AsyncScope, DependencyGraph

from ._itypes import (
    CommandHandler,
    EventListeners,
    FuncMeta,
    IContext,
    IEventContext,
    IGuard,
    MethodMeta,
    PublishStrategy,
    Registee,
    SendStrategy,
)
from ._registry import (
    GuardMapping,
    GuardMeta,
    HandlerMapping,
    ListenerMapping,
    MessageRegistry,
)
from .errors import UnregisteredMessageError
from .messages import IEvent
from .sink import IEventSink


async def default_send(
    message: Any, context: IContext | None, handler: Callable[[Any, IContext], Any]
) -> Any:
    if context is None:
        context = dict()
    return await handler(message, context)


async def default_publish(
    message: Any,
    context: IEventContext | None,
    listeners: list[Callable[[Any, IEventContext], Awaitable[None]]],
) -> None:
    if context is None:
        context = MappingProxyType({})

    for listener in listeners:
        await listener(message, context)


def context_wrapper(origin: Callable[[Any], Any]):
    async def inner(message: Any, _: Any):
        return await origin(message)

    return inner


class InjectMixin:
    def __init__(self, dg: DependencyGraph):
        self._dg = dg

    async def _resolve_meta(self, meta: "FuncMeta[Any]", *, scope: AsyncScope):
        handler = meta.handler

        if not meta.is_async:
            handler = partial(to_thread, cast(Any, handler))

        if isinstance(meta, MethodMeta):
            instance = await scope.resolve(meta.owner_type)
            handler = MethodType(handler, instance)
        else:
            handler = self._dg.entry(ignore=meta.ignore)(handler)

        if not meta.is_contexted:
            handler = context_wrapper(handler)
        return handler


class HandlerManager(InjectMixin):
    def __init__(self, dg: DependencyGraph):
        super().__init__(dg)
        self._handler_metas: dict[type, FuncMeta[Any]] = {}
        self._guard_mapping: GuardMapping = defaultdict(list)
        self._global_guard: list[GuardMeta] = []

    def include_handlers(self, command_mapping: HandlerMapping[Any]):
        handler_mapping = {msg_type: meta for msg_type, meta in command_mapping.items()}
        self._handler_metas.update(handler_mapping)

    def include_guards(self, guard_mapping: GuardMapping):
        for origin_target, guard_meta in guard_mapping.items():
            if origin_target is Any or origin_target is object:
                self._global_guard.extend(guard_meta)
            else:
                self._guard_mapping[origin_target].extend(guard_meta)

    async def _chain_guards(
        self,
        msg_type: Any,
        handler: Callable[..., Any],
        *,
        scope: AsyncScope,
    ) -> CommandHandler:
        command_guards = self._global_guard + self._guard_mapping[msg_type]
        if not command_guards:
            return handler

        guards: list[IGuard] = [
            (
                await scope.resolve(meta.guard)
                if isinstance(meta.guard, type)
                else meta.guard
            )
            for meta in command_guards
        ]

        head, *rest = guards
        ptr = head

        for nxt in rest:
            ptr.chain_next(nxt)
            ptr = nxt

        ptr.chain_next(handler)
        return head

    def get_handler(self, msg_type: type) -> CommandHandler | None:
        try:
            meta = self._handler_metas[msg_type]
        except KeyError:
            return None
        else:
            return meta.handler

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
        self._listener_metas: dict[type, list[FuncMeta[Any]]] = dict()

    def include_listeners(self, event_mapping: ListenerMapping[Any]):
        listener_mapping = {
            msg_type: [meta for meta in metas]
            for msg_type, metas in event_mapping.items()
        }
        for msg_type, metas in listener_mapping.items():
            if msg_type not in self._listener_metas:
                self._listener_metas[msg_type] = metas
            else:
                self._listener_metas[msg_type].extend(metas)

    def get_listeners(self, msg_type: type) -> EventListeners:
        try:
            listener_metas = self._listener_metas[msg_type]
        except KeyError:
            return []
        else:
            return [meta.handler for meta in listener_metas]

    async def resolve_listeners(
        self, msg_type: type, *, scope: AsyncScope
    ) -> EventListeners:
        try:
            listener_metas = self._listener_metas[msg_type]
        except KeyError:
            raise UnregisteredMessageError(msg_type)
        else:
            resolved_listeners = [
                await self._resolve_meta(meta, scope=scope) for meta in listener_metas
            ]
            return resolved_listeners


class Inspect:
    """
    a util class for inspecting anywise
    """

    def __init__(self, aw: "Anywise"):
        self._aw = ref(aw)

    def __getitem__(self, key: type) -> CommandHandler | EventListeners | None:
        aw = self._aw()

        if aw is None:
            raise Exception(f"{self.__class__.__name__} should not outlive anywise")

        if handler := aw.handler_manager.get_handler(key):
            return handler

        if listeners := aw.listener_manager.get_listeners(key):
            return listeners

    def guards(self, key: type):
        ...


class Anywise(InjectMixin):
    """

    - dependency_graph: `DependencyGraph`

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
        sink: IEventSink[IEvent] | None = None,
        sender: SendStrategy = default_send,
        publisher: PublishStrategy = default_publish,
    ):
        dependency_graph = dependency_graph or DependencyGraph()
        super().__init__(dependency_graph)
        self.handler_manager = HandlerManager(self._dg)
        self.listener_manager = ListenerManager(self._dg)

        self._sender = sender
        self._publisher = publisher
        self._sink = sink
        self._dg.register_singleton(self)

        self.include(*registries)

    # async def __enter__(self):
    #     """create an global scope and create resource"""
    #     # scope = self._dg.scope("anywise")

    # async def __aexit__(
    #     self,
    #     exc_type: type[Exception] | None,
    #     exc: Exception | None,
    #     exc_tb: Any | None,
    # ): ...

    def register(
        self, message_type: type | None = None, registee: Registee | None = None
    ) -> None:
        """
        register a function, a class, a module, or a package.

        anywise.register(create_user)
        anywise.register(UserCommand, UserService)
        anywise.register(UserCommand, user_service) # module / package

        NOTE: a package is a module with __path__ attribute
        """

    @property
    def inspect(self) -> Inspect:
        return Inspect(self)

    def register_singleton(self, singleton: Any):
        self._dg.register_singleton(singleton)

    def include(self, *registries: MessageRegistry[Any, Any]) -> None:
        for msg_registry in registries:
            self._dg.merge(msg_registry.graph)
            self.handler_manager.include_handlers(msg_registry.command_mapping)
            self.handler_manager.include_guards(msg_registry.guard_mapping)
            self.listener_manager.include_listeners(msg_registry.event_mapping)
        self._dg.static_resolve_all()

    def scope(self, name: str | None = None):
        return self._dg.scope(name)

    async def send(self, msg: object, *, context: IContext | None = None) -> Any:
        # TODO: msg, context, scope
        scope_proxy = self._dg.use_scope("message", create_on_miss=True, as_async=True)

        async with scope_proxy as scope:
            handler = await self.handler_manager.resolve_handler(type(msg), scope)
            return await self._sender(msg, context, handler)

    async def publish(
        self, msg: object, *, context: IEventContext | None = None
    ) -> None:
        scope_proxy = self._dg.use_scope("message", create_on_miss=True, as_async=True)

        async with scope_proxy as scope:
            resolved_listeners = await self.listener_manager.resolve_listeners(
                type(msg), scope=scope
            )
            return await self._publisher(msg, context, resolved_listeners)

    async def sink(self, event: Any):
        if self._sink is None:
            raise Exception("sink is not set")
        await self._sink.sink(event)


"""

def source_factory():
    anywise = Anywise()
    source = KafkaSource(
        anywise=anywise
    )


```bash
anywise main.source_factory
```
"""
