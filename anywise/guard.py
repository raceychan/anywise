import typing as ty

"""
provide a mechanism that

1. execute before the handler, return nothing
2. wrap the handler, works like a decorator
"""

type MessageGuard = ty.Callable[..., ty.Any]


class Guard[MessageType]:
    def __init__(self, guard: MessageGuard): ...

    def __call__(self, message: MessageType): ...


# this acts like a decorator
class Context: ...


# async def dispatch(self, message: MessageType, call_next: HandlerFunction):
# response = await call_next(request)


"""

user_handler = mark(UserCommand)

@user_handler
class UserService:

    @user_handler.guard # execute before every command handler
    async def _validate_user(self) -> None:
        ...


    async def remove_user(self, cmd: RemoveUser):
        ...
"""
