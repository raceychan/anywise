import typing as ty

from ididi import DependencyGraph

from ._type_resolve import HandlerMapping, Mark


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

    def __init__(self):
        self._handlers = {}
        self._dg = DependencyGraph()

        self.command_handlers: HandlerMapping[ty.Any] = {}

    def register(self, mark: Mark[ty.Any]) -> None:
        self.command_handlers.update(mark.merge_all())

    async def send[R](self, msg: ty.Any) -> ty.Awaitable[R]:
        """
        aw.send[CreateUser](command)
        """

        container = self.command_handlers[type(msg)]

        if (owner_type := container.owner_type) is not None:
            obj = self._dg.resolve(owner_type)
            return await container.handler(obj, msg)
        else:
            return await container.handler(msg)

    # async def ask(self, msg) -> R: ...

    # async def publish(self, msg) -> R: ...


