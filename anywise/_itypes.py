from collections import defaultdict
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Final, Literal, Protocol, TypeGuard

type HandlerMapping[Command] = dict[type[Command], "FuncMeta[Command]"]
type ListenerMapping[Event] = dict[type[Event], list[FuncMeta[Event]]]
type GuardMapping[Command] = defaultdict[type[Command], list[IGuard]]

type GuardContext = dict[str, Any]
type GuardFunc = Callable[[Any, GuardContext], Awaitable[Any]]
type PostHandle[R] = Callable[[Any, GuardContext, R], Awaitable[R]]
type CommandContext = dict[str, Any]
type EventContext = MappingProxyType[str, Any]


class IGuard(Protocol):

    @property
    def next_guard(self) -> GuardFunc | None: ...

    def chain_next(self, next_guard: GuardFunc, /) -> None:
        """
        self._next_guard = next_guard
        """

    async def __call__(self, message: Any, context: GuardContext) -> Any: ...


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


@dataclass(frozen=True, slots=True, kw_only=True)
class MethodMeta[Message](FuncMeta[Message]):
    owner_type: type


class Result[T, E]:
    """
    def divide(a: int, b: int) -> Result[int, ZeroDivisionError]:
        if b == 0:
            raise ZeroDivisionError
        return a / b
    """

    ok: T
    err: E | None = None

    def __iter__(self):
        return iter((self.ok, self.err))


class _Missed:

    def __str__(self) -> str:
        return "MISSING"

    def __bool__(self) -> Literal[False]:
        return False


Missed: Final[type[_Missed]] = _Missed
MISSING = _Missed()


type Maybe[T] = T | _Missed


def is_provided[T](obj: Maybe[T]) -> TypeGuard[T]:
    return obj is not MISSING
