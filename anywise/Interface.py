"Interface, type alias, and related stuff"

from types import ModuleType
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Mapping,
    MutableMapping,
    Protocol,
)

type IContext = dict[Any, Any]
type GuardFunc = Callable[[Any, IContext], Awaitable[Any]]
type PostHandle[R] = Callable[[Any, IContext, R], Awaitable[R]]
type IEventContext = Mapping[Any, Any]


type CommandHandler = Callable[[Any, IContext], Any] | IGuard
type EventListener = Callable[[Any, IEventContext], Any]
type EventListeners = list[EventListener]
type SendStrategy = Callable[[Any, IContext | None, CommandHandler], Any]
type PublishStrategy = Callable[
    [Any, IEventContext | None, EventListeners], Awaitable[None]
]

type LifeSpan = Callable[..., AsyncGenerator[Any, None]]


CTX_MARKER = "__anywise_context__"

type Context[M: MutableMapping[Any, Any]] = Annotated[M, CTX_MARKER]
type FrozenContext[M: Mapping[Any, Any]] = Annotated[M, CTX_MARKER]

type Registee = IPackage | ModuleType | type | CommandHandler | EventListener


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
