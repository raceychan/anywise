from asyncio import to_thread
from collections import defaultdict
from functools import partial
from types import MethodType
from typing import Any, Callable, Sequence, cast
from weakref import ref

from ididi import AsyncScope, Graph

from ._ds import FuncMeta, GuardMeta, MethodMeta
from .errors import SinkUnsetError, UnregisteredMessageError
from .Interface import (
    CommandHandler,
    EventListeners,
    IContext,
    IEventContext,
    IGuard,
    PublishStrategy,
    Registee,
    SendStrategy,
)
from .messages import IEvent
from .registry import GuardMapping, HandlerMapping, ListenerMapping, MessageRegistry
from .sink import IEventSink
from .strategies import default_publish, default_send


def context_wrapper(origin: Callable[[Any], Any]):
    async def inner(message: Any, _: Any):
        return await origin(message)

    return inner


class ManagerBase:
    def __init__(self, dg: Graph):
        self._dg = dg

    async def _resolve_meta(self, meta: "FuncMeta[Any]", *, scope: AsyncScope):
        handler = meta.handler

        if not meta.is_async:
            # TODO: manage ThreadExecutor ourselves to allow config max worker
            # by default is min(32, cpu_cores + 4)
            handler = partial(to_thread, cast(Any, handler))

        if isinstance(meta, MethodMeta):
            instance = await scope.resolve(meta.owner_type)
            handler = MethodType(handler, instance)
        else:
            # TODO: EntryFunc
            handler = self._dg.entry(ignore=meta.ignore)(handler)

        if not meta.is_contexted:
            handler = context_wrapper(handler)
        return handler


class HandlerManager(ManagerBase):
    def __init__(self, dg: Graph):
        super().__init__(dg)
        self._handler_metas: dict[type, FuncMeta[Any]] = {}
        self._guard_mapping: GuardMapping = defaultdict(list)
        self._global_guards: list[GuardMeta] = []

    @property
    def global_guards(self):
        return self._global_guards[:]

    def include_handlers(self, command_mapping: HandlerMapping[Any]):
        handler_mapping = {msg_type: meta for msg_type, meta in command_mapping.items()}
        self._handler_metas.update(handler_mapping)

    def include_guards(self, guard_mapping: GuardMapping):
        for origin_target, guard_meta in guard_mapping.items():
            if origin_target is Any or origin_target is object:
                self._global_guards.extend(guard_meta)
            else:
                self._guard_mapping[origin_target].extend(guard_meta)

    async def _chain_guards[
        C
    ](
        self,
        msg_type: type[C],
        handler: Callable[..., Any],
        *,
        scope: AsyncScope,
    ) -> CommandHandler[C]:
        command_guards = self._global_guards + self._guard_mapping[msg_type]
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

    def get_handler[C](self, msg_type: type[C]) -> CommandHandler[C] | None:
        try:
            meta = self._handler_metas[msg_type]
        except KeyError:
            return None
        else:
            return meta.handler

    def get_guards(self, msg_type: type) -> list[IGuard | type[IGuard]]:
        return [meta.guard for meta in self._guard_mapping[msg_type]]

    async def resolve_handler[C](self, msg_type: type[C], scope: AsyncScope):
        try:
            meta = self._handler_metas[msg_type]
        except KeyError:
            raise UnregisteredMessageError(msg_type)

        resolved_handler = await self._resolve_meta(meta, scope=scope)
        guarded_handler = await self._chain_guards(
            msg_type, resolved_handler, scope=scope
        )
        return guarded_handler


