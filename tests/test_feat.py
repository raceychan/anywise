from dataclasses import dataclass

import pytest

from anywise.anywise import AnyWise
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


@pytest.fixture
def anywise() -> AnyWise[UserCommand]:
    aw = AnyWise[UserCommand]()
    aw.collect(command_handler)
    return aw


@command_handler
def update_user(cmd: UpdateUser) -> str:
    return cmd.new_name


@command_handler
class UserService:
    def __init__(self):
        self.name = "name"

    def create_user(self, cmd: CreateUser) -> str:
        return "hello"

    def remove_user(self, cmd: RemoveUser) -> str:
        return "goodbye"

    # @command_handler.unpack(CreateUser)
    # def unpack_create(self, user_id: str, user_name: str) -> str:
    #     return "created"


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


from fastapi import Depends


class User:
    def __init__(self, name: str = "name"): ...


def user_repo(user: User = Depends(User)):
    return user


def test_fastapi_factor():
    repo = user_repo()
