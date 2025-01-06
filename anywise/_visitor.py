import inspect
import sys
from types import UnionType
from typing import Annotated, Any, Callable, Union, get_args, get_origin

from .errors import InvalidMessageTypeError

type Target = type | Callable[..., Any]


# def _extract_from_module(base_msg_type: type, module: ModuleType):
# ...
# def auto_collect(msg_type: type, dir: pathlib.Path):
#     """
#     scan through dir, looking for function / methods
#     that contain subclass of msg_type as param of signature
#     record its return type
#     constrcut a anywise.pyi stub file along the way
#     """


if sys.version_info >= (3, 10):
    UNION_META = (UnionType, Union)
else:
    UNION_META = (Union,)


def all_subclasses(cls: type) -> set[type]:
    return set(cls.__subclasses__()).union(
        *[all_subclasses(c) for c in cls.__subclasses__()]
    )


def gather_types(annotation: Any) -> set[type]:
    """
    Recursively gather all types from a type annotation, handling:
    - Union types (|)
    - Annotated types
    - Direct types
    """
    types: set[type] = set()

    # Handle None case
    if annotation is inspect.Signature.empty:
        return types

    origin = get_origin(annotation)
    if not origin:
        types.add(annotation)
        types |= all_subclasses(annotation)
    else:
        # Union types (including X | Y syntax)
        if origin is Annotated:
            # For Annotated[Type, ...], we only care about the first argument
            param_type = get_args(annotation)[0]
            types.update(gather_types(param_type))
        elif origin in UNION_META:  # Union[X, Y] and X | Y
            for arg in get_args(annotation):
                types.update(gather_types(arg))
        else:
            # Generic type, e.g. List, Dict, etc.
            raise InvalidMessageTypeError(origin)
    return types
