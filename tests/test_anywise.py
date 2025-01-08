from typing import Mapping, MutableMapping

import pytest

from anywise import FrozenContext
from anywise.anywise import (
    Anywise,
    ListenerManager,
    MessageRegistry,
    context_wrapper,
    default_publish,
    default_send,
)
from anywise.errors import UnregisteredMessageError


async def test_default_send_without_context():
    async def handler(msg: str, ctx: MutableMapping[str, str]) -> str:
        assert ctx == {}
        return "handled"

    result = await default_send("test_message", None, handler)
    assert result == "handled"


async def test_default_publish_without_context():
    async def handler(msg: str, ctx: Mapping[str, str]) -> None:
        assert ctx == {}

    await default_publish("test_message", None, [handler])


async def test_inject_mixin_resolve_sync_meta():
    class TestService:
        def sync_method(self, msg: str) -> str:
            return f"handled {msg}"

    registry = MessageRegistry(command_base=str)

    registry.register(TestService)
    aw = Anywise(registry)
    await aw.send("test")


async def test_inspect_getitem():
    from anywise import Anywise, MessageRegistry
    from tests.conftest import CreateUser, UserCommand

    registry = MessageRegistry(command_base=UserCommand)

    async def handle_create(cmd: CreateUser) -> str:
        return "created"

    registry.register(handle_create)
    aw = Anywise(registry)

    # Test getting handler
    handler = aw.inspect[CreateUser]
    assert handler is not None

    # Test getting non-existent handler
    class UnregisteredCommand: ...

    assert aw.inspect[UnregisteredCommand] is None


# Test for line 96 (context_wrapper)
async def test_context_wrapper_with_non_context_handler():
    async def original_handler(msg: str) -> str:
        return f"handled {msg}"

    wrapped = context_wrapper(original_handler)
    result = await wrapped("test", {"some": "context"})
    assert result == "handled test"


# Test for lines 141-142, 165 (ListenerManager)
async def test_listener_manager_include_listeners():
    from ididi import DependencyGraph

    class TestEvent:
        pass

    async def listener1(event: TestEvent, ctx: dict[str, str]) -> None:
        return None

    async def listener2(event: TestEvent, ctx: dict[str, str]) -> None:
        return None

    dg = DependencyGraph()
    manager = ListenerManager(dg)

    reg = MessageRegistry(event_base=TestEvent)

    reg.register(listener1, listener2)

    # Create event mapping
    # Test including listeners for new message type
    manager.include_listeners(reg.event_mapping)
    assert len(manager.get_listeners(TestEvent)) == 2

    # Test including listeners for existing message type
    manager.include_listeners(reg.event_mapping)  # Should append to existing listeners
    assert len(manager.get_listeners(TestEvent)) == 4


# Test for lines 173, 180-181 (get_listeners and resolve_listeners)
async def test_listener_manager_get_and_resolve_listeners():
    from ididi import DependencyGraph

    class TestEvent:
        pass

    dg = DependencyGraph()
    manager = ListenerManager(dg)

    # Test get_listeners with non-existent message type
    assert manager.get_listeners(TestEvent) == []

    # Test resolve_listeners with non-existent message type
    async with dg.scope("test") as scope:
        with pytest.raises(UnregisteredMessageError):
            await manager.resolve_listeners(TestEvent, scope=scope)


# Test for lines 201, 207, 210 (Inspect class)
async def test_inspect_weakref_cleanup():
    aw = Anywise()
    inspector = aw.inspect

    del aw

    inspector[str]


# Test for lines 293, 304 (Anywise send/publish without sink)
async def test_anywise_sink_not_set():
    aw = Anywise()

    class TestEvent:
        pass

    with pytest.raises(Exception, match="sink is not set"):
        await aw.sink(TestEvent())


# Test for lines 326-328 (Anywise publish with context)
async def test_anywise_publish_with_context():
    class TestEvent:
        pass

    context_received: dict[str, str] | None = None

    async def test_listener(
        event: TestEvent, ctx: FrozenContext[dict[str, str]]
    ) -> None:
        nonlocal context_received
        context_received = ctx
        return None

    registry = MessageRegistry(event_base=TestEvent)
    registry.register(test_listener)

    aw = Anywise(registry)
    test_context: dict[str, str] = {"test": "value"}

    await aw.publish(TestEvent(), context=test_context)
    assert context_received == test_context
