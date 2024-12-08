from dataclasses import dataclass

import pytest

from anywise import AnyWise, command_registry, event_registry, inject


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


user_registry = command_registry(UserCommand)
e_regitry = event_registry(UserEvent)


@user_registry.register
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


@user_registry.register
def update_user(
    cmd: UpdateUser,
    service: UserService = inject(user_service_factory),
) -> str:
    return cmd.new_name


@e_regitry.register
def react_to_event(
    event: UserCreated,
    service: UserService = inject(user_service_factory),
) -> None:
    print(event)

@e_regitry.register
def react_to_event2(
    event: UserCreated,
    service: UserService = inject(user_service_factory),
) -> None:
    print(f"second to {event}")


@pytest.fixture(scope="module")
def anywise() -> AnyWise:
    aw = AnyWise()
    aw.include([user_registry, e_regitry])
    return aw
