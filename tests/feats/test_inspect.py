from typing import Any
import pytest

from anywise import Anywise, Context, MessageRegistry
from anywise.errors import UnregisteredMessageError
from tests.conftest import CreateUser, UserCommand


async def test_inspect_getitem():

    registry = MessageRegistry(command_base=UserCommand)

    async def handle_create(cmd: CreateUser) -> str:
        return "created"

    async def pre_handle(cmd: CreateUser, ctx: Context[dict[str, str]]):
        assert cmd

    async def global_pre_handle(cmd: Any, ctx: dict[str, str]):
        assert cmd

    registry.register(handle_create, pre_hanldes=[global_pre_handle, pre_handle])
    aw = Anywise(registry)

    # Test getting handler
    handler = aw.inspect.handler(CreateUser)
    assert handler is not None

    # Test getting non-existent handler
    class UnregisteredCommand: ...

    assert aw.inspect.handler(UnregisteredCommand) is None
    assert aw.inspect.guards(CreateUser)


async def test_unregistered_command():
    # import gc

    from anywise import Anywise, MessageRegistry

    class TestCommand:
        pass

    registry = MessageRegistry(command_base=TestCommand)
    aw = Anywise(registry)

    inspect = aw.inspect

    # Test get_listeners with non-existent message type
    assert not inspect.handler(TestCommand)

    # Test resolve_listeners with non-existent message type
    with pytest.raises(UnregisteredMessageError):
        await aw.send(object())

    assert aw.graph
    aw.reset_graph()
    del aw

    assert not inspect.guards(TestCommand)


# Test for lines 201, 207, 210 (Inspect class)
async def test_inspect_weakref_cleanup():
    aw = Anywise()
    inspector = aw.inspect

    del aw

    inspector.handler(str)
