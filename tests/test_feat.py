import pytest

from anywise._registry import get_funcmetas, get_methodmetas
from anywise.errors import InvalidHandlerError
from tests.conftest import CreateUser, UpdateUser, UserCommand


async def update_user(cmd: UpdateUser | CreateUser) -> str:
    return "ok"


def test_invalid_handler():

    def test(name: str): ...

    with pytest.raises(InvalidHandlerError):
        get_funcmetas(UserCommand, test)


class UserService:
    def __init__(self):
        self._name = "service"

    @property
    def name(self):
        return self._name

    def hello(self):
        return "hello"

    def create_user(self, command: CreateUser): ...


def test_get_funcmetas():
    results = get_funcmetas(msg_base=UserCommand, func=update_user)
    assert len(results) == 2
    assert results[0].handler == results[1].handler == update_user


def test_get_methodmetas():
    metas = get_methodmetas(UserCommand, UserService)
    assert len(metas) == 1
    assert metas[0].handler is UserService.create_user
