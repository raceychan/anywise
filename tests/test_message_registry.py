from anywise import Anywise, MessageRegistry
from tests.conftest import (  # CreateUser,; RemoveUser,; UpdateUser,
    CreateUser,
    RemoveUser,
    UserCommand,
    UserCreated,
    UserEvent,
    UserNameUpdated,
)

user_message_registry = MessageRegistry(event_base=UserEvent, command_base=UserCommand)


@user_message_registry
async def react_to_event(
    event: UserCreated | UserNameUpdated,
) -> None:
    print(f"handling {event=}")


# @user_message_registry
# class UserService:
#     def __init__(self, name: str = "test", *, anywise: Anywise):
#         self.name = name
#         self._aw = anywise

#     async def create_user(self, cmd: CreateUser) -> str:
#         assert self.name == "test"
#         return "hello"

#     async def remove_user(self, cmd: RemoveUser) -> str:
#         assert self.name == "test"
#         return "goodbye"

#     def hello(self) -> str:
#         return "hello"


def test_message_registry():
    assert user_message_registry.event_mapping[UserNameUpdated]
    assert user_message_registry.command_mapping[CreateUser]
    # anywise = Anywise(user_message_registry)
