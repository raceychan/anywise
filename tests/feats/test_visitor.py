from anywise import MessageRegistry
from anywise._visitor import gather_types
from tests.conftest import CreateUser, RemoveUser, UpdateUser, UserCommand

user_registry = MessageRegistry(command_base=UserCommand)


def test_gather_commands():
    b = CreateUser | UserCommand
    c = UserCommand

    all_cmds = {UserCommand, CreateUser, UpdateUser, RemoveUser}

    assert gather_types(b) == gather_types(c) == all_cmds
