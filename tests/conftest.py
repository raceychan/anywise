from dataclasses import dataclass


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
    user_name: str


@dataclass
class UserNameUpdated(UserEvent):
    changed_name: str
