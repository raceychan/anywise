import typing as ty
from dataclasses import dataclass

type HandlerMapping[Command] = dict[type[Command], "CallableMeta[Command]"]
type ListenerMapping[E] = dict[type[E], list[CallableMeta[E]]]

type ContextedHandler = ty.Callable[[ty.Any, dict[str, ty.Any]], ty.Any]

@dataclass(frozen=True, slots=True, kw_only=True)
class CallableMeta[Message]:
    message_type: type[Message]
    handler: ty.Callable[[Message], ty.Any] | ContextedHandler
    is_async: bool
    is_contexted: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class FuncMeta[Message](CallableMeta[Message]):
    """
    is_async: bool
    is_contexted:
    whether to pass a context object to handler
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class MethodMeta[Message](CallableMeta[Message]):
    owner_type: type


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
