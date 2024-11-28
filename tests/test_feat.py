from dataclasses import dataclass

from anywise._type_resolve import Mark
from anywise.anywise import AnyWise


@dataclass
class UserCommand:
    user_id: str


@dataclass
class CreateUser(UserCommand):
    user_name: str


@dataclass
class RemoveUser(UserCommand): ...


@dataclass
class UpdateUser(UserCommand):
    old_name: str
    new_name: str


command_handler = Mark(UserCommand)


@command_handler
def update_user(cmd: UpdateUser):
    return cmd.new_name


@command_handler
class UserService:

    def __init__(self):
        self.name = "name"

    @command_handler
    async def create_user(self, cmd: CreateUser) -> str:
        return "hello"

    async def remove_user(self, cmd: RemoveUser) -> str:
        return "goodbye"

    @command_handler.unpack(CreateUser)
    def create(self, user_id: str, user_name: str) -> str:
        return "created"


async def test():
    aw = AnyWise()
    aw.register(command_handler)

    cmd = CreateUser("1", "user")
    res = await aw.send(cmd)
    assert res == "hello"
