from anywise import MessageRegistry
from anywise._visitor import gather_commands
from tests.conftest import CreateUser, RemoveUser, UpdateUser, UserCommand

user_registry = MessageRegistry(command_base=UserCommand)


def test_gather_commands():
    b = CreateUser | UserCommand
    c = UserCommand

    all_cmds = {UserCommand, CreateUser, UpdateUser, RemoveUser}

    assert gather_commands(b) == gather_commands(c) == all_cmds
