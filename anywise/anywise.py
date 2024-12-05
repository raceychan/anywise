import typing as ty

from ididi import DependencyGraph

from .mark import Mark

"""
1. use mark to collect handlers, register them into nodes
2. merge marks into anywise
3. statically resolve all dependencies at anywise
4. when call, resolve dependencies, inject them to handler
"""

# async def ask(self, msg) -> R: ...

# async def publish(self, msg: MessageType, concurrent: bool = False) -> None:
#     """
#     if concurrent
#     """
#     subscribers = self._event_handlers[type(msg)]

#     for sub in subscribers:
#         await sub.dispatch(msg)
#         # if event.to_sink:
#         # await self._event_sink.write(event)


class AnyWise[MessageType]:
    def __init__(self, dg: DependencyGraph | None = None):
        self._dg = dg or DependencyGraph()
        self._handler_details = {}
        self._command_handlers = {}
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

    def build_graph(self): ...

    def send(self, msg: MessageType) -> ty.Any:
        # return a result T or an Awaitable[T]
        ...


