import typing as ty

from ididi import DependencyGraph

from .mark import Mark

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
        self._dg = dg or DependencyGraph()
        self._command_handlers: dict[type[MessageType], Mark[MessageType, ty.Any]] = {}
        self._event_handlers: ... = {}
        self._dg.register_dependent(self, self.__class__)

    def collect(self, mark: Mark[MessageType, ty.Any]) -> None:
        """
        handlers should be able to get anywise as dependency

        async def create_user(aw: AnyWise, repo: UserRepo, cmd: CreateUser):
            user = User(cmd.user_id, cmd.user_name, cmd.user_email)
            await repo.add(user)
            event = UserCreated(user_id, user_name, user_email, created_at)
            await aw.publish(event)
        """
        # merge them alone the way?
        for msg_type in mark.duties:
            self._command_handlers[msg_type] = mark

    def send(self, msg: MessageType):
        # should we separate send and ask?
        mark = self._command_handlers[type(msg)]
        # assert handler is not async
        return mark.dispatch(msg)

    # async def ask(self, msg) -> R: ...

    async def publish(self, msg: MessageType, concurrent: bool = False) -> None:
        """
        if concurrent
        """
        subscribers = self._event_handlers[type(msg)]

        for sub in subscribers:
            await sub.dispatch(msg)
            """
            if event.to_sink:
                await self._event_sink.write(event)
            """
