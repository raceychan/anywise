import inspect
import typing as ty
from collections import defaultdict

from ._itypes import (
    CommandHandler,
    EventHandler,
    Handler,
    ICommand,
    IEvent,
    IQuery,
    Message,
    QueryHandler,
)


class MessageBus:
    command_handlers: dict[type[ICommand], CommandHandler[ty.Any]]
    query_handlers: dict[type[IQuery[ty.Any]], QueryHandler[ty.Any, ty.Any]]
    event_handlers: defaultdict[type[IEvent], list[EventHandler[ty.Any]]]

    def __init__(self):
        self.command_handlers = {}
        self.query_handlers = {}
        self.event_handlers = defaultdict(list)

    # def override[P, R](self, handler: Handler[P, R]) -> Handler[P, R]:
    #     msg_type = self._detect_message_type(handler)

    #     if issubclass(msg_type, ICommand):
    #         setattr(handler, "__overridden__", True)
    #         self.command_handlers[msg_type] = ty.cast(CommandHandler[P], handler)
    #     elif issubclass(msg_type, IQuery):
    #         setattr(handler, "__overridden__", True)
    #         self.query_handlers[msg_type] = ty.cast(QueryHandler[P, R], handler)
    #     else:
    #         for existing_handler in self.event_handlers[msg_type]:
    #             if getattr(existing_handler, "__overridden__", False) is False:
    #                 self.event_handlers[msg_type].remove(existing_handler)
    #                 setattr(handler, "__overridden__", True)
    #                 self.event_handlers[msg_type].append(
    #                     ty.cast(EventHandler[P], handler)
    #                 )
    #     return handler

    @ty.overload
    def register[P](self, handler: CommandHandler[P]) -> CommandHandler[P]: ...

    @ty.overload
    def register[P, R](self, handler: QueryHandler[P, R]) -> QueryHandler[P, R]: ...

    @ty.overload
    def register[P](self, handler: EventHandler[P]) -> EventHandler[P]: ...

    def register[P, R](self, handler: Handler[P, R]) -> Handler[P, R]:
        msg_type = self._detect_message_type(handler)
        if issubclass(msg_type, ICommand):
            existing_handler = self.command_handlers.get(msg_type, None)
            if not existing_handler:
                self.command_handlers[msg_type] = ty.cast(CommandHandler[P], handler)
            elif existing_handler is not handler:
                raise ValueError(
                    f"Handler for {msg_type} already registered, use `override` to replace"
                )
        elif issubclass(msg_type, IQuery):
            existing_handler = self.query_handlers.get(msg_type, None)
            if not existing_handler:
                self.query_handlers[msg_type] = ty.cast(QueryHandler[P, R], handler)
            elif existing_handler is not handler:
                raise ValueError(
                    f"Handler for {msg_type} already registered, use `override` to replace"
                )
        else:
            for existing_handler in self.event_handlers.get(msg_type, []):
                if existing_handler is handler:
                    return handler
            self.event_handlers[msg_type].append(ty.cast(EventHandler[P], handler))
        return handler

    def _detect_message_type[P, R](self, handler: Handler[P, R]) -> type[Message[R]]:
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())

        for p in params:
            annt = p.annotation
            if issubclass(annt, (ICommand, IQuery, IEvent)):
                return ty.cast(type[Message[R]], annt)
        else:
            raise ValueError(f"Handler {handler} does not return a Message")

    @ty.overload
    async def send[R](self, msg: IQuery[R]) -> R: ...

    @ty.overload
    async def send(self, msg: ICommand) -> None: ...

    @ty.overload
    async def send(self, msg: IEvent) -> None: ...

    async def send[R](self, msg: Message[R]) -> R | None:
        if isinstance(msg, IQuery):
            handler = ty.cast(QueryHandler[ty.Any, R], self.query_handlers[type(msg)])
            res = await handler(msg)
            return res
        elif isinstance(msg, ICommand):
            handler = ty.cast(
                CommandHandler[ICommand], self.command_handlers[type(msg)]
            )
            await handler(msg)
        else:
            handlers = ty.cast(
                list[EventHandler[IEvent]], self.event_handlers[type(msg)]
            )
            for handler in handlers:
                await handler(msg)

    """
    async def pipeline(self, behavior: ty.Callable[[Message, next], None]):
        # register behaviro
        return behavior
    """
