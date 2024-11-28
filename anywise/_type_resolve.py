import inspect
import typing as ty
from collections import defaultdict

# from dataclasses import dataclass

# def resolve_from_module(module: types.ModuleType) -> Dict[Type[ICommand], IHandler]:
#     """Register all classes and functions in a module and return command-handler mapping."""
#     handlers: HandlersMap = {}
#     for _, obj in inspect.getmembers(module):
#         if inspect.isclass(obj) and not issubclass(obj, ICommand):
#             handlers.update(resolve_from_class(obj))
#         elif inspect.isfunction(obj):
#             result = resolve_from_function(obj)
#             if result:
#                 command_type, handler = result
#                 handlers[command_type] = handler
#     return handlers


type HandlerMapping[Command] = dict[type[Command], "HandlerNode"]
type FuncHandler[Command, R] = ty.Callable[[Command], R]
type MethodHandler[Command, Owner, R] = ty.Callable[[Owner, Command], R]
type AnyCallable = ty.Callable[..., ty.Any]


class HandlerNode:
    @ty.overload
    def __init__[C, R](self, command: type[C], handler: FuncHandler[C, R]) -> None: ...

    @ty.overload
    def __init__[
        C, O, R
    ](
        self, command: type[C], handler: MethodHandler[C, O, R], owner_type: type[O]
    ) -> None: ...

    def __init__[
        C, R, O
    ](
        self,
        command: type[C],
        handler: FuncHandler[C, R] | MethodHandler[C, O, R],
        owner_type: type[O] | ty.Literal[None] = None,
    ) -> None:
        self.command = command
        self.handler = handler
        self.owner_type = owner_type
        # TODO: resolved graph?


class Mark[Command]:
    _mark_registry: defaultdict[type[Command], list["Mark[ty.Any]"]] = defaultdict(list)

    def __init__(self, command: type[Command]):
        self._command = command
        self._handlers: HandlerMapping[Command] = {}
        self._mark_registry[command].append(self)

    def _extract_from_function(
        self, handler: ty.Callable[..., ty.Any], owner_type: type | None = None
    ) -> HandlerNode | None:
        sig = inspect.signature(handler)
        for param in sig.parameters.values():
            param_type = param.annotation
            if param_type is sig.empty:
                continue
            if issubclass(param_type, self._command):
                if owner_type:
                    return HandlerNode(param_type, handler, owner_type)
                return HandlerNode(param_type, handler)

    def _extract_from_class(self, cls: type) -> HandlerMapping[Command]:
        handlers: HandlerMapping[Command] = {}
        for _, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            sig = inspect.signature(method)
            for param in sig.parameters.values():
                param_type = param.annotation

                if param_type is sig.empty:
                    continue

                if not issubclass(param_type, self._command):
                    continue

                container = HandlerNode(
                    command=param_type,
                    handler=method,
                    owner_type=cls,
                )
                handlers[param_type] = container
        return handlers

    def _collect_handlers[
        **P, R
    ](self, handler: ty.Callable[P, R]) -> HandlerMapping[Command]:
        handlers: HandlerMapping[Command] = {}
        if inspect.isfunction(handler):
            cntner = self._extract_from_function(handler)
            if cntner:
                cmd = ty.cast(type[Command], cntner.command)
                handlers[cmd] = cntner
        elif inspect.isclass(handler):
            handlers.update(self._extract_from_class(handler))
        else:
            raise Exception("Not Supported")
        return handlers

    def register(self, handler: AnyCallable):
        handlers = self._collect_handlers(handler)
        self._handlers.update(handlers)
        return handler

    def unpack[**P, R](self, cmd: ty.Callable[P, R]):
        # TODO: support function unpack
        def wrapper[Owner](func: ty.Callable[ty.Concatenate[Owner, P], ty.Any]):
            return func

        return wrapper

    def __call__[
        T
    ](self, handler: type[T] | ty.Callable[[T, ty.Any], ty.Any],):
        return self.register(handler)

    def merge(self, other: "Mark[ty.Any]") -> HandlerMapping[ty.Any]:
        handler_map: HandlerMapping[ty.Any] = {}
        handler_map.update(other._handlers)
        return handler_map

    @classmethod
    def merge_all(cls):
        handler_map: HandlerMapping[ty.Any] = {}
        for _, ms in cls._mark_registry.items():
            for m in ms:
                handler_map.update(m._handlers)
        return handler_map


def mark[C](cmd_type: type[C]) -> Mark[C]:
    mark = Mark[C](cmd_type)
    return mark