class ListenerManager(ManagerBase):
    def __init__(self, dg: Graph):
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

    def get_listeners[E](self, msg_type: type[E]) -> EventListeners[E]:
        try:
            listener_metas = self._listener_metas[msg_type]
        except KeyError:
            return []
        else:
            return [meta.handler for meta in listener_metas]

    # def replace_listener(self, msg_type: type, old, new):
    #    idx = self._listener_metas[msg_type].index(old)
    #    self._listener_metas[msg_type][idx] = FuncMeta.from_handler(msg_type, new)

    async def resolve_listeners[
        E
    ](self, msg_type: type[E], *, scope: AsyncScope) -> EventListeners[E]:
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

    def __init__(
        self, handler_manager: HandlerManager, listener_manager: ListenerManager
    ):
        self._hm = ref(handler_manager)
        self._lm = ref(listener_manager)

    def listeners[E](self, key: type[E]) -> EventListeners[E] | None:
        if (lm := self._lm()) and (listeners := lm.get_listeners(key)):
            return listeners

    def handler[C](self, key: type[C]) -> CommandHandler[C] | None:
        if (hm := self._hm()) and (handler := hm.get_handler(key)):
            return handler

    def guards(self, key: type) -> Sequence[IGuard | type[IGuard]]:
        hm = self._hm()

        if hm is None:
            return []

        global_guards = [meta.guard for meta in hm.global_guards]
        command_guards = hm.get_guards(msg_type=key)
        return global_guards + command_guards


class Anywise:
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

    def __init__(
        self,
        *registries: MessageRegistry[Any, Any],
        graph: Graph | None = None,
        sink: IEventSink[IEvent] | None = None,
        sender: SendStrategy[Any] = default_send,
        publisher: PublishStrategy[IEvent] = default_publish,
    ):
        self._dg = graph or Graph()
        self._handler_manager = HandlerManager(self._dg)
        self._listener_manager = ListenerManager(self._dg)

        self._sender = sender
        self._publisher = publisher
        self._sink = sink

        self.include(*registries)
        self._dg.register_singleton(self)

    @property
    def sender(self) -> SendStrategy[Any]:
        return self._sender

    @property
    def publisher(self) -> PublishStrategy[IEvent]:
        return self._publisher

    @property
    def graph(self) -> Graph:
        return self._dg

    def reset_graph(self) -> None:
        self._dg.reset(clear_nodes=True)

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
        self, message_type: type | None = None, *registee: tuple[Registee, ...]
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
        return Inspect(
            handler_manager=self._handler_manager,
            listener_manager=self._listener_manager,
        )

    def include(self, *registries: MessageRegistry[Any, Any]) -> None:
        for msg_registry in registries:
            self._dg.merge(msg_registry.graph)
            self._handler_manager.include_handlers(msg_registry.command_mapping)
            self._handler_manager.include_guards(msg_registry.guard_mapping)
            self._listener_manager.include_listeners(msg_registry.event_mapping)
        self._dg.analyze_nodes()

    def scope(self, name: str | None = None):
        return self._dg.scope(name)

    async def send(
        self,
        msg: object,
        *,
        context: IContext | None = None,
        scope: AsyncScope | None = None,
    ) -> Any:
        if scope is None:
            scope = await self._dg.scope("message").__aenter__()

        handler = await self._handler_manager.resolve_handler(type(msg), scope)
        return await self._sender(msg, context, handler)

    async def publish(
        self,
        msg: IEvent,
        *,
        context: IEventContext | None = None,
        scope: AsyncScope | None = None,
    ) -> None:
        if scope is None:
            scope = await self._dg.scope("message").__aenter__()

        resolved_listeners = await self._listener_manager.resolve_listeners(
            type(msg), scope=scope
        )
        return await self._publisher(msg, context, resolved_listeners)

    # def add_task[
    #     **P, R
    # ](
    #     self,
    #     task_func: Callable[P, R] | Callable[P, Coroutine[None, None, R]],
    #     *args: P.args,
    #     **kwargs: P.kwargs,
    # ):
    #     # if kwargs:
    #     #     task_func = partial(task_func, **kwargs)

    #     if iscoroutinefunction(task_func):
    #         # self._tg.create_task
    #         t = create_task(task_func(*args, **kwargs))
    #         t.add_done_callback()

    #     # self.loop.call_soon(task_func, *args)

    async def sink(self, event: Any):
        try:
            await self._sink.sink(event)  # type: ignore
        except AttributeError:
            raise SinkUnsetError()
