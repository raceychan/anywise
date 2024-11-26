import typing as ty

from ididi import DependencyGraph

from ._itypes import IHandler
from ._type_resolve import resolve_handlers


class AnyWise:
    """
    userwise = AnyWise()
    authwise = AnyWise()

    appwise = AnyWise.include([user_wise, auth_wise])

    class CreateUser(Command):
        ...

    @app.post("users")
    async def _(create_user: CreateUser):
        appwise.send(command)
    """

    wises: ty.ClassVar[list["AnyWise"]] = []

    def __init__(self):
        self.wises.append(self)
        self._handlers: dict[type, IHandler] = {}
        self._dg = DependencyGraph()

    def register(self, obj):
        self._handlers.update(resolve_handlers(obj))

    def send[T](self, command: T):
        """Send a command to its registered handler."""
        try:
            handler = self._handlers[type(command)]
        except KeyError:
            raise ValueError(f"No handler registered for command type {type(command)}")
        return self._dg.entry(handler)(command)


# Example usage:
