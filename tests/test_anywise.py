from dataclasses import dataclass
from typing import Mapping

import pytest

from anywise import Context, FrozenContext, Ignore
from anywise.anywise import (
    Anywise,
    ListenerManager,
    MessageRegistry,
    context_wrapper,
    default_publish,
    default_send,
)
from anywise.errors import SinkUnsetError, UnregisteredMessageError


async def handler(msg: str, ctx: Context[dict[str, str]]) -> str:
    assert ctx == {}
    return "handled"


async def test_send_with_scope():
    mr = MessageRegistry(command_base=str)
    mr.register(handler)

    aw = Anywise(mr)

    async with aw.scope("message") as scope:
        await aw.send("a", scope=scope)


async def test_default_send_without_context():

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


# Test for line 96 (context_wrapper)
async def test_context_wrapper_with_non_context_handler():
    async def original_handler(msg: str) -> str:
        return f"handled {msg}"

    wrapped = context_wrapper(original_handler)
    result = await wrapped("test", {"some": "context"})
    assert result == "handled test"


# Test for lines 141-142, 165 (ListenerManager)
async def test_listener_manager_include_listeners():
    class TestEvent:
        pass

    async def listener1(event: TestEvent, ctx: dict[str, str]) -> None:
        return None

    async def listener2(event: TestEvent, ctx: dict[str, str]) -> None:
        return None

    reg = MessageRegistry(event_base=TestEvent)

    reg.register(listener1, listener2)

    aw = Anywise(reg)

    # Create event mapping
    # Test including listeners for new message type
    listeners = aw.inspect.listeners(TestEvent)
    assert listeners and len(listeners) == 2


async def test_unregistered_event():
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


# Test for lines 293, 304 (Anywise send/publish without sink)
async def test_anywise_sink_not_set():
    aw = Anywise()

    class TestEvent:
        pass

    with pytest.raises(SinkUnsetError):
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


async def test_aw_properties():
    aw = Anywise()
    assert aw.sender is default_send
    assert aw.publisher is default_publish


async def test_aw_handle_command():
    class Command: ...

    @dataclass
    class CreateUser(Command):
        user_name: str

    class UserService:
        def __init__(self, conn: Ignore[str]):
            self.conn = conn

    service = UserService("asdf")

    async def handle_create(cmd: CreateUser, aw: Anywise, service: UserService):
        assert service.conn == "asdf"
        return "ok"

    mr = MessageRegistry(command_base=Command)
    mr.register(handle_create)

    aw = Anywise(mr)
    aw.graph.register_singleton(service)
    assert await aw.send(CreateUser("user")) == "ok"


async def test_aw_handle_event():
    class Event: ...

    @dataclass
    class UserCreated(Event):
        user_name: str

    class UserService:
        def __init__(self, conn: Ignore[str]):
            self.conn = conn

    service = UserService("asdf")

    async def listen_created(event: UserCreated, aw: Anywise, service: UserService):
        assert service.conn == "asdf"

    async def listen_created_aswell(event: UserCreated, service: UserService):
        assert service.conn == "asdf"

    mr1 = MessageRegistry(event_base=Event)
    mr2 = MessageRegistry(event_base=Event)

    mr1.register(listen_created)
    mr2.register(listen_created_aswell)

    aw = Anywise(mr1, mr2)
    aw.graph.register_singleton(service)
    await aw.publish(UserCreated("user"))
