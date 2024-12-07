from dataclasses import dataclass

import pytest

from anywise import AnyWise, inject
from anywise.mark import mark


@dataclass
class UserCommand:
    user_id: str


@dataclass
class CreateUser(UserCommand):
    user_name: str


@dataclass
class RemoveUser(UserCommand):
    user_name: str


@dataclass
class UpdateUser(UserCommand):
    old_name: str
    new_name: str


command_handler = mark(UserCommand)


@command_handler.register
class UserService:
    def __init__(self, name: str = "test"):
        self.name = name

    def create_user(self, cmd: CreateUser) -> str:
        assert self.name == "test"
        return "hello"

    def remove_user(self, cmd: RemoveUser) -> str:
        assert self.name == "test"
        return "goodbye"


def user_service_factory() -> "UserService":
    return UserService(name="test")


@command_handler.register
def update_user(
    cmd: UpdateUser,
    service: UserService = inject(user_service_factory),
) -> str:
    return cmd.new_name


@pytest.fixture
def anywise() -> AnyWise[UserCommand]:
    aw = AnyWise[UserCommand]()
    aw.merge_registries([command_handler])
    return aw


def test_sendto_method(anywise: AnyWise[UserCommand]):
    cmd = CreateUser("1", "user")
    res = anywise.send(cmd)
    assert res == "hello"

    rm_cmd = RemoveUser("1", "user")
    res = anywise.send(rm_cmd)
    assert res == "goodbye"


def test_sendto_function(anywise: AnyWise[UserCommand]):
    cmd = UpdateUser("1", "user", "new")
    res = anywise.send(cmd)
    assert res == "new"
