import ast
import inspect
import typing as ty
from collections import defaultdict

from ._itypes import CallableMeta, FuncMeta, HandlerMapping, ListenerMapping, MethodMeta

type Target = type | ty.Callable[..., ty.Any]


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


def collect_exceptions[**P, T](func: ty.Callable[P, T]) -> list[Exception]:
    """
    TODO: recursively search for function call,
    diffierentiate customized exception and builtin exception
    only collect customized exception
    """
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
](message_type: type[Message], handler: ty.Callable[..., ty.Any]) -> CallableMeta[
    Message
]:
    sig = inspect.signature(handler)
    for param in sig.parameters.values():
        param_type = param.annotation
        if param_type is sig.empty:
            continue
        if inspect.isclass(param_type) and issubclass(param_type, message_type):
            return FuncMeta(param_type, handler)
    else:
        raise Exception(f"no subcommand found in {handler}")


def _extract_from_class[
    Message
](base_msg_type: type[Message], cls: type) -> list[CallableMeta[Message]]:
    handlers: list[CallableMeta[Message]] = []
    for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if method_name.startswith("_"):
            continue
        func_meta = _extract_from_function(base_msg_type, method)
        message_type = func_meta.message_type
        container = MethodMeta[Message](
            message_type=message_type,
            handler=func_meta.handler,
            owner_type=cls,
        )
        handlers.append(container)
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
        raise Exception("Handler Not Supported")
    return mapping


def collect_listeners[
    Message
](
    message_type: type[Message], target: type | ty.Callable[..., ty.Any]
) -> ListenerMapping[Message]:
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


# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """
#     ...
