"Interface, type alias, and related stuff"

from types import ModuleType
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Final,
    Literal,
    Mapping,
    MutableMapping,
    Protocol,
    Sequence,
    TypeGuard,
)

type IContext = dict[Any, Any]
type GuardFunc = Callable[[Any, IContext], Awaitable[Any]]
type PostHandle[R] = Callable[[Any, IContext, R], Awaitable[R]]
type IEventContext = Mapping[Any, Any]


type CommandHandler[C] = Callable[[C, IContext], Any] | IGuard
type EventListener[E] = Callable[[E, IEventContext], Any]
type EventListeners[E] = Sequence[EventListener[E]]
type SendStrategy[C] = Callable[[C, IContext | None, CommandHandler[C]], Any]
type PublishStrategy[E] = Callable[
    [Any, IEventContext | None, EventListeners[E]], Awaitable[None]
]

type LifeSpan = Callable[..., AsyncGenerator[Any, None]]


CTX_MARKER = "__anywise_context__"

type Context[M: MutableMapping[Any, Any]] = Annotated[M, CTX_MARKER]
type FrozenContext[M: Mapping[Any, Any]] = Annotated[M, CTX_MARKER]

type Registee = IPackage | ModuleType | type | CommandHandler[Any] | EventListener[Any]


class IPackage(Protocol):
    def __path__(self) -> list[str]: ...


class IGuard(Protocol):

    @property
    def next_guard(self) -> GuardFunc | None: ...

    def chain_next(self, next_guard: GuardFunc, /) -> None:
        """
        self._next_guard = next_guard
        """

    async def __call__(self, command: Any, context: IContext) -> Any: ...


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
