import inspect
import sys
import types
import typing as ty
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple, Type

from ._itypes import ICommand, IHandler


@dataclass
class HanlderInfo:
    handler: ty.Callable
    command_type: type
    handler_type: type | None = None


def resolve_from_function(func: IHandler) -> Optional[Tuple[Type[ICommand], Callable]]:
    """Register a single function as a handler and return the command type and handler pair."""
    if not inspect.isfunction(func):
        return None

    sig = inspect.signature(func)
    for param in sig.parameters.values():
        param_ant = param.annotation
        if param_ant is sig.empty:
            continue
        if inspect.isclass(param.annotation) and issubclass(param.annotation, ICommand):
            return (param.annotation, func)

    return None


def resolve_from_class(cls: type) -> Dict[Type[ICommand], Callable]:
    """Register all methods in a class that handle commands and return command-handler mapping."""
    handlers = {}
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        result = resolve_from_function(method)
        if result:
            command_type, handler = result
            handlers[command_type] = handler
    return handlers


def resolve_from_module(module: types.ModuleType) -> Dict[Type[ICommand], Callable]:
    """Register all classes and functions in a module and return command-handler mapping."""
    handlers = {}
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and not issubclass(obj, ICommand):
            handlers.update(resolve_from_class(obj))
        elif inspect.isfunction(obj):
            result = resolve_from_function(obj)
            if result:
                command_type, handler = result
                handlers[command_type] = handler
    return handlers


def resolve_handlers(
    target: ty.Union[ty.Callable, type, str, object]
) -> Dict[Type[ICommand], Callable]:
    """
    Register handlers from various sources and return command-handler mapping:
    - Function/method
    - Class
    - Module (as string or module object)
    - Object instance
    """
    handlers = {}

    if isinstance(target, str):
        # Register by module name
        try:
            module = sys.modules[target]
            handlers.update(resolve_from_module(module))
        except KeyError:
            raise ValueError(f"Module {target} not found")

    elif inspect.ismodule(target):
        # Register a module object
        handlers.update(resolve_from_module(target))

    elif inspect.isclass(target):
        # Register a class
        handlers.update(resolve_from_class(target))

    elif inspect.isfunction(target) or inspect.ismethod(target):
        # Register a function or method
        result = resolve_from_function(target)
        if result:
            command_type, handler = result
            handlers[command_type] = handler

    elif isinstance(target, object):
        # Register an instance's methods
        handlers.update(resolve_from_class(target.__class__))

    else:
        raise ValueError(f"Cannot register {target} of type {type(target)}")

    return handlers
