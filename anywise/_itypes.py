from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Awaitable, Callable, Literal, Protocol, TypeGuard

type HandlerMapping[Command] = dict[type[Command], "FuncMeta[Command]"]
type ListenerMapping[E] = dict[type[E], list[FuncMeta[E]]]

type GuardContext = dict[str, Any]
type GuardFunc = Callable[[Any, GuardContext], Awaitable[Any]]
type PostHandle[R] = Callable[[Any, GuardContext, R], Awaitable[R]]
type CommandContext = dict[str, Any]
type EventContext = MappingProxyType[str, Any]


class IGuard(Protocol):
    next_guard: GuardFunc | None
    # def bind(self, command: type | list[type]) -> None: ...

    def chain_next(self, guard: GuardFunc) -> None: ...
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
    ok: T
    err: E | None = None

    def __iter__(self):
        return iter((self.ok, self.err))


class _Missed:

    def __str__(self) -> str:
        return "MISSING"

    def __bool__(self) -> Literal[False]:
        return False


MISSING = _Missed()

type Maybe[T] = T | _Missed


def is_provided[T](obj: Maybe[T]) -> TypeGuard[T]:
    return obj is not MISSING
