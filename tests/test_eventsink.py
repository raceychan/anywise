"""
EventSink is a port to
"""

import pytest

from anywise import Anywise, MessageRegistry
from anywise.errors import SinkUnsetError
from anywise.messages import Event, IEvent
from anywise.sink import InMemorySink

reg = MessageRegistry(event_base=Event)


class UserCreated(Event): ...


@reg
async def listen_created(event: UserCreated, anywise: Anywise):
    await anywise.sink(event)


@pytest.fixture
def user_created():
    return UserCreated(entity_id="1")


async def test_unset_sink(user_created: UserCreated):
    aw = Anywise(reg)
    with pytest.raises(SinkUnsetError):
        await aw.publish(user_created)


async def test_sink_event(user_created: UserCreated):
    sink = InMemorySink[IEvent]()
    aw = Anywise(reg, sink=sink)
    await aw.publish(user_created)
    assert sink.queue.qsize() == 1


async def test_sink_multiple_event():
    sink = InMemorySink[IEvent]()
    aw = Anywise(reg, sink=sink)
    events = [
        UserCreated(entity_id="1"),
        UserCreated(entity_id="2"),
        UserCreated(entity_id="3"),
    ]
    await aw.sink(events)
    assert sink.queue.qsize() == len(events)
