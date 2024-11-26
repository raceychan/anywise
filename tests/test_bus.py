import typing as ty

from anywise._itypes import ICommand, IQuery
from anywise.bus import MessageBus

mb = MessageBus()


class UserInfo(ty.TypedDict):
    name: str
    age: int


# Example subclass of Query with a specific return type
class GetUserQuery(IQuery[UserInfo]):
    def __init__(self, user_id: int):
        self.user_id = user_id


class CreateUserCommand(ICommand):
    def __init__(self, user_id: int):
        self.user_id = user_id


async def get_user_handler(query: GetUserQuery):
    return query.user_id


async def create_user_handler(command: CreateUserCommand): ...


async def test_bus():
    await mb.send(CreateUserCommand(user_id=123))
    user = await mb.send(GetUserQuery(user_id=123))
    print(f"Handling {GetUserQuery} result {user}")
