import inspect
import sys
from collections import defaultdict
from types import UnionType
from typing import Any, Callable, TypeGuard, Union, cast, get_args, get_origin

from ._itypes import FuncMeta, HandlerMapping, ListenerMapping, MethodMeta
from .errors import MessageHandlerNotFoundError, NotSupportedHandlerTypeError

type Target = type | Callable[..., Any]


# class ExceptionFinder(ast.NodeVisitor):
#     def __init__(self):
#         self.exceptions: list[str] = []

#     def visit_Raise(self, node: ast.Raise):
#         if node.exc:  # If there is an exception being raised
#             if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
#                 # Example: `raise ValueError("...")`
#                 self.exceptions.append(node.exc.func.id)
#             elif isinstance(node.exc, ast.Name):
#                 # Example: `raise CustomException`
#                 self.exceptions.append(node.exc.id)
#         self.generic_visit(node)


# def collect_exceptions[**P, T](func: Callable[P, T]) -> list[Exception]:
#     source = inspect.getsource(func)
#     tree = ast.parse(source)
#     finder = ExceptionFinder()
#     finder.visit(tree)
#     excs: list[Exception] = []
#     for e in finder.exceptions:
#         if exc := getattr(__builtins__, e, None):
#             excs.append(exc)
#         else:
#             exc = func.__globals__[e]
#             excs.append(exc)
#     return excs


def _extract_from_function[
    Message
](message_type: type[Message], handler: Callable[..., Any],) -> FuncMeta[Message]:
    sig = inspect.signature(handler)

    is_async: bool = False
    meta = None

    for param in sig.parameters.values():
        param_type = param.annotation
        if param_type is sig.empty:
            continue
        if inspect.isclass(param_type) and issubclass(param_type, message_type):
            is_async: bool = inspect.iscoroutinefunction(handler)
            meta = FuncMeta(
                message_type=param_type,
                handler=handler,
                is_async=is_async,
                is_contexted=False,
            )
        if param.name == "context":
            if meta:
                meta = FuncMeta[Any](
                    message_type=meta.message_type,
                    handler=meta.handler,
                    is_async=meta.is_async,
                    is_contexted=True,
                )
                return meta

    if meta:
        return meta

    raise MessageHandlerNotFoundError(
        f"can't find param of type `{message_type}` in {handler} signature"
    )


def _extract_from_class[
    Message
](base_msg_type: type[Message], cls: type) -> list[FuncMeta[Message]]:
    handlers: list[FuncMeta[Message]] = []
    cls_members = inspect.getmembers(cls, predicate=inspect.isfunction)
    for method_name, method in cls_members:
        if method_name.startswith("_"):
            continue
        try:
            func_meta = _extract_from_function(base_msg_type, method)
        except MessageHandlerNotFoundError:
            continue
        message_type = func_meta.message_type
        container = MethodMeta[Message](
            message_type=message_type,
            handler=func_meta.handler,
            owner_type=cls,
            is_async=func_meta.is_async,
            is_contexted=func_meta.is_contexted,
        )
        handlers.append(container)

    if not handlers:
        raise MessageHandlerNotFoundError(
            f"{cls} does not have any handler for {base_msg_type}"
        )
    return handlers


def collect_handlers[
    Message
](message_type: type[Message], target: Target) -> HandlerMapping[Message]:
    mapping: HandlerMapping[Message] = {}

    if inspect.isfunction(target):
        func_meta = _extract_from_function(message_type, target)
        mapping[func_meta.message_type] = func_meta
    elif inspect.isclass(target):
        metas = _extract_from_class(message_type, target)
        for meta in metas:
            mapping[meta.message_type] = meta
    else:
        # TODO: extract from module
        raise NotSupportedHandlerTypeError("Handler Not Supported")
    return mapping


def collect_listeners[
    Message
](message_type: type[Message], target: type | Callable[..., Any]) -> ListenerMapping[
    Message
]:

    mapping: ListenerMapping[Message] = defaultdict(list)
    if inspect.isfunction(target):
        func_meta = _extract_from_function(message_type, target)
        mapping[func_meta.message_type].append(func_meta)
    elif inspect.isclass(target):
        metas = _extract_from_class(message_type, target)
        for meta in metas:
            mapping[meta.message_type].append(meta)
    else:
        raise NotSupportedHandlerTypeError("Handler Not Supported")
    return mapping


# def _extract_from_module(base_msg_type: type, module: ModuleType):
# from types import ModuleType
# handlers: defaultdict[type, list[CallableMeta]] = defaultdict(list)
# predict: Callable[[Any], bool] = lambda m: inspect.isclass(m) or inspect.isfunction(m)
# moduel_members = inspect.getmembers(module, predicate=predict)
# for name, member in moduel_members:
# if name.startswith("_"):
# continue
# ...

# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """


def all_subclasses(cls: type) -> set[type]:
    return set(cls.__subclasses__()).union(
        *[all_subclasses(c) for c in cls.__subclasses__()]
    )


def is_union_type(any_type: type | UnionType) -> TypeGuard[UnionType]:
    if sys.version_info >= (3, 10):
        union_meta = (UnionType, Union)
    else:
        union_meta = (Union,)

    return get_origin(any_type) in union_meta


def gather_commands(command_type: type | UnionType) -> set[type]:
    """
    get a list of command from an annotation of command
    if is a union of commands, collect each of them
    else
    """

    command_types: set[type] = set()

    if is_union_type(command_type):
        union_commands = get_args(command_type)
        for command in union_commands:
            command_types |= gather_commands(command)
    else:
        # this might be a bug in pylance
        command_type = cast(type, command_type)
        command_types.add(command_type)
        command_types |= all_subclasses(command_type)
    return command_types


# def extract_gurad_target(func: Callable[..., Any]) -> set[type]:
#     func_params = list(inspect.signature(func).parameters.values())
#     if not func_params:
#         return set()

#     command_type = func_params[0].annotation
#     return gather_commands(command_type)
