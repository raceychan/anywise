from dataclasses import dataclass
from typing import Any, Callable

from ididi.interfaces import GraphIgnore
from .Interface import IGuard

type HandlerMapping[Command] = dict[type[Command], "FuncMeta[Command]"]
type ListenerMapping[Event] = dict[type[Event], list[FuncMeta[Event]]]


@dataclass(frozen=True, slots=True, kw_only=True)
class FuncMeta[Message]:
    """
    is_async: bool
    is_contexted:
    whether the handler receives a context param
    """

    message_type: type[Message]
    handler: Callable[..., Any] 
    is_async: bool
    is_contexted: bool
    ignore: GraphIgnore


@dataclass(frozen=True, slots=True, kw_only=True)
class MethodMeta[Message](FuncMeta[Message]):
    owner_type: type


@dataclass(frozen=True, slots=True, kw_only=True)
class GuardMeta:
    guard_target: type
    guard: IGuard | type[IGuard]
