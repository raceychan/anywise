import inspect
import typing as ty
from dataclasses import dataclass

from ididi import DependencyGraph

type HandlerMapping[Command] = dict[type[Command], "Container[Command, ty.Any, ty.Any]"]
type FuncHandler[Command, R] = ty.Callable[[Command], R]
type MethodHandler[Command, Owner, R] = ty.Callable[[Owner, Command], R]

type AnyHandler[Owner, **P, R] = type[Owner] | ty.Callable[P, R] | ty.Callable[
    ty.Concatenate[Owner, P], R
]


# TODO? Actor node

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
class Container[M, O, R]:
    """
    is_async: bool
    """

    message_type: type[M]
    handler: FuncHandler[M, R] | MethodHandler[M, O, R]
    owner_type: type[O] | None = None

    @ty.overload
    def __call__(self, obj: O, *, message: M) -> R: ...

    @ty.overload
    def __call__(self, *, message: M) -> R: ...

    def __call__(self, obj: O | None = None, *, message: M) -> R:
        # from types import MethodType
        # if not isinstance(handler, MethodType) and handler.owner_type:
        #     owner = self._graph.resolve(handler.owner_type)
        #     method = MethodType(handler, owner)
        #     self._handlers[type(command)] = handler = method
        # return handler(message=command)

        if self.owner_type:
            if obj is None:
                raise Exception(f"missing instance of {self.owner_type}")
            return ty.cast(MethodHandler[M, O, R], self.handler)(obj, message)
        else:
            return ty.cast(FuncHandler[M, R], self.handler)(message)


class Mark[Message, IReturn]:

    _mark_registry: dict[type[Message], "Mark[Message, ty.Any]"] = {}

    def __init__(self, message: type[Message]):
        self.message_type = message
        self._handlers: HandlerMapping[Message] = {}
        self._graph = DependencyGraph()

        # TODO: move this to __new__
        self._mark_registry[message] = self

    @property
    def duties(self):
        return self._handlers.keys()

    def guard(self, func: ty.Any):
        "like middleware in starlette"

    @property
    def graph(self):
        return self._graph

    def _extract_from_function(
        self, handler: ty.Callable[..., IReturn]
    ) -> Container[Message, ty.Any, IReturn]:
        sig = inspect.signature(handler)
        for param in sig.parameters.values():
            param_type = param.annotation
            if param_type is sig.empty:
                continue
            if issubclass(param_type, self.message_type):
                return Container(param_type, handler)
        else:
            raise Exception(f"no subcommand found in {handler}")

    def _extract_from_class(self, cls: type) -> HandlerMapping[Message]:
        handlers: HandlerMapping[Message] = {}
        for _, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            sig = inspect.signature(method)
            for param in sig.parameters.values():
                if param.name.startswith("_"):
                    continue

                param_type = param.annotation
                if param_type is sig.empty:
                    continue

                if not issubclass(param_type, self.message_type):
                    continue

                container = Container[Message, ty.Any, ty.Any](
                    message_type=param_type,
                    handler=method,
                    owner_type=cls,
                )
                handlers[param_type] = container
        return handlers

    # def _extract_from_module(self, mod: ...): ...

    def _collect_handlers[
        Owner, **P
    ](self, handler: AnyHandler[Owner, P, IReturn]) -> HandlerMapping[Message]:
        handlers: HandlerMapping[Message] = {}
        if inspect.isfunction(handler):
            node = self._extract_from_function(handler)
            handlers[node.message_type] = node
            # config = INodeConfig(ignore=(node.message_type,))
            self._graph.entry(handler)
        elif inspect.isclass(handler):
            methods = self._extract_from_class(handler)
            self._graph.node(handler)
            handlers.update(methods)
        else:
            raise Exception("Handler Not Supported")
        return handlers

    def register[Owner, **P](self, handler: AnyHandler[Owner, P, IReturn]):
        handlers = self._collect_handlers(handler)
        self._handlers.update(handlers)
        return handler

    def factory[T](self, handler: type[T]):
        self._graph.node(handler)
        return handler

    def dispatch(self, command: Message) -> IReturn:
        handler = self._handlers[type(command)]

        # TODO: let anywise resolve dependency

        if handler.owner_type:
            owner = self._graph.resolve(handler.owner_type)
            return handler(owner, message=command)
        return handler(message=command)

    def __call__[Owner, **P](self, handler: AnyHandler[Owner, P, IReturn]):
        return self.register(handler)

    def merge(self, other: "Mark[ty.Any, ty.Any]") -> HandlerMapping[ty.Any]:
        handler_map: HandlerMapping[ty.Any] = {}
        handler_map.update(other._handlers)
        return handler_map

    @classmethod
    def merge_all(cls):
        handler_map: HandlerMapping[ty.Any] = {}
        # merge graph as well
        for _, m in cls._mark_registry.items():
            handler_map.update(m._handlers)
        return handler_map

    @classmethod
    def get_mark[
        M
    ](cls, msg_type: type[Message], default: M = None) -> "Mark[Message, IReturn] | M ":
        return cls._mark_registry.get(msg_type, default)


@ty.overload
def mark[C](msg_type: type[C]) -> Mark[C, ty.Any]: ...


@ty.overload
def mark[C, R](msg_type: type[C], rt: type[R]) -> Mark[C, R]: ...


def mark[
    C, R
](msg_type: type[C], rt: type[R] | None = None) -> Mark[C, R] | Mark[C, ty.Any]:
    m = Mark[C, R].get_mark(msg_type, Mark[C, R](msg_type))
    return m
