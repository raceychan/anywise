from collections import defaultdict
from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Final,
    Literal,
    Mapping,
    MutableMapping,
    Protocol,
    TypeGuard,
)

type HandlerMapping[Command] = dict[type[Command], "FuncMeta[Command]"]
type ListenerMapping[Event] = dict[type[Event], list[FuncMeta[Event]]]
type GuardMapping[Command] = defaultdict[type[Command], list[IGuard]]

type IContext = MutableMapping[Any, Any]
type GuardFunc = Callable[[Any, IContext], Awaitable[Any]]
type PostHandle[R] = Callable[[Any, IContext, R], Awaitable[R]]
type EventContext = Mapping[Any, Any]


class IGuard(Protocol):

    @property
    def next_guard(self) -> GuardFunc | None: ...

    def chain_next(self, next_guard: GuardFunc, /) -> None:
        """
        self._next_guard = next_guard
        """

    async def __call__(self, command: Any, context: IContext) -> Any: ...


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


type Result[R, E] = Annotated[R, E]
"""
A helper type alias to represent a function that can return either a value or an error.

Example:
---
```py
class UserNotFoundError(Exception): ...


class InvalidStateError(Exception): ...


type SignupError = UserNotFoundError | InvalidStateError


def signup_user(command: CreateUser) -> Result[User, SignupError]:
    return user
```
"""


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
