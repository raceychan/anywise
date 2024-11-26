import inspect
import typing as ty
from collections import defaultdict

from ididi import DependencyGraph

type Command = type

"""
register class with mark
register method with mark

if method is registered with mark like

@mark(CreateUser)
def create_user(user_id: str, user_email: str):
    ...

we unpack the command and send it there

bus.send(command) -> self.get_handler(command)(**command)
"""

"""
aw.send[CreateUser](command)
"""


class Mark:
    mark_registry: defaultdict[Command, list[ty.Callable[..., ty.Any]]] = defaultdict(
        list
    )

    def __init__[**P, R](self, coh: Command | ty.Callable[P, R] | None = None):
        if coh:
            self._coh = coh
        else:
            self._coh = None

    def register[
        **P, R
    ](self, command: Command | ty.Callable[P, R], hanlder: ty.Callable[P, R]):
        return self.mark_registry[command].append(hanlder)

    def merge(self): ...


@ty.overload
def mark[R](coh: type[R]) -> type[R]: ...


@ty.overload
def mark[**P, R](coh: ty.Callable[P, R]) -> ty.Callable[P, R]: ...


# @ty.overload
# def mark(coh: ty.Literal[None]): ...


def mark[**P, R](coh: type[R] | ty.Callable[P, R]) -> type[R]:
    """
    @mark
    class UserService:
        ...

    from app.features import user
    mark(user)


    class UserService:
        @mark(CreateUser)
        def create_user(self, user_id: str, user_name: str, user_email: str):
            ...

    @mark
    async def notify_user(notification, user):
        ...
    
    """
    # dg = DependencyGraph()

    def wrapper():
        ...

    # def decor(coh: ty.Callable[P, R]) -> Mark:
    #     mark = Mark(coh)
    #     return mark

    # if coh:
    #     return decor(coh)
    # return decor
