import inspect
import sys
from collections import defaultdict
from types import UnionType
from typing import (  # Annotated,; TypeGuard,
    Annotated,
    Any,
    Callable,
    Union,
    cast,
    get_args,
    get_origin,
)

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

if sys.version_info >= (3, 10):
    UNION_META = (UnionType, Union)
else:
    UNION_META = (Union,)


def all_subclasses(cls: type) -> set[type]:
    return set(cls.__subclasses__()).union(
        *[all_subclasses(c) for c in cls.__subclasses__()]
    )


def gather_commands(command_type: type | UnionType) -> set[type]:
    """
    get a list of command from an annotation of command
    if is a union of commands, collect each of them
    else
    """

    command_types: set[type] = set()

    origin = get_origin(command_type)

    if origin in UNION_META:
        union_commands = get_args(command_type)
        for command in union_commands:
            command_types |= gather_commands(command)
    # elif origin is Annotated:
    #     command_type = origin.__value__[0]
    else:
        # this might be a bug in pylance that we have to use cast
        command_type = cast(type, command_type)
        command_types.add(command_type)
        command_types |= all_subclasses(command_type)
    return command_types


def gather_types(annotation: Any) -> set[type]:
    """
    Recursively gather all types from a type annotation, handling:
    - Union types (|)
    - Annotated types
    - Direct types
    """
    types: set[type] = set()

    # Handle None case
    if annotation is None or annotation is inspect.Signature.empty:
        return types

    # Handle Union types (including X | Y syntax)
    origin = get_origin(annotation)
    if origin is not None:
        if origin is Annotated:
            # For Annotated[Type, ...], we only care about the first argument
            types.update(gather_types(get_args(annotation)[0]))
        elif origin in UNION_META:
            # Handle both Union[X, Y] and X | Y syntax
            for arg in get_args(annotation):
                types.update(gather_types(arg))
        else:
            # Generic type, e.g. List, Dict, etc.
            types.add(origin)
            for arg in get_args(annotation):
                types.update(gather_types(arg))
    else:
        types.add(annotation)
        types |= all_subclasses(annotation)
    return types


def _extract_from_function[
    Message
](
    message_type_base: type[Message],
    handler: Callable[..., Any],
    ignore_first: bool = False,
) -> list[FuncMeta[Message]]:
    """
    async def listen_user_renamed(event: UserRenamed | UserNameChanged):
        ...

    async def listen_user_renamed(event: Annotated[""]):
        ...
    """

    sig = inspect.signature(handler)

    is_async: bool = inspect.iscoroutinefunction(handler)
    is_contexted: bool = False

    target_types: set[type] = set()
    params = sig.parameters.values()

    if ignore_first:
        params = list(params)[1:]
        if len(params) < 1:
            raise MessageHandlerNotFoundError(message_type_base, handler)
    elif len(params) < 1:
        raise MessageHandlerNotFoundError(message_type_base, handler)

    msg, *rest = params

    msg_types = gather_types(msg.annotation)
    is_contexted = bool(rest) and rest[0].name == "context"

    for msg_type in msg_types:
        if issubclass(msg_type, message_type_base):
            target_types.add(msg_type)

    if not target_types:
        raise MessageHandlerNotFoundError(message_type_base, handler)


    metas = [
        FuncMeta[Any](
            message_type=t,
            handler=handler,
            is_async=is_async,
            is_contexted=is_contexted,
            ignore=ignore,
        )
        for t in target_types
    ]
    return metas


def _extract_from_class[
    Message
](base_msg_type: type[Message], cls: type) -> list[FuncMeta[Message]]:
    method_metas: list[FuncMeta[Message]] = []
    cls_members = inspect.getmembers(cls, predicate=inspect.isfunction)
    for method_name, method in cls_members:
        if method_name.startswith("_"):
            continue

        try:
            func_metas = _extract_from_function(
                base_msg_type, method, ignore_first=True
            )
        except MessageHandlerNotFoundError:
            continue

        for meta in func_metas:
            message_type = meta.message_type
            method_meta = MethodMeta[Message](
                message_type=message_type,
                handler=meta.handler,
                owner_type=cls,
                ignore=meta.ignore,
                is_async=meta.is_async,
                is_contexted=meta.is_contexted,
            )
            method_metas.append(method_meta)

    if not method_metas:
        raise MessageHandlerNotFoundError(cls, base_msg_type)
    return method_metas


def collect_handlers[
    Message
](message_type: type[Message], target: Target) -> HandlerMapping[Message]:
    mapping: HandlerMapping[Message] = {}

    if inspect.isfunction(target):
        func_metas = _extract_from_function(message_type, target)
        for meta in func_metas:
            mapping[meta.message_type] = meta
    elif inspect.isclass(target):
        method_metas = _extract_from_class(message_type, target)
        for meta in method_metas:
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
        func_metas = _extract_from_function(message_type, target)
        for meta in func_metas:
            mapping[meta.message_type].append(meta)
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
