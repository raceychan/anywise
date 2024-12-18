import pytest

from anywise import Anywise, MessageRegistry, concurrent_publish, inject
from tests.conftest import (
    CreateUser,
    RemoveUser,
    UpdateUser,
    UserCommand,
    UserCreated,
    UserEvent,
    UserNameUpdated,
)

user_message_registry = MessageRegistry(event_base=UserEvent, command_base=UserCommand)


@user_message_registry
class UserService:
    def __init__(self, name: str = "test", *, anywise: Anywise):
        self.name = name
        self._aw = anywise

    async def create_user(self, cmd: CreateUser) -> str:
        assert self.name == "test"
        return "hello"

    async def remove_user(self, cmd: RemoveUser) -> str:
        assert self.name == "test"
        return "goodbye"

    def hello(self) -> str:
        return "hello"


def user_service_factory(asynwise: Anywise) -> "UserService":
    return UserService(name="test", anywise=asynwise)


@user_message_registry
async def update_user(
    cmd: UpdateUser,
    anywise: Anywise,
    service: UserService = inject(user_service_factory),
) -> str:
    assert service.hello() == "hello"
    await anywise.publish(UserNameUpdated(cmd.new_name))
    return "ok"


@user_message_registry
async def react_to_event(
    event: UserCreated,
    service: UserService = inject(user_service_factory),
) -> None:
    print(f"handling {event=}")


@pytest.fixture(scope="module")
def asynwise() -> Anywise:
    aw = Anywise(publisher=concurrent_publish)
    aw.include(user_message_registry)
    return aw


async def test_send_to_method(asynwise: Anywise):
    cmd = CreateUser("1", "user")
    res = await asynwise.send(cmd)
    assert res == "hello"

    rm_cmd = RemoveUser("1", "user")
    res = await asynwise.send(rm_cmd)
    assert res == "goodbye"


async def test_send_to_function(asynwise: Anywise):
    cmd = UpdateUser("1", "user", "new")
    res = await asynwise.send(cmd)
    assert res == "ok"


async def test_event_handler(asynwise: Anywise):
    event = UserCreated("new_name")
    await asynwise.publish(event)
