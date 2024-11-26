import types
import typing as ty

# from uuid import uuid4


class ICommand: ...


class IQuery[R]: ...


class IEvent: ...


type CommandHandler[C] = ty.Callable[[C], ty.Coroutine[ty.Any, ty.Any, None]]
type QueryHandler[Q, R] = ty.Callable[[Q], ty.Coroutine[ty.Any, ty.Any, R]]
type EventHandler[E] = ty.Callable[[E], ty.Coroutine[ty.Any, ty.Any, None]]
type Handler[P, R] = CommandHandler[P] | QueryHandler[P, R] | EventHandler[P]
type Message[R] = ICommand | IQuery[R] | IEvent


class AnyWised(ty.Protocol):
    __anywised__: bool


def anywise(t: types.ModuleType | ty.Callable | type) -> ty.TypeGuard[AnyWised]:
    setattr(t, "__anywised__", True)
    return t


class IHandler(ty.Protocol):

    def __call__(self, command: ICommand) -> None: ...


class Result[T, E]:
    ok: T
    err: E | None = None

    def __iter__(self):
        return iter((self.ok, self.err))


class _Missed:

    def __str__(self) -> str:
        return "MISSING"

    def __bool__(self) -> ty.Literal[False]:
        return False


MISSING = _Missed()

type Maybe[T] = T | _Missed


def is_provided[T](obj: Maybe[T]) -> ty.TypeGuard[T]:
    return obj is not MISSING
