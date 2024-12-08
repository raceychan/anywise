from dataclasses import dataclass

import pytest

from anywise import AnyWise, handler_registry, inject, listener_registry


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


@dataclass
class UserEvent: ...


@dataclass
class UserCreated(UserEvent):
    changed_name: str


user_cmd_handler = handler_registry(UserCommand)
user_event_handler = listener_registry(UserEvent)


@user_cmd_handler
class UserService:
    def __init__(self, name: str = "test", *, anywise: AnyWise):
        self.name = name
        self._anywise = anywise

    def create_user(self, cmd: CreateUser) -> str:
        assert self.name == "test"
        return "hello"

    def remove_user(self, cmd: RemoveUser) -> str:
        assert self.name == "test"
        return "goodbye"


def user_service_factory(anywise: AnyWise) -> "UserService":
    return UserService(name="test", anywise=anywise)


@user_cmd_handler
def update_user(
    cmd: UpdateUser,
    service: UserService = inject(user_service_factory),
) -> str:
    return cmd.new_name


@user_event_handler
def react_to_event(
    event: UserCreated,
    service: UserService = inject(user_service_factory),
) -> None:
    print(f"first handler {event}")


@user_event_handler
def react_to_event2(
    event: UserCreated,
    service: UserService = inject(user_service_factory),
) -> None:
    print(f"second handler {event}")


@pytest.fixture(scope="module")
def anywise() -> AnyWise:
    aw = AnyWise()
    aw.include([user_cmd_handler, user_event_handler])
    return aw
