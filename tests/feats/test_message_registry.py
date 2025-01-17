import pytest

from anywise import Anywise, MessageRegistry, use
from anywise.errors import (
    InvalidHandlerError,
    MessageHandlerNotFoundError,
    NotSupportedHandlerTypeError,
)
from anywise.Interface import is_provided
from anywise.registry import get_funcmetas, get_methodmetas
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


class Database: ...


@user_message_registry.factory(reuse=False)
def db_factory() -> Database:
    return Database()


async def react_to_event(
    event: UserCreated | UserNameUpdated, db: Database = use(db_factory)
) -> None:
    assert isinstance(db, Database)


async def random_func(cmd: str): ...


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


def test_message_registry():
    user_message_registry.register(react_to_event, UserService)
    assert user_message_registry.event_mapping[UserNameUpdated]
    assert user_message_registry.command_mapping[CreateUser]
    user_message_registry.__repr__()


def test_unempty_msgreg():
    msg = MessageRegistry(command_base=str)
    assert is_provided(msg.command_base)
    assert not is_provided(msg.event_base)


def test_message_register_fail():
    with pytest.raises(InvalidHandlerError):
        user_message_registry.register(random_func)


async def update_user(cmd: UpdateUser | CreateUser) -> str:
    return "ok"


def test_invalid_handler():

    def test(name: str): ...
    def test2(): ...

    with pytest.raises(InvalidHandlerError):
        get_funcmetas(UserCommand, test)

    with pytest.raises(MessageHandlerNotFoundError):
        get_funcmetas(UserCommand, test2)


def test_register_invalid_handler():
    with pytest.raises(NotSupportedHandlerTypeError):
        user_message_registry(pytest)

    r = MessageRegistry(event_base=str)
    with pytest.raises(NotSupportedHandlerTypeError):
        r(pytest)


def test_invalid_guard():
    mr = MessageRegistry(command_base=str)

    def test(): ...

    with pytest.raises(MessageHandlerNotFoundError):
        mr.pre_handle(test)

    with pytest.raises(MessageHandlerNotFoundError):
        mr.pre_handle(pytest)


class HelloService:
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
    metas = get_methodmetas(UserCommand, HelloService)
    assert len(metas) == 1
    assert metas[0].handler is HelloService.create_user
