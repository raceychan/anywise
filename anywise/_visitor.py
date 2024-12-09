import ast
import inspect
from collections import defaultdict
from typing import Any, Callable

from ._itypes import CallableMeta, FuncMeta, HandlerMapping, ListenerMapping, MethodMeta
from .errors import MessageNotFoundError, NotSupportedHandlerTypeError

type Target = type | Callable[..., Any]


class ExceptionFinder(ast.NodeVisitor):
    def __init__(self):
        self.exceptions: list[str] = []

    def visit_Raise(self, node: ast.Raise):
        if node.exc:  # If there is an exception being raised
            if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                # Example: `raise ValueError("...")`
                self.exceptions.append(node.exc.func.id)
            elif isinstance(node.exc, ast.Name):
                # Example: `raise CustomException`
                self.exceptions.append(node.exc.id)
        self.generic_visit(node)


def collect_exceptions[**P, T](func: Callable[P, T]) -> list[Exception]:
    source = inspect.getsource(func)
    tree = ast.parse(source)
    finder = ExceptionFinder()
    finder.visit(tree)
    excs: list[Exception] = []
    for e in finder.exceptions:
        if exc := getattr(__builtins__, e, None):
            excs.append(exc)
        else:
            exc = func.__globals__[e]
            excs.append(exc)
    return excs


def _extract_from_function[
    Message
](message_type: type[Message], handler: Callable[..., Any],) -> CallableMeta[Message]:
    sig = inspect.signature(handler)
    for param in sig.parameters.values():
        param_type = param.annotation
        if param_type is sig.empty:
            continue
        if inspect.isclass(param_type) and issubclass(param_type, message_type):
            is_async: bool = inspect.iscoroutinefunction(handler)
            return FuncMeta(param_type, handler, is_async=is_async)
    raise MessageNotFoundError(
        f"can't find param of type `{message_type}` in {handler} signature"
    )


def _extract_from_class[
    Message
](base_msg_type: type[Message], cls: type) -> list[CallableMeta[Message]]:
    handlers: list[CallableMeta[Message]] = []
    cls_members = inspect.getmembers(cls, predicate=inspect.isfunction)
    for method_name, method in cls_members:
        if method_name.startswith("_"):
            continue
        try:
            func_meta = _extract_from_function(base_msg_type, method)
        except MessageNotFoundError:
            continue
        message_type = func_meta.message_type
        container = MethodMeta[Message](
            message_type=message_type,
            handler=func_meta.handler,
            is_async=func_meta.is_async,
            owner_type=cls,
        )
        handlers.append(container)

    if not handlers:
        raise MessageNotFoundError(f"{cls} does not have any handler")
    return handlers


def collect_handlers[
    Message
](message_type: type[Message], target: Target) -> HandlerMapping[Message]:
    """
    TODO:
    collect from module, package, project
    if target is None, collect current module
    """
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
    """
    TODO: collect from module, package, project
    if target is None, collect current module
    """
    mapping: ListenerMapping[Message] = defaultdict(list)
    if inspect.isfunction(target):
        func_meta = _extract_from_function(message_type, target)
        mapping[func_meta.message_type].append(func_meta)
    elif inspect.isclass(target):
        metas = _extract_from_class(message_type, target)
        for meta in metas:
            mapping[meta.message_type].append(meta)
    else:
        raise Exception("Handler Not Supported")
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


