import typing as ty

from ididi import DependencyGraph

from .mark import HandlerMapping, Mark

# class AsyncWise:
#     call sync handler in anyio worker thread
#     def __init__(self, wise: AnyWise):
#         self.wise = wise

#     async def send(self, msg: IMessage) -> ty.Awaitable[ty.Any]:
#         ...
#


class IMessage[R](ty.Protocol):
    "The base massage protocol"
    # def __subclasscheck__(self, subclass: type) -> bool: ...


class AnyWise[MessageType]:
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

    def __init__(self, dg: DependencyGraph | None = None):
        # self._handlers = {}
        self._dg = dg or DependencyGraph()
        self.command_handlers: HandlerMapping[MessageType] = {}

    def merge_marks(self, mark: Mark[MessageType, ty.Any]) -> None:
        self.command_handlers.update(mark.merge_all())
        # statically analysie dependencies

    def send(self, msg: MessageType):
        container = self.command_handlers[type(msg)]

        # assert handler is async
        if (owner_type := container.owner_type) is not None:
            obj = self._dg.resolve(owner_type)
            res = container(obj, message=msg)
        else:
            res = container(message=msg)

        return res

    # async def ask(self, msg) -> R: ...

    # async def publish(self, msg) -> R: ...
