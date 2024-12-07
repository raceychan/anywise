import inspect
import typing as ty
from dataclasses import dataclass

from ididi import DependencyGraph, INode

type HandlerMapping[Command] = dict[
    type[Command], "FuncMeta[Command] | MethodMeta[Command]"
]

type ResolvedFunc[Command] = ty.Callable[[Command], ty.Any]

type AnyHandler[Owner, **P] = type[Owner] | ty.Callable[P, ty.Any] | ty.Callable[
    ty.Concatenate[Owner, P], ty.Any
]


# class Mark:
# def unpack[**P, R](self, msg: ty.Callable[P, R]):
#     # we can add dependencies types before P and after Owner
#     @ty.overload
#     def wrapper(func: ty.Callable[P, ty.Any]) -> ty.Callable[P, ty.Any]: ...

#     @ty.overload
#     def wrapper[
#         Owner
#     ](func: ty.Callable[ty.Concatenate[Owner, P], ty.Any]) -> ty.Callable[
#         ty.Concatenate[Owner, P], ty.Any
#     ]: ...

#     def wrapper[
#         Owner
#     ](
#         func: ty.Callable[P, ty.Any] | ty.Callable[ty.Concatenate[Owner, P], ty.Any]
#     ) -> (ty.Callable[P, ty.Any] | ty.Callable[ty.Concatenate[Owner, P], ty.Any]):

#         return func

#     return wrapper


@dataclass
class FuncMeta[Message]:
    """
    is_async: bool
    """

    message_type: type[Message]
    handler: ty.Callable[[Message], ty.Any]

    # owner_type: type[O] | None = None
    # contexted: bool = False

    # @property
    # def is_method(self) -> bool:
    # return self.owner_type is not None


@dataclass
class MethodMeta[Message](FuncMeta[Message]):
    owner_type: type


def extract_from_function[
    Message
](message_type: type[Message], handler: ty.Callable[..., ty.Any]) -> FuncMeta[Message]:
    sig = inspect.signature(handler)
    for param in sig.parameters.values():
        param_type = param.annotation
        if param_type is sig.empty:
            continue
        if inspect.isclass(param_type) and issubclass(param_type, message_type):
            return FuncMeta(param_type, handler)
    else:
        raise Exception(f"no subcommand found in {handler}")


def extract_from_class[
    Message
](message_type: type[Message], cls: type) -> HandlerMapping[Message]:
    handlers: HandlerMapping[Message] = {}
    for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if method_name.startswith("_"):
            continue

        sig = inspect.signature(method)
        for param in sig.parameters.values():

            param_type = param.annotation
            if param_type is sig.empty:
                continue

            if not issubclass(param_type, message_type):
                continue

            container = MethodMeta[Message](
                message_type=param_type,
                handler=method,
                owner_type=cls,
            )
            handlers[param_type] = container
    return handlers


def collect_handlers[
    Message
](message_type: type[Message], handler: AnyHandler[ty.Any, ...]) -> HandlerMapping[
    Message
]:
    handlers: HandlerMapping[Message] = {}
    if inspect.isfunction(handler):
        node = extract_from_function(message_type, handler)
        handlers[node.message_type] = node
        # config = INodeConfig(ignore=(node.message_type,))
    elif inspect.isclass(handler):
        methods = extract_from_class(message_type, handler)
        # config = INodeConfig(ignore=(node.message_type,))
        handlers.update(methods)
    else:
        raise Exception("Handler Not Supported")
    return handlers


class HandlerRegistry[Message]:
    "A pure container that collects handlers"

    _mark_registry: dict[type[Message], "HandlerRegistry[Message]"] = {}

    def __new__(cls, message: type[Message]):
        cls._mark_registry[message] = self = super().__new__(cls)
        return self

    def __init__(self, message: type[Message]):
        self.message_type = message
        self._handler_meta: HandlerMapping[Message] = {}
        self._graph = DependencyGraph()

    def __iter__(self):
        items = self._handler_meta.items()
        for msg, meta in items:
            yield (msg, meta)

    def guard(self, func: ty.Any):
        "like middleware in starlette"

    def factory[**P, R](self, factory: INode[P, R]) -> INode[P, R]:
        self._graph.node(factory)
        return factory

    @property
    def graph(self):
        return self._graph

    @ty.overload
    def register[T](self, handler: type[T]) -> type[T]: ...

    @ty.overload
    def register[
        T
    ](self, handler: ty.Callable[[T, ty.Any], ty.Any]) -> ty.Callable[
        [T, ty.Any], ty.Any
    ]: ...

    @ty.overload
    def register(
        self, handler: ty.Callable[[ty.Any], ty.Any]
    ) -> ty.Callable[[ty.Any], ty.Any]: ...

    def register[
        T
    ](
        self,
        handler: (
            type[T] | ty.Callable[[T, ty.Any], ty.Any] | ty.Callable[[ty.Any], ty.Any]
        ),
    ):

        mappings = collect_handlers(self.message_type, handler)
        for msg_type, handler_meta in mappings.items():
            f = handler_meta.handler
            if isinstance(handler_meta, MethodMeta):
                self._graph.node(ignore=msg_type)(handler_meta.owner_type)
            else:
                handler_meta.handler = self._graph.entry(ignore=msg_type)(f)

        self._handler_meta.update(mappings)
        return handler

    @classmethod
    def get_mark[
        M
    ](
        cls, msg_type: type[Message], default: M = None
    ) -> "HandlerRegistry[Message] | M ":
        return cls._mark_registry.get(msg_type, default)


@ty.overload
def mark[C](msg_type: type[C]) -> HandlerRegistry[C]: ...


@ty.overload
def mark[C, R](msg_type: type[C], rt: type[R]) -> HandlerRegistry[C]: ...


def mark[
    C, R
](msg_type: type[C], rt: type[R] | None = None) -> (
    HandlerRegistry[C] | HandlerRegistry[C]
):
    m = HandlerRegistry[C].get_mark(msg_type, HandlerRegistry[C](msg_type))
    return m
